# /home/dickin/FRC/ProgramManager/program_manager.py
import asyncio
import json
import os
import signal
import subprocess
from datetime import datetime, timedelta

import zmq
import zmq.asyncio


PROGRAMS_JSON = "/home/dickin/FRC/ProgramManager/programs.json"
LOG_SOCK_ADDR = "ipc:///tmp/messenger_logs.sock"
HB_SOCK_ADDR  = "ipc:///tmp/messenger_heartbeat.sock"

HEARTBEAT_WARN_S = 15
HEARTBEAT_OK_EVERY_S = 10


class ProgramManager:
    def __init__(self):
        self.ctx = zmq.asyncio.Context.instance()

        # ProgramManager = server → BIND
        self.log_sub = self.ctx.socket(zmq.SUB)
        self.log_sub.bind(LOG_SOCK_ADDR)
        self.log_sub.setsockopt_string(zmq.SUBSCRIBE, "")

        self.hb_sub = self.ctx.socket(zmq.SUB)
        self.hb_sub.bind(HB_SOCK_ADDR)
        self.hb_sub.setsockopt_string(zmq.SUBSCRIBE, "")

        self.running = True
        self.processes: dict[str, subprocess.Popen] = {}
        self.last_heartbeat: dict[str, datetime] = {}
        self._tasks: list[asyncio.Task] = []
        self._last_ok_print = datetime.min

    async def run(self):
        self._log_self("Spuštěn...")

        # signály pro čisté ukončení
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.request_stop)
            except NotImplementedError:
                pass

        await self._start_programs()

        # paralelní tasky
        self._tasks = [
            asyncio.create_task(self._read_logs(), name="read_logs"),
            asyncio.create_task(self._read_heartbeats(), name="read_heartbeats"),
            asyncio.create_task(self._watchdog(), name="watchdog"),
        ]

        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await self._shutdown()

    async def _start_programs(self):
        with open(PROGRAMS_JSON, "r", encoding="utf-8") as f:
            programs = json.load(f)

        for p in programs:
            proc = subprocess.Popen(["python3", p["path"]])
            self.processes[p["name"]] = proc
            self._log_line(p["name"], f"Spuštěno (PID {proc.pid})")

    async def _read_logs(self):
        """Čte logy z ostatních modulů a formátuje je jednotně."""
        try:
            while self.running:
                try:
                    msg = await asyncio.wait_for(self.log_sub.recv_json(), timeout=0.2)
                except asyncio.TimeoutError:
                    continue
                except zmq.error.ContextTerminated:
                    break

                ts = msg.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                sender = msg.get("sender", "?")
                text = (msg.get("message") or "").strip()

                if not text:
                    continue

                # 📜 Jednotný styl výpisu:
                print(f"[{ts}] - [{sender}] : {text}")
        except asyncio.CancelledError:
            pass

    async def _read_heartbeats(self):
        try:
            while self.running:
                try:
                    msg = await asyncio.wait_for(self.hb_sub.recv_json(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                except zmq.error.ContextTerminated:
                    break

                sender = msg.get("sender")
                if sender:
                    self.last_heartbeat[sender] = datetime.now()
        except asyncio.CancelledError:
            pass

    async def _watchdog(self):
        try:
            while self.running:
                await asyncio.sleep(1)
                now = datetime.now()

                # detekce ztracených heartbeatů
                for name, last in list(self.last_heartbeat.items()):
                    if (now - last).total_seconds() > HEARTBEAT_WARN_S:
                        self._log_line("ProgramManager", f"{name} neposlal heartbeat déle než {HEARTBEAT_WARN_S}s")

                # periodický "Všechno OK"
                if (now - self._last_ok_print) > timedelta(seconds=HEARTBEAT_OK_EVERY_S):
                    all_ok = True
                    for name, proc in self.processes.items():
                        if proc.poll() is not None:
                            all_ok = False
                            break
                        last = self.last_heartbeat.get(name)
                        if not last or (now - last).total_seconds() > HEARTBEAT_WARN_S:
                            all_ok = False
                    if all_ok:
                        self._log_line("ProgramManager", "Všechno OK ❤️")
                    self._last_ok_print = now
        except asyncio.CancelledError:
            pass

    def request_stop(self):
        if not self.running:
            return
        self.running = False
        self._log_line("ProgramManager", "Zachycen signál k ukončení, vypínám všechny procesy...")
        for t in self._tasks:
            t.cancel()

    async def _shutdown(self):
        await asyncio.gather(*self._tasks, return_exceptions=True)

        for s in (self.log_sub, self.hb_sub):
            try:
                s.close(linger=0)
            except Exception:
                pass

        for name, proc in list(self.processes.items()):
            if proc.poll() is None:
                try:
                    self._log_line("ProgramManager", f"Ukončuji proces {name} (PID {proc.pid})")
                    proc.terminate()
                    proc.wait(timeout=5)
                    self._log_line("ProgramManager", f"{name} ukončen.")
                except Exception:
                    proc.kill()
        self.processes.clear()

        try:
            self.ctx.term()
        except Exception:
            pass

        self._log_line("ProgramManager", "ProgramManager končí.")

    # pomocné formátovací metody
    def _log_line(self, sender, text):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] - [{sender}] : {text}")

    def _log_self(self, text):
        self._log_line("ProgramManager", text)


if __name__ == "__main__":
    asyncio.run(ProgramManager().run())
