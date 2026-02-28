from qgis.PyQt.QtWidgets import QAction, QInputDialog
from qgis.core import Qgis
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from enum import Enum, auto
import os

from .ui.dock_widget import RDockWidget
from .core.r_thread import RRunner
from .core import plugin_settings
from .core import utils

class RSessionState(Enum):
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    FAILED = auto()

class Console:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dock = None
        self.runner = None
        self._state = RSessionState.UNINITIALIZED
        self._allow_path_popup = False
        self._pending_code = None

    def initGui(self):
        self.action = QAction(
            QIcon(os.path.join(self.plugin_dir, "Rlogo.png")),
            "R Console",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removeToolBarIcon(self.action)
            self.action = None

        self._stop_runner()

        if self.dock is not None:
            self.dock.deleteLater()
            self.dock = None

    def run(self):
        if self.dock is None:
            self.dock = RDockWidget(self.iface.mainWindow())
            self.dock.runRequested.connect(self._on_run_requested)
            self.dock.restartRequested.connect(self._on_restart_requested)
            self.dock.changeWd.connect(self._on_change_wd)
            self.dock.closing.connect(self._stop_runner)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

        self._ensure_runner(False)

        self.dock.show()
        self.dock.raise_()

    def _start_runner(self):
        self.runner = RRunner()
        self.runner.initialized.connect(self._on_runner_initialized)
        self.runner.path_required.connect(self._on_path_required)
        self.runner.line_result.connect(self.dock.append_result)
        self.runner.welcome_result.connect(self.dock.append_welcome)
        self.runner.run_finished.connect(self._on_runner_finished)
        self.runner.failed.connect(self._on_runner_failed)
        self.runner.busy_changed.connect(self.dock.executionStateChanged.emit)

    def _stop_runner(self):
        if self.runner is not None:
            self.runner.stop()
            self.runner = None

        self._state = RSessionState.UNINITIALIZED
        self._pending_code = None
        self.dock.clean_console(prompt=False)

    def _ensure_runner(self, popup):
        self._allow_path_popup = popup
        try:
            if self.runner is None:
                self._start_runner()
            if self._state == RSessionState.UNINITIALIZED:
                self._state = RSessionState.INITIALIZING
                self.runner.initialize()
            return True
        except Exception as e:
            self.iface.messageBar().pushMessage("R Console Error", str(e), Qgis.Warning)
            return False

    def _on_run_requested(self, code):
        if not code.strip():
            return

        if not self._ensure_runner(True):
            return

        if self._state != RSessionState.READY:
            if self._pending_code is None:
                self._pending_code = code
            return

        self.runner.run(code, self.dock.console_width())

    def _on_runner_initialized(self):
        self._state = RSessionState.READY
        self.runner.welcome_message(self.dock.console_width())
        self.dock.new_console_prompt()

        if self._pending_code:
            code, self._pending_code = self._pending_code, None
            self.runner.run(code, self.dock.console_width())

    def _on_runner_finished(self):
        self.dock.new_console_prompt()

    def _on_runner_failed(self, msg):
        self._state = RSessionState.FAILED
        self._pending_code = None
        self.iface.messageBar().pushMessage("R Console Error", msg, Qgis.Warning)

    def _on_path_required(self):
        if not self._allow_path_popup:
            self._on_runner_failed("Rscript not found in PATH.")
            return 
        
        path, ok = QInputDialog.getText(
            None,
            "R Not Found in PATH",
            "Enter the path to Rscript:"
        )

        if not ok or not path.strip():
            self._on_runner_failed("Rscript path not provided.")
            return

        path = path.strip()

        if not utils.is_valid_rscript(path):
            self._on_runner_failed(f"Invalid Rscript path: {path}")
            return

        plugin_settings.set_r_path(path)
        self._state = RSessionState.INITIALIZING
        self.runner.initialize()

    def _on_restart_requested(self, path):
        if self.runner:
            self._state = RSessionState.INITIALIZING
            self.runner.restart_r()
            self.runner.change_wd(path)
            self.dock.clean_console(prompt=False)
    
    def _on_change_wd(self, path):
        if self.runner:
            self.runner.change_wd(path)

