import os
import io
import pty
import termios
import subprocess
import signal

from .base import BaseBackend

class UnixBackend(BaseBackend):
    def start(self):
        self.master, self.slave = pty.openpty()
        attrs = termios.tcgetattr(self.slave)
        attrs[3] = attrs[3] & ~termios.ECHO 
        termios.tcsetattr(self.slave, termios.TCSANOW, attrs)

        self.process = subprocess.Popen(
            self.args,
            stdin=self.slave,
            stdout=self.slave,
            stderr=subprocess.STDOUT,
            cwd=self.cwd,
            text=False,
            start_new_session=True,
        )

        os.close(self.slave)
        self.slave = None
        self.stdin = io.TextIOWrapper(os.fdopen(self.master, "rb+", buffering=0), encoding="utf-8", newline="\n", write_through=True)
        self.stdout = self.stdin
        return self

    def terminate(self):
        if self.is_running():
            self.process.terminate()

    def wait(self, timeout=None):
        if self.process:
            return self.process.wait(timeout=timeout)
    
    def kill(self):
        if self.is_running():
            self.process.kill()

    def interrupt(self):
        if self.is_running():
            os.killpg(self.process.pid, signal.SIGINT)

        
