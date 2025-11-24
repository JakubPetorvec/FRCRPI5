import cv2
import numpy as np
import asyncio
import time

from base_mode import BaseCameraMode


SEND_INTERVAL_MS = 10
MIN_AREA = 1000          # větší jistota
MASK_BLUR = 7
KERNEL = np.ones((7, 7), np.uint8)
MIN_CIRCULARITY = 0.30

# --------------------------------------------------------------
#  HSV podle reálné barvy z tvé fotky – TOTO JE KLÍČ
# --------------------------------------------------------------
HSV_LOWER = np.array([160, 120, 120])
HSV_UPPER = np.array([180, 255, 255])


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

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # ---------------------------------------------------------
            #   MASKA – ultra čistá verze
            # ---------------------------------------------------------
            mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
            mask = cv2.GaussianBlur(mask, (MASK_BLUR, MASK_BLUR), 0)

            # odstranění šumu
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, KERNEL)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, KERNEL)

            # odlesky / ruce → jemný erode
            mask = cv2.erode(mask, np.ones((3,3), np.uint8))

            # ---------------------------------------------------------
            #  KONTURY – najdeme JEDEN největší blob
            # ---------------------------------------------------------
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            best = None
            best_score = 0

            for c in contours:
                area = cv2.contourArea(c)
                if area < MIN_AREA:
                    continue

                # kruhovitost
                per = cv2.arcLength(c, True)
                if per == 0:
                    continue

                circularity = 4 * np.pi * (area / (per * per))
                if circularity < MIN_CIRCULARITY:
                    continue

                # score = kruhovitost x plocha
                score = circularity * area

                if score > best_score:
                    best_score = score
                    best = c

            debug = frame.copy()

            # ---------------------------------------------------------
            #  VÝSTUP
            # ---------------------------------------------------------
            rel_x = -1
            rel_y = -1
            ball_detected = False

            if best is not None:
                M = cv2.moments(best)
                if M["m00"] > 0:
                    bx = int(M["m10"] / M["m00"])
                    by = int(M["m01"] / M["m00"])

                    rel_x = bx - cx
                    rel_y = by - cy
                    ball_detected = True

                    (cx2, cy2), r = cv2.minEnclosingCircle(best)
                    cv2.circle(debug, (int(cx2), int(cy2)), int(r), (0, 255, 0), 2)
                    cv2.circle(debug, (bx, by), 6, (0, 255, 0), -1)

                    cv2.putText(
                        debug, f"X={rel_x} Y={rel_y}",
                        (bx + 10, by),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0), 2
                    )

            # ---------------------------------------------------------
            #  PREVIEW — BEZ JEDINÉ ZMĚNY (NEŠAHÁM NA TO!)
            # ---------------------------------------------------------
            mask_color = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            side = np.hstack((debug, mask_color))

            preview = cv2.resize(side, (self.frame_w, self.frame_h))
            await self.send_preview(preview)

            # ---------------------------------------------------------
            # POSÍLÁNÍ DAT
            # ---------------------------------------------------------
            now = time.time() * 1000
            if now - last_send > SEND_INTERVAL_MS:

                await self.send_data(rel_x, rel_y)

                if getattr(self.manager, "bus", None) is not None:
                    await self.manager.bus.send_detect_ball(
                        rel_x, rel_y, ball_detected
                    )

                last_send = now

            await asyncio.sleep(0)
