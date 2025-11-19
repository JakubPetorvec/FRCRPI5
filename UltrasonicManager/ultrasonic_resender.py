import asyncio
import socket
import struct
import serial
import importlib.util
import zmq
import zmq.asyncio

# ============================================================
# LOAD PORTS
# ============================================================
PORT_FILE = "/home/dickin/FRC/ProgramManager/ports.py"
spec_ports = importlib.util.spec_from_file_location("ports", PORT_FILE)
ports = importlib.util.module_from_spec(spec_ports)
spec_ports.loader.exec_module(ports)

UDP_PORT = 5820
ROBORIO_IP = "10.69.69.2"
SERIAL_PORT = "/dev/ttyACM0"
BAUD = 9600

# ============================================================
# LOGGER
# ============================================================
LOGGER_FILE = "/home/dickin/FRC/LoggerManager/logger.py"
spec_log = importlib.util.spec_from_file_location("logger", LOGGER_FILE)
logger_module = importlib.util.module_from_spec(spec_log)
spec_log.loader_exec_module = spec_log.loader.exec_module  # fix
spec_log.loader_exec_module(logger_module)

Logger = logger_module.Logger


# ============================================================
# SONIC MANAGER
# ============================================================
class SonicManager:
    def __init__(self):
        self.log = Logger("SonicManager")

        self.ser = None
        self.running = True

        # poslední hodnoty sonarů (8x float)
        self.sonic_values = [0.0] * 8

        # UDP socket → RoboRIO
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Messenger
        self.ctx = zmq.asyncio.Context()
        self.sock = self.ctx.socket(zmq.DEALER)
        self.sock.connect("ipc:///tmp/messenger_data.sock")

        self.subscribers = set()

    # -----------------------------------------------------------
    async def register(self):
        await self.sock.send_json({"sender": "SONIC_MANAGER"})
        self.log.info("Registered to MessengerServer")

    # -----------------------------------------------------------
    async def connect_serial(self):
        while self.running:
            try:
                self.ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
                self.log.info(f"Serial connected: {SERIAL_PORT}")
                return
            except Exception:
                self.log.warn("Waiting for sonar serial...")
                await asyncio.sleep(1)

    # -----------------------------------------------------------
    async def read_serial(self):
        """Čte 8 hodnot z pico → ultrasonic module"""
        while self.running:
            if not self.ser or not self.ser.is_open:
                await self.connect_serial()
                continue

            try:
                line = self.ser.readline().decode().strip()
                if not line:
                    continue

                parts = line.split(",")
                if len(parts) != 8:
                    self.log.warn(f"Invalid sonic packet: '{line}'")
                    continue

                # převod
                self.sonic_values = [float(p) for p in parts]

                # odeslat na RoboRIO
                packed = struct.pack("8f", *self.sonic_values)
                self.udp.sendto(packed, (ROBORIO_IP, UDP_PORT))

            except Exception as e:
                self.log.error(f"Sonic read error: {e}")
                await asyncio.sleep(0.2)

    # -----------------------------------------------------------
    async def send_state_to(self, target):
        await self.sock.send_json({
            "sender": "SONIC_MANAGER",
            "target": target,
            "cmd": "STATE_UPDATE",
            "data": {
                "sonics": self.sonic_values
            }
        })

    # -----------------------------------------------------------
    async def broadcast_state(self):
        for target in self.subscribers:
            await self.send_state_to(target)

    # -----------------------------------------------------------
    async def poll_messenger(self):
        while self.running:
            try:
                msg = await self.sock.recv_json()
                sender = msg.get("sender")
                cmd = msg.get("cmd")

                if not sender:
                    continue

                if cmd == "GET_STATE":
                    await self.send_state_to(sender)
                    continue

                if cmd == "SUBSCRIBE_STATE":
                    self.subscribers.add(sender)
                    self.log.info(f"{sender} subscribed to sonic data")
                    await self.send_state_to(sender)
                    continue

            except Exception as e:
                self.log.error(f"Messenger error: {e}")
                await asyncio.sleep(0.1)

    # -----------------------------------------------------------
    async def periodic_broadcast(self):
        while self.running:
            await self.broadcast_state()
            await asyncio.sleep(1)

    # -----------------------------------------------------------
    async def run(self):
        await self.register()
        await self.connect_serial()

        asyncio.create_task(self.read_serial())
        asyncio.create_task(self.poll_messenger())
        asyncio.create_task(self.periodic_broadcast())

        self.log.info("SonicManager ready")

        while self.running:
            await asyncio.sleep(1)


# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    mgr = SonicManager()
    asyncio.run(mgr.run())
