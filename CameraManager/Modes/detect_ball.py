import cv2
import numpy as np
import asyncio
import time

from base_mode import BaseCameraMode

# =================== KONFIG =====================

SEND_INTERVAL_MS = 100
MIN_AREA = 800          # minimální plocha – menší ignorujeme
MASK_BLUR = 7

HSV_LOWER = np.array([145, 80, 60])
HSV_UPPER = np.array([175, 255, 255])


class DetectBall(BaseCameraMode):
    name = "DETECTBALL"

    async def loop(self):
        self.log.info("DetectBall running")

        cx = self.frame_w // 2
        cy = self.frame_h // 2

        last_send = 0

        while self.running:

            ok, frame = self.cap.read()
            if not ok:
                await asyncio.sleep(0)
                continue

            # -------------------------------------
            # MASKA
            # -------------------------------------
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
            mask = cv2.GaussianBlur(mask, (MASK_BLUR, MASK_BLUR), 0)

            # -------------------------------------
            # NAJÍT NEJVĚTŠÍ KONTURU
            # -------------------------------------
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            best = None
            best_area = 0

            for c in contours:
                area = cv2.contourArea(c)
                if area > best_area and area > MIN_AREA:
                    best_area = area
                    best = c

            # -------------------------------------
            # DEBUG OBRÁZEK
            # -------------------------------------
            debug = frame.copy()

            ball_x = -1
            ball_y = -1

            if best is not None:
                M = cv2.moments(best)
                if M["m00"] > 0:
                    bx = int(M["m10"] / M["m00"])
                    by = int(M["m01"] / M["m00"])

                    ball_x, ball_y = bx, by

                    # Kruh kolem míče
                    (cx2, cy2), r = cv2.minEnclosingCircle(best)
                    cv2.circle(debug, (int(cx2), int(cy2)), int(r), (0,255,0), 2)
                    cv2.circle(debug, (bx, by), 6, (0,255,0), -1)

                    # XY text
                    rel_x = bx - cx
                    rel_y = by - cy
                    cv2.putText(debug, f"X={rel_x}  Y={rel_y}", (bx+10, by),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

            else:
                rel_x = -1
                rel_y = -1

            # -------------------------------------
            # POSÍLÁNÍ DAT KAŽDÝCH X ms
            # -------------------------------------
            now = time.time() * 1000
            if now - last_send > SEND_INTERVAL_MS:
                await self.send_data(rel_x, rel_y)
                last_send = now

            # -------------------------------------
            # PREVIEW – maska + live+debug
            # -------------------------------------
            mask_rgb = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            mask_rgb = cv2.resize(mask_rgb, (self.frame_w, self.frame_h))
            debug_resized = cv2.resize(debug, (self.frame_w, self.frame_h))

            preview = np.hstack((mask_rgb, debug_resized))
            await self.send_preview(preview)

            await asyncio.sleep(0)
