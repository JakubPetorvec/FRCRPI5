import asyncio
import socket
import os
import sys
import zmq
import zmq.asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from LoggerManager.logger import Logger
from ProgramManager.ports import (
    PROGRAM_SELECT_PORT,
    CAMERA_DATA_PORT,
    PREVIEW_PORT,
    ROBORIO_IP,
)

from Modes.detect_ball import DetectBall
from Modes.apriltag import AprilTag
from Modes.detect_qrcode import QRCodeMode

from camera_bus import CameraBus


class CameraManager:
    def __init__(self):
        self.log = Logger("CameraManager")
        self.current_mode = None

        self.CAMERA_DATA_PORT = CAMERA_DATA_PORT
        self.PREVIEW_PORT = PREVIEW_PORT
        self.ROBORIO_IP = ROBORIO_IP

        # UDP
        self.udp_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.preview_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # ZMQ pro příjem
        self.ctx = zmq.asyncio.Context()
        self.sub = self.ctx.socket(zmq.DEALER)
        self.sub.identity = b"CameraManager"
        self.sub.connect("ipc:///tmp/messenger_data.sock")

        self.bus = CameraBus("CameraBus")

    async def run(self):

        asyncio.create_task(self.listen_commands())
        asyncio.create_task(self.listen_messenger())

        self.log.info("CameraManager ready.")
        while True:
            await asyncio.sleep(1)

    async def listen_commands(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", PROGRAM_SELECT_PORT))

        self.log.info(f"Listening on UDP {PROGRAM_SELECT_PORT}")
        loop = asyncio.get_running_loop()

        while True:
            data, addr = await loop.run_in_executor(None, sock.recvfrom, 1024)
            msg = data.decode().strip().upper()
            self.log.info(f"CMD: {msg}")
            await self.set_mode(msg)

    async def set_mode(self, msg):
        if not msg.startswith("SET MODE "):
            self.log.warn(f"Neplatný příkaz: {msg}")
            return

        mode = msg.replace("SET MODE ", "")

        if self.current_mode:
            self.log.info(f"Zastavuji {self.current_mode.name}")
            await self.current_mode.stop()

        if mode == "DETECTBALL":
            self.current_mode = DetectBall(self)

        elif mode == "APRILTAG":
            self.current_mode = AprilTag(self)

        elif mode == "QRCODE":
            self.current_mode = QRCodeMode(self)

        else:
            self.log.warn(f"Neznámý mód {mode}, nic nespouštím.")
            self.current_mode = None
            return

        self.log.info(f"Přepínám režim → {self.current_mode.name}")
        await self.current_mode.start()

    async def listen_messenger(self):
        self.log.info("ZMQ listener ready.")

        while True:
            try:
                msg = await self.sub.recv_json()
                cmd = msg.get("cmd")
                reply_target = msg.get("reply_to")

                if not reply_target:
                    continue

                if cmd == "get_status":
                    resp = {"mode": self.current_mode.name if self.current_mode else "NONE"}

                else:
                    resp = {"error": "Unknown command"}

                await self.sub.send_json({
                    "target": reply_target,
                    "data": resp
                })

            except Exception as e:
                self.log.error(f"ZMQ error: {e}")
                await asyncio.sleep(0.2)

    def update_ball_data(self, x, y):
        self.last_ball = {"x": x, "y": y}

    def update_tag_data(self, tag_id, x, y):
        self.last_tag = {"id": tag_id, "x": x, "y": y}


if __name__ == "__main__":
    mgr = CameraManager()
    asyncio.run(mgr.run())
