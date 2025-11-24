import os
import sys
import time
import zmq
import zmq.asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from LoggerManager.logger import Logger

import zmq.utils.jsonapi as jsonapi

class CameraBus:
    def __init__(self, name="CameraBus"):
        self.log = Logger(name)
        self.ctx = zmq.asyncio.Context.instance()
        self.sock = self.ctx.socket(zmq.DEALER)

        self.sock.connect("ipc:///tmp/messenger_data.sock")

        self.sender_name = "CameraManager"
        self.target_name = "DisplayManager"

        self.log.info("CameraBus connected to messenger.")

    async def send_apriltag(self, tags):
        msg = {
            "sender": self.sender_name,
            "target": self.target_name,
            "type": "camera_event",
            "mode": "APRILTAG",
            "payload": {
                "timestamp": time.time(),
                "tags": tags,
            },
        }

        try:
            await self.sock.send(jsonapi.dumps(msg))
            #self.log.debug(jsonapi.dumps(msg).decode())
        except Exception as e:
            self.log.warn(f"send_apriltag failed: {e}")

    async def send_detect_ball(self, rel_x, rel_y, detected):
        msg = {
            "sender": self.sender_name,
            "target": self.target_name,
            "type": "camera_event",
            "mode": "DETECTBALL",
            "payload": {
                "timestamp": time.time(),
                "ball": {
                    "x": float(rel_x),
                    "y": float(rel_y),
                    "detected": bool(detected),
                },
            },
        }

        try:
            #self.log.debug(jsonapi.dumps(msg).decode())
            await self.sock.send(jsonapi.dumps(msg))
        except Exception as e:
            self.log.warn(f"send_detect_ball failed: {e}")

    async def send_qrcode(self, codes):
        msg = {
            "sender": self.sender_name,
            "target": self.target_name,
            "type": "camera_event",
            "mode": "QRCODE",
            "payload": {
                "timestamp": time.time(),
                "codes": codes,
            },
        }

        try:
            #self.log.debug(jsonapi.dumps(msg).decode())
            await self.sock.send(jsonapi.dumps(msg))
        except Exception as e:
            self.log.warn(f"send_qrcode failed: {e}")

    async def close(self):
        try:
            self.sock.close(linger=0)
        except:
            pass
        self.log.info("CameraBus closed.")
