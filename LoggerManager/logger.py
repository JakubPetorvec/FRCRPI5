import time

class Logger:
    def __init__(self, name: str):
        self.name = name

    def _log(self, level, message):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [{level.upper()}] {message}", flush=True)

    def info(self, msg): self._log("info", msg)
    def warn(self, msg): self._log("warn", msg)
    def error(self, msg): self._log("error", msg)
    def debug(self, msg): self._log("debug", msg)
