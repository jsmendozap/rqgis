from qgis.PyQt.QtWidgets import QInputDialog
from shutil import which
from subprocess import Popen, PIPE
import json
import os

class RBridge:
    def __init__(self, plugin_dir):
        self.plugin_dir = plugin_dir
        self.r = 'Rscript' if which('Rscript') is not None else self._request_r_path()
        self.process = self._start()
        
    def _request_r_path(self):

        if 'r_path.json' in os.listdir(self.plugin_dir):
            with open(os.path.join(self.plugin_dir, 'r_path.json'), 'r') as f:
                data = json.load(f)
                return data['path']

        path, ok = QInputDialog.getText(
            None,
            "R Not Found in PATH",
            "Enter the path to Rscript:"
        )
        if not ok or not path.strip():
            raise RuntimeError("Rscript path not found.")
        
        with open(os.path.join(self.plugin_dir, 'r_path.json'), 'w') as f:
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
        print(ready)

        if ready != "READY":
            raise RuntimeError("Failed to start R worker process.")
        
        return process     

    def run_code(self, code):
        request = json.dumps({"code": code}) + "\n"
        print(request)
        self.process.stdin.write(request)
        self.process.stdin.flush()

        response = self.process.stdout.readline().strip()
        print(response)
        return json.loads(response.strip())
    
    def stop(self):
        self.process.terminate()

    def restart(self):
        self.stop()
        self.process, self.stderr_thread = self._start()
