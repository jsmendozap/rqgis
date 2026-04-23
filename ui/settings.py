from qgis.PyQt.QtWidgets import QDialog, QFormLayout, QVBoxLayout, QMessageBox, QGroupBox, QPushButton, QCheckBox
from qgis.gui import QgsFileWidget
from ..core import utils
from ..core import plugin_settings
from ..qt.widgets import QDialogButtonBox
from .log import LogViewerDialog
import os

class RDockSettings(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("R Console Settings")
        self.setMinimumSize(600, 150)
        self._build_layout()
        self._load_settings()
        self._register_signals()

    def save_settings(self):
        r_path = self.r_path.filePath().strip()

        if r_path and not utils.is_valid_rscript(r_path):
            QMessageBox.warning(
                self,
                "Invalid Rscript path",
                f"The path '{r_path}' is not a valid Rscript executable."
            )
            return
        
        plugin_settings.set_r_path(r_path)
        plugin_settings.set_initial_wd(self.initial_wd.filePath().strip())
        plugin_settings.set_status_debug(self.debug_group.isChecked())
        plugin_settings.set_log_dir(self.log_dir.filePath().strip())
        plugin_settings.set_show_panel_title(self.panel_title.isChecked())
        
        self.accept()

    def _build_layout(self):
        main_layout = QVBoxLayout(self)
        
        self.r_path = QgsFileWidget()
        self.r_path.setStorageMode(QgsFileWidget.GetFile)

        self.initial_wd = QgsFileWidget()
        self.initial_wd.setStorageMode(QgsFileWidget.GetDirectory)

        self.panel_title = QCheckBox()

        general_group = QGroupBox("General")
        general_layout = QFormLayout(general_group)
        general_layout.setContentsMargins(10, 10, 10, 10)
        general_layout.addRow("Working directory on startup:", self.initial_wd)
        general_layout.addRow("R/Rscript path:", self.r_path)
        general_layout.addRow("Show panel title:", self.panel_title)

        self.log_dir = QgsFileWidget()
        self.log_dir.setStorageMode(QgsFileWidget.GetDirectory)

        self.view_log_btn = QPushButton("View logs")
        self.view_log_btn.setFixedWidth(80)
        self.view_log_btn.clicked.connect(self._view_logs)

        self.debug_group = QGroupBox("Session Logging")
        self.debug_group.setCheckable(True)
        self.debug_group.setChecked(False)
        debug_layout = QFormLayout(self.debug_group)
        debug_layout.setContentsMargins(10, 10, 10, 10)
        debug_layout.addRow("Log file location:", self.log_dir)
        debug_layout.addRow("", self.view_log_btn)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        main_layout.addWidget(general_group)
        main_layout.addWidget(self.debug_group)
        main_layout.addWidget(self.button_box)

    def _register_signals(self):
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)
        self.debug_group.toggled.connect(self._toggle_debug)
        self.panel_title.toggled.connect(self._toggle_panel_title)

    def _load_settings(self):
        r_path = plugin_settings.get_r_path()
        initial = plugin_settings.get_initial_wd()

        if r_path:
            self.r_path.setFilePath(r_path)

        self.initial_wd.setFilePath(initial)
        self.debug_group.setChecked(plugin_settings.get_status_debug())
        self.panel_title.setChecked(plugin_settings.get_show_panel_title())
        
        log_dir = plugin_settings.get_log_dir()
        if not log_dir:
            log_dir = utils.root_dir()
        self.log_dir.setFilePath(log_dir)
        self._toggle_debug(self.debug_group.isChecked())

    def _toggle_debug(self, enabled):
        self.log_dir.setEnabled(bool(enabled))

    def _view_logs(self):
        log_dir = self.log_dir.filePath().strip()
        if not log_dir:
            log_dir = utils.root_dir()
            
        log_file = os.path.join(log_dir, "session.log")
        if not os.path.exists(log_file):
            QMessageBox.information(self, "No Logs", f"No session log found at:\n{log_file}")
            return
            
        dialog = LogViewerDialog(log_file, self)
        dialog.exec_()

    def _toggle_panel_title(self, checked):
        plugin_settings.set_show_panel_title(checked)            
