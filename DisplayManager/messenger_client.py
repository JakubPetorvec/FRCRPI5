import os
import sys
import asyncio
import zmq
import zmq.asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from LoggerManager.logger import Logger


class MessengerServer:
    def __init__(self):
        self.name = "MessengerServer"
        self.log = Logger(self.name)
        self.ctx = zmq.asyncio.Context()

        self.router = self.ctx.socket(zmq.ROUTER)
        self.router.bind("ipc:///tmp/messenger_data.sock")

        self.targets = {}
        self.running = True

    async def run(self):
        self.log.info("MessengerServer started")
        asyncio.create_task(self.heartbeat(360))

        while self.running:
            try:
                ident, msg = await self.router.recv_multipart()

                self.log.info(f"RECV FROM {ident!r}: {msg}")

                data = zmq.utils.jsonapi.loads(msg)

                sender = data.get("sender")
                target = data.get("target")

                if sender:
                    self.targets[sender] = ident
                    self.log.debug(f"Registered client '{sender}'")

                if target:
                    if target in self.targets:
                        self.log.debug(f"Routing message to '{target}'")

                        # ★ LOG ODESÍLANOU ZPRÁVU ★
                        self.log.info(f"SEND TO {self.targets[target]!r}: {msg}")

                        self.router.send_multipart([self.targets[target], msg])
                    else:
                        self.log.warn(f"Target '{target}' is not connected")

            except Exception as e:
                self.log.error(f"Message handling error: {e}")
                await asyncio.sleep(0.1)

    async def heartbeat(self, interval):
        while self.running:
            self.log.debug("Heartbeat")
            await asyncio.sleep(interval)

    async def stop(self):
        self.running = False
        try: self.router.close(linger=0)
        except: pass
        self.log.info("MessengerServer stopped")


if __name__ == "__main__":
    asyncio.run(MessengerServer().run())
