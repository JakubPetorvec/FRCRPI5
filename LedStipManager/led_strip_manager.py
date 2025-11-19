from serial import Serial
import asyncio
import zmq
import zmq.asyncio
import importlib.util


# ============================================================
# CONFIG
# ============================================================
SERIAL_SYMLINK = "/dev/pico_led"     # sem ukazuje tvůj udev alias
BAUDRATE = 115200

# ============================================================
# LOAD PORTS
# ============================================================
PORT_FILE = "/home/dickin/FRC/ProgramManager/ports.py"
spec_ports = importlib.util.spec_from_file_location("ports", PORT_FILE)
ports = importlib.util.module_from_spec(spec_ports)
spec_ports.loader.exec_module(ports)

UDP_PORT = ports.LED_STRIP_PORT

# ============================================================
# LOGGER
# ============================================================
LOGGER_FILE = "/home/dickin/FRC/LoggerManager/logger.py"
spec_log = importlib.util.spec_from_file_location("logger", LOGGER_FILE)
logger_module = importlib.util.module_from_spec(spec_log)
spec_log.loader.exec_module(logger_module)
Logger = logger_module.Logger


# ============================================================
# LED CONTROLLER
# ============================================================
class LedController:
    def __init__(self):
        self.log = Logger("LedController")

        self.ser = None
        self.running = True
        self.subscribers = set()

        # DRŽÍME STAV
        self.current_mode = "IDLE"
        self.current_color = (255, 255, 255)

        # ZMQ
        self.ctx = zmq.asyncio.Context()
        self.sock = self.ctx.socket(zmq.DEALER)
        self.sock.connect("ipc:///tmp/messenger_data.sock")

    # ---------------------------------------------------------
    async def connect_serial(self):
        """Hledá Pico do té doby, než se připojí"""
        while self.running:
            try:
                self.ser = Serial(
                    SERIAL_SYMLINK,
                    BAUDRATE,
                    timeout=0.1
                )
                self.log.info(f"Connected to Pico at {SERIAL_SYMLINK}")
                return
            except Exception:
                self.log.warn("Waiting for Pico...")
                await asyncio.sleep(1)

    # ---------------------------------------------------------
    async def write_serial(self, line: str):
        if not self.ser or not self.ser.is_open:
            return
        try:
            self.log.info(f"SEND → {line}")     # <-- LOG SEND
            self.ser.write((line.strip() + "\n").encode())
        except Exception as e:
            self.log.error(f"USB write error: {e}")


    # ---------------------------------------------------------
    async def handle_messenger(self):
        """Příjem zpráv z MessengerServeru"""
        while self.running:
            try:
                msg = await self.sock.recv_json()
                sender = msg.get("sender")
                cmd = msg.get("cmd")

                if not sender:
                    continue

                # požadavek na stav
                if cmd == "GET_STATE":
                    await self.send_state_to(sender)
                    continue

                # přihlášení k odběru stavů
                if cmd == "SUBSCRIBE_STATE":
                    self.subscribers.add(sender)
                    self.log.info(f"{sender} subscribed")
                    await self.send_state_to(sender)
                    continue

                # SET …
                if cmd == "SET":
                    data = msg.get("data", "")
                    await self.process_set_command(data)
                    continue

            except Exception as e:
                self.log.error(f"Messenger error: {e}")
                await asyncio.sleep(0.1)

    # ---------------------------------------------------------
    async def process_set_command(self, line):
        """SET MODE … nebo SET COLOR …"""
        parts = line.split()

        if len(parts) >= 3 and parts[0] == "SET" and parts[1] == "MODE":
            mode = parts[2].upper()
            self.current_mode = mode
            await self.write_serial(line)
            await self.broadcast_state()
            return

        if len(parts) == 5 and parts[0] == "SET" and parts[1] == "COLOR":
            r = int(parts[2])
            g = int(parts[3])
            b = int(parts[4])

            self.current_color = (r, g, b)
            await self.write_serial(line)
            await self.broadcast_state()
            return

        self.log.warn(f"Unknown command: {line}")

    # ---------------------------------------------------------
    async def send_state_to(self, target):
        """Pošli stav jednomu klientovi."""
        await self.sock.send_json({
            "sender": "LED_CONTROLLER",
            "target": target,
            "state": {
                "mode": self.current_mode,
                "color": self.current_color
            }
        })

    # ---------------------------------------------------------
    async def broadcast_state(self):
        """Rozesílá stav všem odběratelům."""
        for target in self.subscribers:
            await self.send_state_to(target)

    # ---------------------------------------------------------
    async def register(self):
        """Registrace do MessengerServeru."""
        await self.sock.send_json({"sender": "LED_CONTROLLER"})
        self.log.info("Registered to MessengerServer")

    # ---------------------------------------------------------
    async def run(self):
        await self.register()
        await self.connect_serial()

        asyncio.create_task(self.handle_messenger())

        self.log.info("LED Controller ready (USB CDC mode)")

        # smyčka nic nedělá, protože všechny eventy jsou async
        while self.running:
            await asyncio.sleep(0.5)

 
# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    ctrl = LedController()
    asyncio.run(ctrl.run())
