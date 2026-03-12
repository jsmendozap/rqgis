from qgis.PyQt.QtWidgets import QDialog, QFormLayout, QDialogButtonBox, QVBoxLayout, QMessageBox
from qgis.gui import QgsFileWidget
from ..core import utils
from ..core import plugin_settings
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
        self.accept()

    def _build_layout(self):
        main_layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(10, 10, 10, 10)
        
        self.r_path = QgsFileWidget()
        self.r_path.setStorageMode(QgsFileWidget.GetFile)

        self.initial_wd = QgsFileWidget()
        self.initial_wd.setStorageMode(QgsFileWidget.GetDirectory)

        form_layout.addRow("Working directory on startup:", self.initial_wd)
        form_layout.addRow("R/Rscript path:", self.r_path)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.button_box)

    def _register_signals(self):
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)

    def _load_settings(self):
        r_path = plugin_settings.get_r_path()
        initial = plugin_settings.get_initial_wd()

        if r_path:
            self.r_path.setFilePath(r_path)

        self.initial_wd.setFilePath(initial)

            
