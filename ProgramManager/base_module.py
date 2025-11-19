import asyncio
import zmq
import zmq.asyncio
from datetime import datetime


class BaseModule:
    """Základní třída pro všechny procesové moduly."""

    def __init__(self, name: str):
        self.name = name
        self.running = True
        self.ctx = zmq.asyncio.Context.instance()

        # === LOG PUB ===
        # ProgramManager BINDuje, moduly CONNECTUJÍ
        self.log_pub = self.ctx.socket(zmq.PUB)
        self.log_pub.connect("ipc:///tmp/messenger_logs.sock")

        # === HEARTBEAT PUB ===
        self.hb_pub = self.ctx.socket(zmq.PUB)
        self.hb_pub.connect("ipc:///tmp/messenger_heartbeat.sock")

        # === DATA DEALER ===
        self.data_sock = self.ctx.socket(zmq.DEALER)
        self.data_sock.identity = self.name.encode()
        self.data_sock.connect("ipc:///tmp/messenger_data.sock")

    # ---------------- LOGGING ----------------
    def log(self, level: str, message: str):
        payload = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sender": self.name,
            "message": (message or ""),
            "level": level.lower()
        }
        self.log_pub.send_json(payload)

    # ---------------- HEARTBEAT ----------------
    async def start_heartbeat(self, interval: int = 10):
        while self.running:
            self.hb_pub.send_json({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sender": self.name,
                "level": "heartbeat"
            })
            await asyncio.sleep(interval)

    # ---------------- SEND DATA ----------------
    async def send(self, target: str, command: str, data: dict):
        payload = {
            "type": "data",
            "sender": self.name,
            "target": target,
            "command": command,
            "data": data,
        }
        await self.data_sock.send_json(payload)

    # ---------------- RECEIVE DATA ----------------
    async def on_message(self, handler):
        while self.running:
            msg = await self.data_sock.recv_json()
            if msg.get("type") == "data" and msg.get("target") == self.name:
                await handler(msg)

    # ---------------- STOP ----------------
    async def stop(self):
        self.running = False
        for sock in [self.log_pub, self.hb_pub, self.data_sock]:
            try:
                sock.close(linger=0)
            except:
                pass
