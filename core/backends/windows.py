try:
    from winpty import PtyProcess
except ImportError:
    PtyProcess = None

from .base import BaseBackend
import re

_ANSI_RE = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]')

class _CRLFWriter:
    def __init__(self, proc, on_write=None):
        self._proc = proc
        self._on_write = on_write

    def write(self, s):
        if self._on_write:
            self._on_write(s)
        return self._proc.write(s.replace('\n', '\r\n'))

    def flush(self):
        self._proc.flush()


class WindowsBackend(BaseBackend):

    def __init__(self, args, cwd=None):
        super().__init__(args, cwd)
        self._proc = None
        self._last_written = None

    def start(self):
        if PtyProcess is None:
            raise ImportError("winpty is not available")
        self._proc = PtyProcess.spawn(self.args, cwd=self.cwd)
        self.process = self._proc
        self.stdin = _CRLFWriter(self._proc, on_write=self._track_write)
        self.stdout = self._proc
        return self

    def _track_write(self, s):
        self._last_written = _ANSI_RE.sub('', s).strip()

    def readline(self):
        while True:
            try:
                line = self._proc.readline()
            except EOFError:
                return ""
            clean = _ANSI_RE.sub('', line)
            if self._last_written and clean.strip() == self._last_written:
                self._last_written = None
                continue
            return clean

    def is_running(self):
        return self.process is not None and self.process.isalive()

    def terminate(self):
        if self.is_running():
            self.process.terminate(force=False)

    def wait(self, timeout=None):
        if not self.process:
            return
        if timeout is None:
            self.process.wait()
            return
        import time
        deadline = time.time() + timeout
        while self.is_running() and time.time() < deadline:
            time.sleep(0.05)

    def kill(self):
        if self.is_running():
            self.process.terminate(force=True)

    def interrupt(self):
        if self.is_running():
            self.process.sendintr()

    def __str__(self):
        return "WindowsPty"