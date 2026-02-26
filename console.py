from qgis.PyQt.QtWidgets import QAction, QInputDialog
from qgis.core import Qgis
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt, QSettings
import os
from subprocess import run

from .ui.dock_widget import RDockWidget
from .core.r_thread import RRunner

class Console:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.settings = QSettings("r_console", "RConsole")
        self.action = None
        self.dock = None
        self.runner = None
        self._allow_path_popup = None
        self._runner_ready = False
        self._initializing = False
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

        if self.runner is not None:
            self.runner.stop()
            self.runner = None

        self._runner_ready = False
        self._initializing = False
        self._pending_code = None

        if self.dock is not None:
            self.dock.deleteLater()
            self.dock = None

    def run(self):
        if self.dock is None:
            self.dock = RDockWidget(self.iface.mainWindow())
            self.dock.runRequested.connect(self.on_run_requested)
            self.dock.restartRequested.connect(self._on_restart_requested)
            self.dock.changeWd.connect(self._on_change_wd)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

        self._ensure_runner(False)

        self.dock.show()
        self.dock.raise_()

    def _ensure_runner(self, popup):
        self._allow_path_popup = popup
        
        try:
            if self.runner is None:
                self.runner = RRunner()
                self.runner.initialized.connect(self._on_runner_initialized)
                self.runner.path_required.connect(self._on_path_required)
                self.runner.line_result.connect(self.dock.append_result)
                self.runner.run_finished.connect(self._on_runner_finished)
                self.runner.failed.connect(self._on_runner_failed)
                self.runner.busy_changed.connect(self.dock.executionStateChanged.emit)

            if not self._runner_ready and not self._initializing:
                self._initializing = True
                self.runner.initialize(self.plugin_dir)

            return True
        except Exception as e:
            self.iface.messageBar().pushMessage("R Console Error", str(e), Qgis.Warning)
            return False

    def on_run_requested(self, code):
        if not code.strip():
            return

        if not self._ensure_runner(True):
            return

        if self._initializing or not self._runner_ready:
            self._pending_code = code   
            return

        width = self.dock.console_width()
        self.runner.run(code, width)

    def _on_runner_initialized(self, r_version):
        self._runner_ready = True
        self._initializing = False
        self.dock.set_console_header(r_version)

        if self._pending_code:
            code = self._pending_code
            self._pending_code = None
            width = self.dock.console_width()
            self.runner.run(code, width)

    def _on_runner_finished(self):
        self.dock.new_console_prompt()

    def _on_runner_failed(self, msg):
        self._runner_ready = False
        self._initializing = False
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

        if not self._is_valid_rscript(path):
            self._on_runner_failed(f"Invalid Rscript path: {path}")
            return

        self.settings.setValue('r_path', path)
        self._initializing = True
        self.runner.initialize(self.plugin_dir)

    def _is_valid_rscript(self, path):
        path = os.path.realpath(path)
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            return False
        try:
            result = run(
                [path, '-e', 'R.version.string'],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout + result.stderr
            return 'R version' in output
        except Exception:
            return False

    def _on_restart_requested(self):
        if self.runner:
            self.runner.restart_r()
            self.dock.clean_console()
    
    def _on_change_wd(self, path):
        if self.runner:
            self.runner.change_wd(path)