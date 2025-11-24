import cv2
import asyncio
import time
from pupil_apriltags import Detector

from base_mode import BaseCameraMode


SEND_ZMQ_INTERVAL = 0.5  # sekundy – posíláme jen jednou za 0.5s


class AprilTag(BaseCameraMode):
    name = "APRILTAG"

    async def start(self):
        self.detector = Detector(
            families='tag36h11',
            nthreads=1,
            quad_decimate=2.0,
            quad_sigma=0.0,
            refine_edges=True
        )
        await super().start()

    async def loop(self):
        self.log.info("AprilTag detection running")

        cx = self.frame_w // 2
        cy = self.frame_h // 2

        last_zmq_send = 0   # čas posledního ZMQ eventu

        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                await asyncio.sleep(0)
                continue

            # ---- grayscale pro apriltagy ----
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # ---- detekce ----
            tags = self.detector.detect(gray, estimate_tag_pose=False)

            debug = frame.copy()

            # výchozí hodnoty
            offset_x = -1.0
            offset_y = -1.0
            tag_id = -1.0

            # věci pro display
            display_tags = []

            for t in tags:

                tx = float(t.center[0])
                ty = float(t.center[1])
                dx = tx - cx
                dy = ty - cy

                pts = t.corners.astype(int)
                cv2.polylines(debug, [pts], True, (0, 255, 0), 2)
                cv2.circle(debug, (int(tx), int(ty)), 5, (0, 255, 0), -1)

                cv2.putText(debug,
                            f"id={t.tag_id}",
                            (int(tx) + 10, int(ty) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 0), 1)

                display_tags.append({
                    "id": int(t.tag_id),
                    "family": (
                        t.tag_family.decode("utf-8") 
                        if isinstance(t.tag_family, bytes) 
                        else t.tag_family
                    ),
                    "center": [tx, ty],
                    "offset": [dx, dy],
                    "corners": t.corners.tolist(),
                })

            # UDP → RoboRIO (vždy)
            if display_tags:
                first = display_tags[0]
                offset_x = float(first["offset"][0])
                offset_y = float(first["offset"][1])
                tag_id = float(first["id"])

            await self.send_data(offset_x, offset_y, tag_id)

            # ZMQ → DISPLAY (jen 1× za 0.5s)
            now = time.time()
            if now - last_zmq_send >= SEND_ZMQ_INTERVAL:
                if getattr(self.manager, "bus", None) is not None:
                    await self.manager.bus.send_apriltag(display_tags)
                last_zmq_send = now

            # preview → DisplayManager
            preview = cv2.resize(debug, (self.frame_w, self.frame_h))
            await self.send_preview(preview)

            await asyncio.sleep(0)
