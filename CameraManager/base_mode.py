import asyncio
import struct
import cv2
import socket


class BaseCameraMode:
    name = "BASE"

    def __init__(self, manager):
        from LoggerManager.logger import Logger  # lazy import kvůli cestám

        self.manager = manager
        self.log = Logger(self.name)
        self.running = False
        self.cap = None
        self.frame_w = 0
        self.frame_h = 0
        self.task = None

    async def start(self):
        self.running = True
        ok = await self._init_camera()
        if not ok:
            self.log.error("Kamera se nepodařila otevřít.")
            return
        self.task = asyncio.create_task(self.loop())

    async def stop(self):
        self.running = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except:
                pass
            self.task = None

        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None

        self.log.info("Zastaveno.")

    async def _init_camera(self):
        for attempt in range(10):
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                self.cap = cap
                self.frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.log.info(f"Kamera připravena: {self.frame_w}x{self.frame_h}")
                return True

            self.log.warn(f"Kamera nedostupná (pokus {attempt + 1}/10)")
            await asyncio.sleep(0.5)

        return False

    async def send_data(self, *values):
        try:
            packet = struct.pack("f" * len(values), *values)
            self.manager.udp_out.sendto(
                packet,
                (self.manager.ROBORIO_IP, self.manager.CAMERA_DATA_PORT),
                #("127.0.0.1", self.manager.CAMERA_DATA_PORT),
            )
        except Exception as e:
            self.log.warn(f"Chyba při odesílání dat: {e}")

    async def send_preview(self, frame):
        import cv2

        try:
            ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if not ok:
                self.log.warn("cv2.imencode selhal")
                return

            self.manager.preview_sock.sendto(
                jpg.tobytes(), ("127.0.0.1", self.manager.PREVIEW_PORT)
            )
        except Exception as e:
            self.log.warn(f"send_preview error: {e}")

    async def loop(self):
        raise NotImplementedError()
