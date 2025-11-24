import cv2
import numpy as np
import asyncio
import time

from base_mode import BaseCameraMode


SEND_ZMQ_INTERVAL = 0.5   # s – jak často posíláme ZMQ event na DisplayManager
SEND_INTERVAL_MS = 10     # ms – jak často posíláme UDP data na RoboRIO


class QRCodeMode(BaseCameraMode):
    name = "QRCODE"

    async def start(self):
        # OpenCV detektor QR kódů
        self.detector = cv2.QRCodeDetector()
        await super().start()

    async def loop(self):
        self.log.info("QRCode detection running")

        cx = self.frame_w // 2
        cy = self.frame_h // 2

        last_udp_send = 0.0
        last_zmq_send = 0.0

        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                await asyncio.sleep(0)
                continue

            debug = frame.copy()

            # ---------------------------------------------------------
            #  DETEKCE JEDNOHO QR KÓDU
            # ---------------------------------------------------------
            codes = []
            offset_x = -1.0
            offset_y = -1.0

            try:
                # data = string, points = 4 body, straight_qrcode = nepoužijeme
                data, points, _ = self.detector.detectAndDecode(debug)
            except Exception as e:
                self.log.warn(f"QRCode detectAndDecode error: {e}")
                data = ""
                points = None

            if data and points is not None:
                pts = np.int32(points)  # (4, 2)

                tx = float(np.mean(pts[:, 0]))
                ty = float(np.mean(pts[:, 1]))
                dx = tx - cx
                dy = ty - cy

                offset_x = dx
                offset_y = dy

                # vykreslení obrysu a středu
                cv2.polylines(debug, [pts], True, (0, 255, 0), 2)
                cv2.circle(debug, (int(tx), int(ty)), 5, (0, 255, 0), -1)

                label = str(data)
                if len(label) > 20:
                    label = label[:17] + "..."

                cv2.putText(
                    debug,
                    label,
                    (int(tx) + 10, int(ty) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
                )

                codes.append(
                    {
                        "data": str(data),
                        "center": [tx, ty],
                        "offset": [dx, dy],
                        "corners": pts.tolist(),
                    }
                )

            # ---------------------------------------------------------
            #  UDP → RoboRIO (X, Y jako u DETECTBALL)
            # ---------------------------------------------------------
            now_ms = time.time() * 1000.0
            if now_ms - last_udp_send >= SEND_INTERVAL_MS:
                await self.send_data(float(offset_x), float(offset_y))
                last_udp_send = now_ms

            # ---------------------------------------------------------
            #  ZMQ → DISPLAY (JSON event s kompletními daty o kódu)
            # ---------------------------------------------------------
            now = time.time()
            if now - last_zmq_send >= SEND_ZMQ_INTERVAL:
                if getattr(self.manager, "bus", None) is not None:
                    # očekává se CameraBus.send_qrcode(codes)
                    try:
                        await self.manager.bus.send_qrcode(codes)
                    except AttributeError:
                        # kdybys neměl send_qrcode, jen to ignoruj
                        self.log.warn("CameraBus has no send_qrcode(), skipping")
                last_zmq_send = now

            # ---------------------------------------------------------
            #  PREVIEW → WebPreview (ÚPLNĚ STEJNĚ JAKO APRILTAG)
            # ---------------------------------------------------------
            preview = cv2.resize(debug, (self.frame_w, self.frame_h))
            await self.send_preview(preview)

            await asyncio.sleep(0)
