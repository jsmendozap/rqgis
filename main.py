from qgis.PyQt.QtWidgets import QAction, QInputDialog
from qgis.core import Qgis, QgsProject
from qgis.PyQt import sip
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import Qt
from enum import Enum, auto
import os

from .ui.dock import RDockWidget
from .core.thread import RRunner
from .core.qgis_api import QGISApi
from .core import plugin_settings
from .core import utils

class RSessionState(Enum):
    """Enumeration for the state of the R session."""
    UNINITIALIZED = auto()
    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    FAILED = auto()

class Console:
    """
    Main controller for the R Console plugin.

    This class manages the plugin's lifecycle, UI (dock widget), and the
    background R process. It acts as an intermediary between the UI events
    (from RDockWidget) and the R execution logic (in RRunner), using a state
    machine (RSessionState) to handle the R session's status (e.g., ready,
    running, failed).
    """
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dock = None
        self.runner = None
        self._state = RSessionState.UNINITIALIZED
        self._allow_path_popup = False
        self._pending_code = None
        self.qgis_api = None
        self._project_signals_connected = False
        self._project_signals = None

    def initGui(self):
        """Initializes the plugin's GUI components (toolbar icon)."""
        self.action = QAction(
            QIcon(os.path.join(self.plugin_dir, "resources", "Rlogo.png")),
            "R Console",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        """Cleans up resources when the plugin is unloaded."""
        if self.action is not None:
            self.iface.removeToolBarIcon(self.action)
            self.action = None

        self._stop_runner()
        self._disconnect_project_updates()

        if self.dock is not None:
            self.dock.deleteLater()
            self.dock = None

    def run(self):
        """
        Shows the R Console dock widget.

        If the dock widget doesn't exist, it creates it. It also ensures the
        R runner is initialized.
        """
        if self.dock is None:
            self.dock = RDockWidget(self.iface.mainWindow())
            self._connect_dock_signals()
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
            
        self._ensure_runner(False)

        self.dock.show()
        self.dock.raise_()

    def _start_runner(self):
        """Creates and initializes the RRunner and its background thread."""
        self.qgis_api = QGISApi(self.iface)
        self._listen_project_updates()
        self.runner = RRunner(self.qgis_api)
        self._connect_runner_signals()

    def _stop_runner(self):
        """Stops the R runner thread and cleans up associated resources."""
        if self.runner is not None:
            self.runner.stop()
            self.runner = None
        
        if self.qgis_api is not None:
            self.qgis_api.remove_temp_files()
            self.qgis_api = None

        self._set_state(RSessionState.UNINITIALIZED)
        self._pending_code = None
        if self.dock is not None and not sip.isdeleted(self.dock):
            self.dock.clean_console(prompt=False)

    def _ensure_runner(self, popup):
        """
        Ensures the R runner is started and ready.

        If the runner is not initialized or has failed, it attempts to start it.

        Args:
            popup (bool): If True, allows showing a popup to the user to ask for
                          the Rscript path if it's not found.
        """
        self._allow_path_popup = popup
        try:
            if self.runner is None:
                self._start_runner()
            if self._state == RSessionState.UNINITIALIZED or self._state == RSessionState.FAILED:
                self._set_state(RSessionState.INITIALIZING)
                self.runner.initialize()
            return True
        except Exception as e:
            self.iface.messageBar().pushMessage("R Console Error", str(e), Qgis.Warning)
            return False

    def _on_run_requested(self, code):
        """
        Slot triggered when the user requests to run code from the UI.

        It ensures the runner is ready and then asks it to execute the code.
        If the runner is busy, the code is queued to run later.

        Args:
            code (str): The R code to execute.
        """
        if not code.strip():
            return

        if not self._ensure_runner(True):
            return

        if self._state in (RSessionState.INITIALIZING, RSessionState.RUNNING):
            if self._pending_code is None:
                self._pending_code = code
            return

        if self._state != RSessionState.READY:
            return

        self._set_state(RSessionState.RUNNING)
        self.runner.run(code, self.dock.console_width())

    def _on_runner_initialized(self):
        """
        Slot triggered when the R runner has successfully initialized.

        Sets the state to READY, displays the welcome message, and runs any
        pending code that was queued while initializing.
        """
        self._set_state(RSessionState.READY)
        self.runner.welcome_message(self.dock.console_width())

        if self._pending_code:
            code, self._pending_code = self._pending_code, None
            self._set_state(RSessionState.RUNNING)
            self.runner.run(code, self.dock.console_width())

    def _on_runner_finished(self):
        """
        Slot triggered after a code execution block finishes.

        Sets the state back to READY and either runs the next pending code
        block or shows a new prompt in the console.
        """
        if self._state == RSessionState.RUNNING:
            self._set_state(RSessionState.READY)

        if self._pending_code:
            code, self._pending_code = self._pending_code, None
            self._set_state(RSessionState.RUNNING)
            self.runner.run(code, self.dock.console_width())
        else:
            self.dock.new_console_prompt()

    def _on_runner_failed(self, msg):
        """
        Slot triggered when the R runner encounters a critical error.

        Args:
            msg (str): The error message to display.
        """
        self._set_state(RSessionState.FAILED)
        self._pending_code = None
        self.iface.messageBar().pushMessage("R Console Error", msg, Qgis.Warning)

    def _on_path_required(self):
        """
        Slot triggered when Rscript executable is not found.

        If allowed, it prompts the user to provide the path to Rscript.
        If the path is valid, it saves it and retries initialization.
        """
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
        self._set_state(RSessionState.INITIALIZING)
        self.runner.initialize()

    def _on_restart_requested(self, path):
        """
        Slot triggered when the user requests to restart the R session.

        Args:
            path (str): The working directory to set after restarting.
        """
        if self.runner:
            self._set_state(RSessionState.INITIALIZING)
            self.runner.restart_r()
            self.runner.change_wd(path)
            self.dock.clean_console(prompt=False)
    
    def _on_change_wd(self, path):
        """Slot to change the working directory in the R session."""
        if self.runner:
            self.runner.change_wd(path)

    def _on_project_changed(self, *args):
        """
        Slot triggered by QGIS project signals (e.g., CRS changed, project loaded).

        Flags the QGISApi to send an update to the R process before the next
        code execution.
        """
        if self.qgis_api is not None:
            self.qgis_api.update_state()

    def _listen_project_updates(self):
        """Connects to QGIS project signals to detect changes."""
        if self._project_signals_connected:
            return

        project = QgsProject.instance()
        self._project_signals = [
            project.crsChanged,
            project.readProject,
        ]

        if hasattr(project, 'titleChanged'):
            self._project_signals.append(project.titleChanged)
        else:
            self._project_signals.append(project.metadataChanged)

        for signal in self._project_signals:
            signal.connect(self._on_project_changed)
        
        self._project_signals_connected = True

    def _connect_dock_signals(self):
        """Connects signals from the RDockWidget to this controller's slots."""
        self.dock.runRequested.connect(self._on_run_requested)
        self.dock.restartRequested.connect(self._on_restart_requested)
        self.dock.changeWd.connect(self._on_change_wd)
        self.dock.closing.connect(self._stop_runner)

    def _connect_runner_signals(self):
        """Connects signals from the RRunner to this controller's slots."""
        self.runner.initialized.connect(self._on_runner_initialized)
        self.runner.path_required.connect(self._on_path_required)
        self.runner.line_result.connect(self.dock.append_result)
        self.runner.welcome_result.connect(self.dock.append_welcome)
        self.runner.run_finished.connect(self._on_runner_finished)
        self.runner.failed.connect(self._on_runner_failed)
        self.runner.busy_changed.connect(self.dock.executionStateChanged.emit)
        self.runner.pkg_loaded.connect(self.dock.on_pkg_loaded)
        self.runner.help_requested.connect(self.dock.show_help_dialog)
        self.runner.plot_server.connect(lambda data: self.dock.connect_plot_server(data))

    def _disconnect_project_updates(self):
        """Disconnects from all QGIS project signals."""
        if not self._project_signals_connected:
            return

        for signal in self._project_signals or []:
            try:
                signal.disconnect(self._on_project_changed)
            except TypeError:
                pass

        self._project_signals = None
        self._project_signals_connected = False

    def _set_state(self, state):
        """Changes the internal state of the R session."""
        self._state = state
