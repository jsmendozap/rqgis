"""Manages the R execution thread to keep the QGIS UI responsive."""
from qgis.PyQt.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QMetaObject, Qt
from dataclasses import dataclass
from typing import Callable

from .utils import MissingDependencyError, RPathRequiredError
from .result import ExpressionResult
from .bridge import RBridge 

@dataclass
class BridgeCallbacks:
    on_pkg_loaded: Callable
    on_help_requested: Callable
    on_plot_server_ready: Callable

class RWorker(QObject):
    """
    A worker object that runs in a separate thread to handle R communication.

    It owns the RBridge and performs all blocking operations, communicating
    with the main GUI thread via Qt signals and slots.
    """
    initialized = pyqtSignal()        
    line_result = pyqtSignal(str, object)  
    welcome_result = pyqtSignal(object)
    run_finished = pyqtSignal()
    failed = pyqtSignal(str)
    busy_changed = pyqtSignal(bool)
    path_required = pyqtSignal()
    pkg_loaded = pyqtSignal(list)
    help_requested = pyqtSignal(str)
    plot_server = pyqtSignal(tuple)

    def __init__(self, qgis_api):
        """
        Initializes the RWorker.

        Args:
            qgis_api: The QGISApi instance for the R bridge to use.
        """
        super().__init__()
        self.bridge = None
        self.qgis_api = qgis_api

    @pyqtSlot()
    def initialize(self):
        """
        Slot to initialize the R bridge. Emits 'initialized' on success or
        'path_required'/'failed' on error.
        """
        try:
            callbacks = BridgeCallbacks(
                on_pkg_loaded=self._on_pkg_loaded,
                on_help_requested=self._on_help_requested,
                on_plot_server_ready=self._on_plot_server_ready
            )
            self.bridge = RBridge(self.qgis_api, callbacks)
            self.bridge.initialize()
            self.initialized.emit()
        except RPathRequiredError:
            self.path_required.emit()
        except MissingDependencyError as e:
            self.failed.emit(f"{e}")
        except Exception as e:
            if self.bridge is not None:
                self.bridge.stop()
                self.bridge = None
            self.failed.emit(f"Failed to initialize R Console: {e}")

    @pyqtSlot(str, int)
    def run_code_block(self, code, width):
        """
        Slot to execute a block of R code.

        Iterates through the results from the bridge and emits signals for each
        piece of output.

        Args:
            code (str): The R code to run.
            width (int): The console width for formatting.
        """
        if self.bridge is None:
            self.failed.emit("R bridge is not initialized.")
            self.run_finished.emit()
            return

        self.busy_changed.emit(True)
        try:
            for result in self.bridge.run_code(code, width=width):
                if isinstance(result, ExpressionResult):
                    self.line_result.emit(result.expression, result)
                else:
                    self.line_result.emit("", result)
        except Exception as e:
            self.failed.emit(f"Execution error: {e}")
        finally:
            self.busy_changed.emit(False)
            self.run_finished.emit()

    @pyqtSlot(int)
    def run_welcome(self, width):
        """
        Slot to run the welcome script and emit the result.

        Args:
            width (int): The console width.
        """
        if self.bridge is None:
            return
        try:
            result = self.bridge.run_welcome(width=width)
            self.welcome_result.emit(result)
        except Exception as e:
            self.failed.emit(f"Welcome message error: {e}")

    @pyqtSlot()
    def restart_r(self):
        """Slot to restart the R process."""
        if self.bridge:
            try:
                self.bridge.restart()
                self.initialized.emit()
            except Exception as e:
                self.failed.emit(f"Failed to restart R: {e}")

    @pyqtSlot()
    def shutdown(self):
        """Slot to gracefully stop the R bridge."""
        try:
            if self.bridge is not None:
                self.bridge.stop()
        except Exception:
            pass
        finally:
            self.bridge = None

    @pyqtSlot(str)
    def change_wd(self, path):
        """
        Slot to change the working directory in the R process.

        Args:
            path (str): The new working directory path.
        """
        if self.bridge:
            try:
                path = path.replace('\\', '/').replace('"', '\\"')
                for _ in self.bridge.run_code(f'setwd("{path}")'):
                    pass
            except Exception as e:
                self.failed.emit(f"Failed to change working directory: {e}")

    def _on_pkg_loaded(self, signatures):
        """
        Callback for when the R bridge reports a package has been loaded.

        Args:
            signatures (list): A list of function signatures from the loaded package.
        """
        self.pkg_loaded.emit(signatures)

    def _on_help_requested(self, path):
        """
        Callback for when the R bridge requests help.

        Args:
            path (str): The path to the html help file.
        """
        self.help_requested.emit(path)

    def _on_plot_server_ready(self, port, token):
        """
        Callback for when the R bridge reports the plot server is ready.

        Args:
            port (int): The port number where the plot server is listening.
            token (str): A token for authenticating with the plot server.
        """
        self.plot_server.emit((port, token))


class RRunner(QObject):
    """
    Manages the RWorker and its QThread, providing a clean API for the GUI.

    This class is the main entry point for the GUI to interact with the R
    process. It forwards requests to the RWorker in the background thread
    and connects the worker's signals to the appropriate slots in the GUI.
    """
    initialized = pyqtSignal()
    line_result = pyqtSignal(str, object)
    welcome_result = pyqtSignal(object)
    run_finished = pyqtSignal()
    failed = pyqtSignal(str)
    busy_changed = pyqtSignal(bool)
    path_required = pyqtSignal()
    request_initialize = pyqtSignal()
    request_run = pyqtSignal(str, int)
    request_welcome = pyqtSignal(int)
    request_restart = pyqtSignal()
    request_change_wd = pyqtSignal(str)
    pkg_loaded = pyqtSignal(list)
    help_requested = pyqtSignal(str)
    plot_server = pyqtSignal(tuple)

    def __init__(self, qgis_api):
        """
        Initializes the RRunner, creating and starting the background thread.

        Args:
            qgis_api: The QGISApi instance to be passed to the worker.
        """
        super().__init__()
        self._thread = QThread()
        self._worker = RWorker(qgis_api)
        self._worker.moveToThread(self._thread)
        self._connect_request_signals()
        self._connect_woker_signals()
        self._thread.start()

    def initialize(self):
        """Requests the worker to initialize the R bridge."""
        self.request_initialize.emit()

    def run(self, code, width):
        """
        Requests the worker to run a block of R code.

        Args:
            code (str): The R code to run.
            width (int): The console width.
        """
        self.request_run.emit(code, width)

    def welcome_message(self, width):
        """
        Requests the worker to run the welcome script.

        Args:
            width (int): The console width.
        """
        self.request_welcome.emit(width)

    def restart_r(self):
        """Requests the worker to restart the R process."""
        self.request_restart.emit()

    def stop(self):
        """Stops the worker and waits for the thread to terminate."""
        QMetaObject.invokeMethod(
            self._worker,
            "shutdown",
            Qt.BlockingQueuedConnection
        )
        self._thread.quit()
        self._thread.wait()

    def change_wd(self, path):
        """
        Requests the worker to change the R working directory.

        Args:
            path (str): The new path.
        """
        self.request_change_wd.emit(path)

    def _connect_woker_signals(self):
        """Connects signals from the worker to this object's signals."""
        self._worker.initialized.connect(self.initialized)
        self._worker.path_required.connect(self.path_required)
        self._worker.line_result.connect(self.line_result)
        self._worker.welcome_result.connect(self.welcome_result)
        self._worker.run_finished.connect(self.run_finished)
        self._worker.failed.connect(self.failed)
        self._worker.busy_changed.connect(self.busy_changed)
        self._worker.pkg_loaded.connect(self.pkg_loaded)
        self._worker.help_requested.connect(self.help_requested)
        self._worker.plot_server.connect(self.plot_server)

    def _connect_request_signals(self):
        """Connects this object's request signals to the worker's slots."""
        self.request_initialize.connect(self._worker.initialize)
        self.request_run.connect(self._worker.run_code_block)
        self.request_welcome.connect(self._worker.run_welcome)
        self.request_restart.connect(self._worker.restart_r)
        self.request_change_wd.connect(self._worker.change_wd)
        