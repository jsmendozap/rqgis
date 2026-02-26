from qgis.PyQt.QtWidgets import QDialog, QFormLayout, QDialogButtonBox, QVBoxLayout
from qgis.gui import QgsFileWidget
from qgis.PyQt.QtCore import QSettings
import os

class RDockSettings(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("R Console Settings")
        self.setMinimumSize(600, 150)
        self.settings = QSettings("r_console", "RConsole")
        self._build_layout()
        self._load_settings()
        self._register_signals()

    def save_settings(self):
        initial = self.initial_wd.filePath().strip()
        self.settings.setValue("r_path", self.r_path.filePath().strip())
        self.settings.setValue("initial_wd", initial)
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
        r_path = self.settings.value("r_path", "", type=str)
        initial = self.settings.value("initial_wd", "", type=str)
        
        if r_path:
            self.r_path.setFilePath(r_path)

        if not initial:
            initial = os.path.expanduser("~").replace("\\", "/")
        
        self.initial_wd.setFilePath(initial)

            
