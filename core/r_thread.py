from qgis.PyQt.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QMetaObject, Qt
from .utils import MissingDependencyError, RPathRequiredError
from .r_bridge import RBridge 


class RWorker(QObject):
    initialized = pyqtSignal()        
    line_result = pyqtSignal(str, dict)  
    welcome_result = pyqtSignal(dict)
    run_finished = pyqtSignal()
    failed = pyqtSignal(str)
    busy_changed = pyqtSignal(bool)
    path_required = pyqtSignal()
    pkg_loaded = pyqtSignal(list)

    def __init__(self, qgis_api):
        super().__init__()
        self.bridge = None
        self.qgis_api = qgis_api

    @pyqtSlot()
    def initialize(self):
        try:
            self.bridge = RBridge(self.qgis_api, self._on_pkg_loaded)
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
        if self.bridge is None:
            self.failed.emit("R bridge is not initialized.")
            self.run_finished.emit()
            return

        self.busy_changed.emit(True)
        try:
            for result in self.bridge.run_code(code, width=width):
                if result.expression:
                    self.line_result.emit(result.expression, result)
                elif result:
                    self.line_result.emit("", result)
                else:
                    self.line_result.emit("", result)
        except Exception as e:
            self.failed.emit(f"Execution error: {e}")
        finally:
            self.busy_changed.emit(False)
            self.run_finished.emit()

    @pyqtSlot(int)
    def run_welcome(self, width):
        if self.bridge is None:
            return
        try:
            result = self.bridge.run_welcome(width=width)
            self.welcome_result.emit(result)
        except Exception as e:
            self.failed.emit(f"Welcome message error: {e}")

    @pyqtSlot()
    def restart_r(self):
        if self.bridge:
            try:
                self.bridge.restart()
                self.initialized.emit()
            except Exception as e:
                self.failed.emit(f"Failed to restart R: {e}")

    @pyqtSlot()
    def shutdown(self):
        try:
            if self.bridge is not None:
                self.bridge.stop()
        except Exception:
            pass
        finally:
            self.bridge = None

    @pyqtSlot(str)
    def change_wd(self, path):
        if self.bridge:
            try:
                path = path.replace('\\', '/').replace('"', '\\"')
                for _ in self.bridge.run_code(f'setwd("{path}")'):
                    pass
            except Exception as e:
                self.failed.emit(f"Failed to change working directory: {e}")

    def _on_pkg_loaded(self, signatures):
        self.pkg_loaded.emit(signatures)


class RRunner(QObject):
    initialized = pyqtSignal()
    line_result = pyqtSignal(str, dict)
    welcome_result = pyqtSignal(dict)
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

    def __init__(self, qgis_api):
        super().__init__()
        self._thread = QThread()
        self._worker = RWorker(qgis_api)
        self._worker.moveToThread(self._thread)
        self._connect_request_signals()
        self._connect_woker_signals()
        self._thread.start()

    def initialize(self):
        self.request_initialize.emit()

    def run(self, code, width):
        self.request_run.emit(code, width)

    def welcome_message(self, width):
        self.request_welcome.emit(width)

    def restart_r(self):
        self.request_restart.emit()

    def stop(self):
        QMetaObject.invokeMethod(
            self._worker,
            "shutdown",
            Qt.BlockingQueuedConnection
        )
        self._thread.quit()
        self._thread.wait()

    def change_wd(self, path):
        self.request_change_wd.emit(path)

    def _connect_woker_signals(self):
        self._worker.initialized.connect(self.initialized)
        self._worker.path_required.connect(self.path_required)
        self._worker.line_result.connect(self.line_result)
        self._worker.welcome_result.connect(self.welcome_result)
        self._worker.run_finished.connect(self.run_finished)
        self._worker.failed.connect(self.failed)
        self._worker.busy_changed.connect(self.busy_changed)
        self._worker.pkg_loaded.connect(self.pkg_loaded)

    def _connect_request_signals(self):
        self.request_initialize.connect(self._worker.initialize)
        self.request_run.connect(self._worker.run_code_block)
        self.request_welcome.connect(self._worker.run_welcome)
        self.request_restart.connect(self._worker.restart_r)
        self.request_change_wd.connect(self._worker.change_wd)
        