from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from os.path import join, dirname
from .dock_widget import RDockWidget
from .r_bridge import RBridge
from qgis.PyQt.QtCore import Qt
#from importlib.util import find_spec

class Console:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = dirname(__file__)
        self.action = None
        self.dock = None
        self.r_console = None

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
        
        if self.r_console is not None:
            self.r_console.stop()
            self.r_console = None

    def run(self):
        if self.dock is None:
            self.dock = RDockWidget(self.iface.mainWindow())
            self.dock.runRequested.connect(self.on_run_requested)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

        self.dock.show()
        self.dock.raise_()

    def on_run_requested(self, code):
        if not code.strip():
            self.dock.append_output("No code to run.")
            return

        if self.r_console is None:
            try:
                self.r_console = RBridge(self.plugin_dir)
            except Exception as e:
                QMessageBox.critical(self.iface.mainWindow(), "R Console Error", f"Failed to initialize R Console: {e}")
                return

        self.dock.executionStateChanged.emit(True)
        try:
            for line in code.splitlines():
                result = self.r_console.run_code(line)
                self.dock.print_to_console(line, result)
        finally:
            self.dock.new_line()
            self.dock.executionStateChanged.emit(False)
