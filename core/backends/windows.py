import os
try:
    from pywinpty import PtyProcess
except ImportError:
    PtyProcess = None

from .base import BaseBackend

class WindowsBackend(BaseBackend):
    def start(self):
        if PtyProcess is None:
            raise ImportError("pywinpty is not available")
        
        self.process = PtyProcess.spawn(self.args, cwd=self.cwd, env=os.environ.copy())
        self.stdin = self.process
        self.stdout = self.process
        return self
    
    def is_running(self):
        return self.process is not None and self.process.isalive()

    def terminate(self):
        if self.is_running():
            self.process.terminate()

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
        if self.is_running():
            self.process.kill()

    def interrupt(self):
        if self.is_running():
            self.process.sendintr()