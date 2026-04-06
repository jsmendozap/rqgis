from qgis.PyQt.QtCore import QMetaObject, Qt, Q_ARG
from .result import RResult, RequestResult, PkgResult, HelpResult, PlotServerResult, DoneResult
from .utils import RPathRequiredError, root_dir
from .logger import SessionLogger
from . import plugin_settings
from shutil import which
import subprocess
import json
import os
import signal

class RBridge:
    """Handles the lifecycle and communication with the R subprocess."""

    def __init__(self, qgis_api, callbacks):
        """
        Initializes the RBridge.

        Args:
            qgis_api: An instance of QGISApi to handle requests from R.
            callbacks: An instance of BridgeCallbacks containing the callback functions.
        """
        self.plugin_dir = root_dir()
        self.process = None
        self.qgis_api = qgis_api
        self.r = self._find_rscript()
        self.callbacks = callbacks
        
        if plugin_settings.get_status_debug():
            log_dir = plugin_settings.get_log_dir().strip()
            self._logger = SessionLogger(log_dir)
        else:
            self._logger = None

    def initialize(self):
        """Starts the R subprocess and sets the initial working directory."""
        self.process = self._start()
        self._set_wd()
        
    def run_code(self, code, width=None):
        """
        Executes R code and yields results as they are received.

        This is a generator that sends code to the R process and then listens for
        responses. It handles standard output, errors, and special "request"
        messages from R that require interaction with the QGIS API.

        Args:
            code (str): The R code to execute.
            width (int, optional): The console width in characters, used for
                                   formatting R output. Defaults to None.

        Yields:
            RResult: An object representing a message from the R process.
        """

        QMetaObject.invokeMethod(self.qgis_api, "check_update", Qt.BlockingQueuedConnection)
        if self.qgis_api.result:
            self._send_project_update(type="update")

        data = {"type": "code", "code": code.replace('\r\n', '\n'), "width": width}
        request = json.dumps(data) + "\n"
        self._log(1, request)
        self.process.stdin.write(request)
        self.process.stdin.flush()

        while True:
            response = self.process.stdout.readline().strip()
            self._log(2, response)
            if not response:
                raise RuntimeError("R process ended unexpectedly.")
            
            result = RResult.from_msg(json.loads(response))

            if isinstance(result, RequestResult):
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

            if isinstance(result, PkgResult):
                self.callbacks.on_pkg_loaded(result.signatures)
                continue

            if isinstance(result, HelpResult):
                self.callbacks.on_help_requested(result.html)
                continue

            if isinstance(result, PlotServerResult):
                self.callbacks.on_plot_server_ready(result.port, result.token)
                continue

            yield result
            if isinstance(result, DoneResult):
                break
    
    def run_welcome(self,width=None):
        """
        Executes a predefined script to get the R version and OS info.

        Args:
            width (int, optional): The console width. Defaults to None.

        Returns:
            RResult: A result object containing the welcome message.
        """
        code = "\n".join([
        'cat(R.version.string, "\\n")',
        'cat("Running on", format(utils::osVersion), "\\n")',
        ])

        stdout = ""
        wd = None

        for result in self.run_code(code, width=width):
            if not isinstance(result, DoneResult):
                stdout += result.stdout
            else:
                wd = result.wd
        
        return RResult.from_msg({"type": "chunk", "data": stdout, "wd": wd})

    def stop(self):
        """Terminates the R subprocess gracefully."""
        if self.process.poll() is not None:
            return
        self.process.terminate()
        if self._logger:
            self._logger.close()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)

    def restart(self):
        """Stops and then restarts the R subprocess."""
        self.stop()
        self.process = self._start()

    def interrupt(self):
        """Sends an interrupt signal to the R subprocess to stop current execution."""
        if self.process and self.process.poll() is None:
            if os.name == 'nt':
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.kill(self.process.pid, signal.SIGINT)
                
    def _start(self):
        """
        Launches the R worker subprocess.

        Constructs the command to run the `main.R` script and starts it,
        establishing stdin/stdout pipes for communication.

        Raises:
            RuntimeError: If the R worker process fails to start and send the
                          "READY" signal.

        Returns:
            subprocess.Popen: The Popen object for the running R process.
        """
        base = os.path.basename(self.r).lower()
        worker = os.path.join(self.plugin_dir, "main.R")
        args = [self.r, "--vanilla"]
        
        if "rscript" not in base:
            args.extend(["--slave", "-f", f"{worker}", "--args", f"{self.plugin_dir}"])
        else:
            args.extend([f"{worker}", f"{self.plugin_dir}"])
        
        creationflags = 0
        if os.name == 'nt':
            creationflags = subprocess.CREATE_NO_WINDOW | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)

        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=0,
            cwd=self.plugin_dir, 
            creationflags=creationflags, 
            start_new_session= True if not os.name == 'nt' else False
        )

        ready = process.stdout.readline().strip()
        if ready != "READY":
            process.kill()
            if self._logger:
                try:
                    remainder = process.stdout.read()
                except Exception:
                    remainder = ""
                self._logger.log(2, remainder)
            raise RuntimeError(f"Failed to start R worker process. Error: {ready}")
        
        return process     
    
    def _send_project_update(self, type):
        """
        Sends the current QGIS project state to the R process.

        Args:
            type (str): The type of update message (e.g., "update").
        """
        QMetaObject.invokeMethod(
            self.qgis_api, "dispatch",
            Qt.BlockingQueuedConnection,
            Q_ARG('PyQt_PyObject', {"method": "project_state"})
        )
        state = self.qgis_api.result
        msg = {"type": f"{type}", "data": state}
        self.process.stdin.write(json.dumps(msg) + "\n")
        self.process.stdin.flush()

    def _find_rscript(self):
        """
        Finds the path to the Rscript executable.

        It first checks the plugin settings, then searches the system's PATH.

        Raises:
            RPathRequiredError: If Rscript cannot be found.

        Returns:
            str: The absolute path to the Rscript executable.
        """
        saved = plugin_settings.get_r_path()
        if saved:
            return saved
        
        path = which('Rscript')
        if path:
            return path
        
        raise RPathRequiredError("R/Rscript not found.")

    def _set_wd(self):
        """Sets the initial working directory in the R session."""
        wd = plugin_settings.get_initial_wd()
        wd = wd.replace('\\', '/').replace('"', '\\"')
        for _ in self.run_code(f'setwd("{wd}")'): 
            pass

    def _log(self, direction, data):
        """Logs a message to the session logger if it is enabled."""
        if self._logger:
            self._logger.log(direction, data)
