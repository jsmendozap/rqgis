import os
import subprocess

from .base import BaseBackend

class PipesBackend(BaseBackend):
    def start(self):
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        self.process = subprocess.Popen(
            self.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=0,
            cwd=self.cwd,
            creationflags=creationflags,
            start_new_session=False if os.name == "nt" else True,
        )
        self.stdin = self.process.stdin
        self.stdout = self.process.stdout
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
        return