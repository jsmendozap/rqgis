from qgis.PyQt.QtWidgets import QInputDialog
from shutil import which
from subprocess import Popen, PIPE
import json
import os

class RBridge:
    def __init__(self, plugin_dir, popup = False):
        self.plugin_dir = plugin_dir
        self.popup = popup
        self.r = 'Rscript' if which('Rscript') is not None else self._request_r_path()
        self.process = self._start()
        self.r_version = self._get_r_version()
        self._set_home()
        
    def _request_r_path(self):

        settings = os.path.join(self.plugin_dir, 'settings.json')
        if os.path.exists(settings):
            try:
                with open(settings, 'r') as f:
                    data = json.load(f)
                    return data['path']
            except Exception:
                pass 

        if not self.popup:
            raise RuntimeError("Rscript not found in PATH.")

        path, ok = QInputDialog.getText(
            None,
            "R Not Found in PATH",
            "Enter the path to Rscript:"
        )
        
        if not ok or not path.strip():
            raise RuntimeError("Rscript path not found.")
        
        with open(os.path.join(self.plugin_dir, 'settings.json'), 'w') as f:
            json.dump({'path': path.strip()}, f)
            return path.strip()
            
    def _start(self):
        base = os.path.basename(self.r).lower()
        args = [self.r, "--vanilla"]
        
        if "rscript" not in base:
            args.extend(["--slave", "-f", "r_worker.R"])
        else:
            args.append("r_worker.R")

        process = Popen(
            args,
            stdin=PIPE, 
            stdout=PIPE, 
            stderr=PIPE, 
            text=True,
            bufsize=1,
            cwd=self.plugin_dir
        )

        ready = process.stdout.readline().strip()

        if ready != "READY":
            raise RuntimeError("Failed to start R worker process.")
        
        return process     

    def run_code(self, code, width=None):
        data = {"code": code}
        if width:
            data["width"] = int(width)
        request = json.dumps(data) + "\n"

        self.process.stdin.write(request)
        self.process.stdin.flush()

        response = self.process.stdout.readline().strip()
            
        return json.loads(response.strip())
    
    def stop(self):
        self.process.terminate()

    def restart(self):
        self.stop()
        self.process = self._start()
        self.r_version = self._get_r_version()

    def _get_r_version(self):
        code = "cat(paste0(R.Version()$major, '.', R.Version()$minor))"
        response = self.run_code(code)
        return response["stdout"].strip()
    
    def _set_home(self):
        code = f"setwd('{os.path.expanduser('~')}')"
        self.run_code(code)
