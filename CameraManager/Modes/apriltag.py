import cv2
import numpy as np
import asyncio
import time
from pupil_apriltags import Detector

from base_mode import BaseCameraMode

class AprilTag(BaseCameraMode):
    name = "APRILTAG"
    SEND_INTERVAL_S = 0.5

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

        last_send = 0

        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                await asyncio.sleep(0)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            tags = self.detector.detect(
                gray,
                estimate_tag_pose=False
            )

            debug = frame.copy()

            # výstup pro RoboRIO – 1 tag (nebo žádný)
            offset_x = -1.0
            offset_y = -1.0
            tag_id = -1.0

            # výstup pro Display – list všech tagů
            display_tags = []

            for t in tags:
                tx, ty = float(t.center[0]), float(t.center[1])
                dx = tx - cx
                dy = ty - cy

                # polygon + marker
                pts = t.corners.astype(int)
                cv2.polylines(debug, [pts], True, (0, 255, 0), 2)
                cv2.circle(debug, (int(tx), int(ty)), 5, (0, 255, 0), -1)

                cv2.putText(
                    debug,
                    f"id={t.tag_id}",
                    (int(tx) + 10, int(ty) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1
                )

                display_tags.append({
                    "id": int(t.tag_id),
                    "family": str(t.tag_family.decode("utf-8") if isinstance(t.tag_family, bytes) else t.tag_family),
                    "center": [tx, ty],
                    "offset": [dx, dy],
                    "corners": t.corners.tolist(),
                })

            if display_tags:
                # pro RoboRIO vezmeme první
                first = display_tags[0]
                offset_x = float(first["offset"][0])
                offset_y = float(first["offset"][1])
                tag_id = float(first["id"])

                # self.log.debug(
                #     f"TAG id={int(tag_id)}  dx={offset_x:.1f}  dy={offset_y:.1f}"
                # )
            #else:
                #self.log.debug("no tag")

            now = time.time()
            if now - last_send >= self.SEND_INTERVAL_S:
                # UDP → RoboRIO
                await self.send_data(offset_x, offset_y, tag_id)

                # Messenger → Display (pokud bus existuje)
                if getattr(self.manager, "bus", None) is not None:
                    await self.manager.bus.send_apriltag(display_tags)
                else:
                    self.log.debug("no bus")

                last_send = now

            # preview
            preview = cv2.resize(debug, (self.frame_w, self.frame_h))
            await self.send_preview(preview)

            await asyncio.sleep(0)
