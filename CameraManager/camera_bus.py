import os
import sys
import time
import zmq
import zmq.asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from LoggerManager.logger import Logger

import zmq.utils.jsonapi as jsonapi


class CameraBus:
    """
    Async klient k MessengerServeru.
    Posílá JSON zprávy typu 'camera_event' na DisplayManager.
    """

    def __init__(self, name="CameraBus"):
        self.log = Logger(name)
        self.ctx = zmq.asyncio.Context.instance()
        self.sock = self.ctx.socket(zmq.DEALER)

        # stejný endpoint jako MessengerServer
        self.sock.connect("ipc:///tmp/messenger_data.sock")

        self.sender_name = "CameraManager"
        self.target_name = "DisplayManager"

        self.log.info("CameraBus connected to messenger.")

    async def send_apriltag(self, tags):
        """
        tags = list dictů:
        {
          "id": int,
          "family": str,
          "center": [x, y],
          "offset": [dx, dy],
          "corners": [[x1,y1],..., [x4,y4]]
        }
        """
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
            #self.log.debug(f"Sent APRILTAG event with {len(tags)} tags")
            self.log.debug(jsonapi.dumps(msg).decode())
        except Exception as e:
            self.log.warn(f"send_apriltag failed: {e}")

    async def close(self):
        try:
            self.sock.close(linger=0)
        except:
            pass
        self.log.info("CameraBus closed.")
