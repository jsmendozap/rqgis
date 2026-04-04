from qgis.PyQt.QtCore import Qt, pyqtSignal, QSize
from qgis.PyQt.QtGui import QIcon, QKeySequence
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QToolButton,
    QTabWidget, QSplitter, QLabel, QStyle, QFrame, QShortcut,
    QFileDialog, QApplication
)
import os
from qgis.PyQt.QtGui import QTextCursor

from .editor import EditorTabsWidget, EditorTab
from .plot import PlotPanel
from .console import RConsole
from .settings import RDockSettings
from .help import HelpDialog
from ..core import plugin_settings

class RDockWidget(QDockWidget):
    """
    The main dock widget for the R Console.

    This widget contains the UI elements, including the script editor tabs and
    the console output area. It emits signals based on user actions (e.g.,
    clicking "Run", typing in the console), which are handled by the `Console`
    controller class.
    """
    runRequested = pyqtSignal(str)
    executionStateChanged = pyqtSignal(bool)
    restartRequested = pyqtSignal(str)
    changeWd = pyqtSignal(str)
    closing = pyqtSignal()


    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = RDockSettings()
        self.wd = plugin_settings.get_initial_wd()
        self._from_console = False
        self._shortcuts = []
        self._build_header()
        self._build_editor_area()
        self._build_console_area()
        self._build_main_layout()
        self._connect_signals()
        self.set_running_state(False)
        
    def set_console_header(self, new_path = None, emit = True):
        """
        Updates the working directory path displayed in the console header.

        Args:
            new_path (str, optional): The new path to display. Defaults to the
                                      current `self.wd`.
            emit (bool): If True, emits the `changeWd` signal.
        """
        if new_path is None:
            new_path = self.wd

        path = new_path.replace("\\", "/").split("/")
        self.wd = new_path
        
        if len(path) > 4:
            path = path[:2] + ["..."] + path[-2:]
            new_path = os.sep.join(path)
        
        self.console_info_left.setText(new_path)
        self.console_info_left.setToolTip(self.wd)
        if emit:
            self.changeWd.emit(self.wd)

    def set_running_state(self, is_running):
        """
        Updates the UI to reflect the execution state (running or ready).

        Args:
            is_running (bool): True if R code is currently executing.
        """
        self.run_button.setEnabled(not is_running)
        self.console.setReadOnly(is_running)

        if is_running:
            self._set_state_icon(is_running)
            self.state.setToolTip("Running")
        else:
            self._set_state_icon(is_running)
            self.state.setToolTip("Ready")

    def append_result(self, line, result):
        """
        Appends the result of a code execution to the console widget.

        Args:
            line (str): The code that was executed.
            result (dict): The result object from the R process.
        """

        line = "" if self._from_console else line
        self.console.add_to_console(line, result)

        if result.wd and result.wd != self.wd:
            self.wd = result.wd
            self.set_console_header(self.wd, emit = False)

        self._from_console = False

    def append_welcome(self, result):
        """
        Appends the initial welcome message to the console.

        Args:
            result (dict): The welcome message result from the R process.
        """
        self.console.moveCursor(QTextCursor.End)
        self.console.moveCursor(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        if self.console.textCursor().selectedText().strip() == self.console.prompt.strip():
            self.console.textCursor().removeSelectedText()
        
        if result.stdout:
            self.console.append_raw(result.stdout + "\n")

        self.console.new_line()
        self.set_console_header(result.wd)

    def clean_console(self, prompt):
        """Clears the console widget."""
        self.console.clean(prompt)

    def new_console_prompt(self):
        """Adds a new, empty prompt line to the console."""
        self.console.new_line()
        if self._from_console:
            self.console.setFocus()

    def console_width(self):
        """Returns the approximate width of the console in characters."""
        return self.console.width_cols
    
    def connect_plot_server(self, data):
        self.plot_panel.connect_to_server(data)

    def on_pkg_loaded(self, signatures):
        """
        Updates the editor's autocompleter with new function signatures.

        Args:
            signatures (list): A list of function signatures from a newly loaded package.
        """
        self.editor_tabs.update_signatures(signatures)

    def show_help_dialog(self, path):
        """
        Open a dialog window showing help for requested function

        Args:
            path (str): Path to help file to open
        """
        dialog = HelpDialog(path, self)
        dialog.show()

    def closeEvent(self, event):
        """Emits the `closing` signal when the widget is closed by the user."""
        self.closing.emit()
        super().closeEvent(event)

    def _build_header(self):
        self.save_button = QToolButton()
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_button.setToolTip("Save script")

        self.open_button = QToolButton()
        self.open_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogStart))
        self.open_button.setToolTip("Open script")

        self.run_button = QToolButton()
        self.run_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.run_button.setToolTip("Run (Ctrl/Cmd+Enter)")

        self.settings_button = QToolButton()
        self.settings_button.setIcon(QIcon.fromTheme("preferences-system", self.style().standardIcon(QStyle.SP_FileDialogDetailedView)))
        self.settings_button.setToolTip("Settings")

        self.clear_button = QToolButton()
        self.clear_button.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.clear_button.setToolTip("Clear console")

        self.restart_button = QToolButton()
        self.restart_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.restart_button.setToolTip("Restart R")

        self.wd_button = QToolButton()
        self.wd_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.wd_button.setToolTip("Change working directory")

    def _build_editor_area(self):
        """Constructs the editor tabs and their associated buttons."""
        self.editor_tabs = EditorTabsWidget(self)

        corner_editor = QWidget()
        corner_layout = QHBoxLayout(corner_editor)
        corner_layout.setContentsMargins(0, 0, 4, 3)
        corner_layout.addWidget(self.run_button)
        corner_layout.addWidget(self.save_button)
        corner_layout.addWidget(self.open_button)
        corner_layout.addWidget(self.settings_button)
        self.editor_tabs.setCornerWidget(corner_editor, Qt.TopRightCorner)

    def _build_console_area(self):
        """Constructs the console output area, including its header and styling."""
        self.output_tabs = QTabWidget()
        
        corner_console = QWidget()
        corner_layout = QHBoxLayout(corner_console)
        corner_layout.setContentsMargins(0, 0, 4, 3)
        corner_layout.addWidget(self.clear_button)
        corner_layout.addWidget(self.restart_button)
        corner_layout.addWidget(self.wd_button)
        self.output_tabs.setCornerWidget(corner_console, Qt.TopRightCorner)

        # ---- Console tab container ----
        console_tab = QWidget()
        tab_layout = QVBoxLayout(console_tab)
        tab_layout.setContentsMargins(3, 3, 3, 3)

        # ---- console shell ----
        self.console_shell = QFrame()
        self.console_shell.setObjectName("consoleShell")
        shell_layout = QVBoxLayout(self.console_shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("consoleHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(6)

        self.state = QLabel()
        self.state.setFixedSize(12, 12)

        self.console_info_left = QLabel("")
        self.console_info_left.setStyleSheet("color:#8a8a8a;")
        
        header_layout.addWidget(self.console_info_left)
        header_layout.addStretch()
        header_layout.addWidget(self.state)

        self.console = RConsole()
        self.console.setFrameShape(QFrame.NoFrame)
        self.console.setObjectName("consoleHistory")

        shell_layout.addWidget(header)
        shell_layout.addWidget(self.console)

        tab_layout.addWidget(self.console_shell)
        self.output_tabs.addTab(console_tab, "Console")

        self.plot_panel = PlotPanel()
        self.output_tabs.addTab(self.plot_panel, "Plots")

        self.console_shell.setStyleSheet("""
            #consoleShell {
                background: #f7f8fa;
                border: 1px solid #d9dde3;
                border-radius: 8px;
            }
            #consoleHeader {
                border-bottom: 1px solid #d9dde3;
                background: #f7f8fa;
            }
            #consoleHistory {
                background: #fcfcfd;
                border: none;
                padding: 4px;
            }
        """)

    def _set_state_icon(self, is_running):
        """Sets the small status icon (running/ready) in the console header."""
        if is_running:
            icon = QIcon.fromTheme("media-playback-stop", self.style().standardIcon(QStyle.SP_DialogNoButton))
        else:
            icon = QIcon.fromTheme("media-playback-start", self.style().standardIcon(QStyle.SP_DialogYesButton))
        
        pm = icon.pixmap(QSize(12, 12))
        self.state.setPixmap(pm)    
        
    def _build_main_layout(self):
        """Constructs the main layout of the dock widget using a splitter."""
        container = QWidget()
        self.setWidget(container)

        layout = QVBoxLayout(container)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.editor_tabs)
        splitter.addWidget(self.output_tabs)
        splitter.setSizes([320, 280])

        layout.addWidget(splitter)

    def _connect_signals(self):
        """Connects UI element signals to internal slots or emits signals."""
        self.run_button.clicked.connect(lambda: self._emit_run(True))
        self.settings_button.clicked.connect(self.settings.show)
        self.clear_button.clicked.connect(lambda: self.console.clean(True))
        self.save_button.clicked.connect(self.editor_tabs.save_current)
        self.open_button.clicked.connect(self.editor_tabs.open_script)
        self.restart_button.clicked.connect(lambda: self.restartRequested.emit(self.wd))
        self.wd_button.clicked.connect(self._on_change_wd)
        self.console.runRequested.connect(self._on_console_run)
        self.executionStateChanged.connect(self.set_running_state)
        self.plot_panel.plotAdded.connect(lambda: self.output_tabs.setCurrentWidget(self.plot_panel))
        self.runRequested.connect(lambda: self.output_tabs.setCurrentIndex(0))
        self._register_shortcuts()

    def _on_change_wd(self):
        """Opens a dialog to let the user select a new working directory."""
        path = QFileDialog.getExistingDirectory(self, "Change working directory")
        if path:
            self.set_console_header(path)

    def _register_shortcuts(self):
        """Registers keyboard shortcuts for the widget."""
        run_ctrl = QShortcut(QKeySequence("Ctrl+Return"), self)
        run_ctrl.activated.connect(self._emit_run)
        self._shortcuts.append(run_ctrl)

        run_cmd = QShortcut(QKeySequence("Meta+Return"), self)
        run_cmd.activated.connect(self._emit_run)
        self._shortcuts.append(run_cmd)

        self.editor_tabs.register_shortcuts()
        self.console.register_shortcuts()
        
    def _emit_run(self, run_all=False):
        focused = QApplication.focusWidget()
        if isinstance(focused, RConsole):
            return
        editor = self.editor_tabs.currentWidget()
        if not isinstance(editor, EditorTab):
            return

        if editor.hasSelectedText():
            code = editor.selectedText()
        elif run_all:
            code = editor.text()
        else:
            line, _ = editor.getCursorPosition()
            code = editor.text(line)

        if not code.strip():
            return
        self.runRequested.emit(code)        

    def _on_console_run(self, code):
        """Handles code submitted directly from the console input."""
        self._from_console = True
        self.runRequested.emit(code)
