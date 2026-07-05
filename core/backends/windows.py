import os
import threading
import queue
try:
    from winpty import PtyProcess
except ImportError:
    PtyProcess = None

from .base import BaseBackend

class WindowsBackend(BaseBackend):

    def __init__(self, args, cwd=None):
        super().__init__(args, cwd)
        self._proc = None
        self._reader = None
        self._queue = queue.Queue()
        self._stop = threading.Event()

    def start(self):
        if PtyProcess is None:
            raise ImportError("winpty is not available")
        self._proc = PtyProcess.spawn(self.args, cwd=self.cwd, env=os.environ.copy())
        self.process = self._proc
        self.stdin = self._proc
        self.stdout = self._proc
        self._reader = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader.start()
        return self
        
    def _reader_loop(self):
        while not self._stop.is_set() and self._proc and self._proc.isalive():
            try:
                data = self._proc.read(4096)
            except EOFError:
                break
            if not data:
                break
            self._queue.put(data if isinstance(data, str) else data.decode("utf-8", errors="replace"))    

    def readline(self):
        try:
            return self._queue.get(timeout=0.1)
        except queue.Empty:
            return ""

    def is_running(self):
        return self.process is not None and self.process.isalive()

    def terminate(self):
        self._stop.set()
        if self.is_running():
            self.process.terminate()
        if self._reader is not None:
            self._reader.join(timeout=1.0)

    def wait(self, timeout=None):
        if not self.process:
            return
        if timeout is None:
            while self.is_running():
                pass
            return
        import time
        deadline = time.time() + timeout
        while self.is_running() and time.time() < deadline:
            time.sleep(0.05)

    def kill(self):
        self._stop.set()
        if self.is_running():
            self.process.kill()
        if self._reader is not None:
            self._reader.join(timeout=1.0)

    def interrupt(self):
        if self.is_running():
            self.process.sendintr()

    def __str__(self):
        return "WindowsPty"