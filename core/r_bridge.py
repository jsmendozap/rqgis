from qgis.PyQt.QtCore import QMetaObject, Qt, Q_ARG
from .r_result import RResult
from .utils import RPathRequiredError
from . import plugin_settings
from shutil import which
import subprocess
import json
import os

class RBridge:
    def __init__(self, qgis_api):
        self.plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.process = None
        self.qgis_api = qgis_api
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
            print(response)
            if not response:
                raise RuntimeError("R process ended unexpectedly.")
            
            result = RResult(json.loads(response))

            if result.is_request:
                QMetaObject.invokeMethod(
                    self.qgis_api,
                    "dispatch",
                    Qt.BlockingQueuedConnection,
                    Q_ARG('PyQt_PyObject', {"method": result.method, "args": result.args})
                )
                
                qgis_response = self.qgis_api.result

                self.process.stdin.write(json.dumps(qgis_response) + "\n")
                self.process.stdin.flush()
                continue 

            yield result
            if result.is_done:
                break
    
    def run_welcome(self,width=None):
        code = "\n".join([
        'cat(R.version.string, "\\n")',
        'cat("Running on", format(utils::osVersion), "\\n")',
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
        worker = os.path.join(self.plugin_dir, "main.R")
        args = [self.r, "--vanilla"]
        
        if "rscript" not in base:
            args.extend(["--slave", "-f", f"{worker}"])
        else:
            args.append(f"{worker}")

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
