from . import plugin_settings
from shutil import which
import subprocess
import json
import os

class RPathRequiredError(RuntimeError):
    pass

class MissingDependencyError(RuntimeError):
    pass


class RResult(dict):
    def __init__(self, msg):
        super().__init__()
        self.stdout = ""
        self.error = None
        self.wd = None
        self.expression = None
        self.is_done = False
        self._parse(msg)

    def _parse(self, msg):
        match msg["type"]:
            case "expression":
                self.expression = msg["data"]
            case "chunk":
                self.stdout = msg["data"]
                self.wd = msg.get("wd")
                self.update(stdout=self.stdout, error=None, wd=self.wd)
            case "done":
                self.error = msg.get("error")
                self.wd = msg.get("wd")
                self.is_done = True
                self.update(stdout="", error=self.error, wd=self.wd)
            case "error":
                self.error = msg.get("data")
                self.is_done = True
                self.update(stdout="", error=self.error, wd=None)
            case "missing":
                raise MissingDependencyError(f"The following R packages are required but are not installed: {msg['data']}")

    def __bool__(self):
        return not self.is_done
    

class RBridge:
    def __init__(self):
        self.plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.process = None
        self.r = self._find_rscript()

    def initialize(self):
        self.process = self._start()
        self._set_wd()
        
    def run_code(self, code, width=None):
        data = {"code": code}
        if width:
            data["width"] = int(width)
        request = json.dumps(data) + "\n"

        self.process.stdin.write(request)
        self.process.stdin.flush()

        while True:
            response = self.process.stdout.readline().strip()
            if not response:
                raise RuntimeError("R process ended unexpectedly.")
            
            result = RResult(json.loads(response))
            print(result)
            yield result
            if result.is_done:
                break
    
    def run_welcome(self,width=None):
        code = "\n".join([
        'cat(R.version.string, "\\n")',
        'cat("Running under", format(utils::osVersion), "\\n")',
        ])

        stdout = ""
        wd = None

        for result in self.run_code(code, width=width):
            if not result.is_done:
                stdout += result.stdout
            else:
                wd = result.wd
        
        return RResult({"type": "chunk", "data": stdout, "wd": wd})

    def stop(self):
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)

    def restart(self):
        self.stop()
        self.process = self._start()
            
    def _start(self):
        base = os.path.basename(self.r).lower()
        args = [self.r, "--vanilla"]
        
        if "rscript" not in base:
            args.extend(["--slave", "-f", "r_worker.R"])
        else:
            args.append("r_worker.R")

        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0

        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.plugin_dir, 
            creationflags=creationflags
        )

        ready = process.stdout.readline().strip()
        if ready != "READY":
            process.kill()
            raise RuntimeError(f"Failed to start R worker process.")
        
        return process     
    
    def _find_rscript(self):
        saved = plugin_settings.get_r_path()
        if saved:
            return saved
        
        path = which('Rscript')
        if path:
            return path
        
        raise RPathRequiredError("R/Rscript not found.")

    def _set_wd(self):
        wd = plugin_settings.get_initial_wd()
        wd = wd.replace('\\', '/').replace('"', '\\"')
        for _ in self.run_code(f'setwd("{wd}")'): 
            pass
