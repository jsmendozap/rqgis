from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from os.path import join, dirname
from .dock_widget import RConsoleDockWidget
from qgis.PyQt.QtCore import Qt

class Console:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = dirname(__file__)
        self.action = None
        self.dock = None

    def initGui(self):
        self.action = QAction(
            QIcon(join(self.plugin_dir, "Rlogo.png")),
            "R Console",
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removeToolBarIcon(self.action)
            self.action = None

    def run(self):
        if self.dock is None:
            self.dock = RConsoleDockWidget(self.iface.mainWindow())
            self.dock.runRequested.connect(self.on_run_requested)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

        self.dock.show()
        self.dock.raise_()

    def on_run_requested(self, code):
        if not code.strip():
            self.dock.append_output("No code to run.")
            return

        self.dock.executionStateChanged.emit(True)
        try:
            for line in code.splitlines():
                self.dock.append_command(line)
        finally:
            self.dock.executionStateChanged.emit(False)

