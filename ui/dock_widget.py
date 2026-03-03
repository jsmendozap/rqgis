from qgis.PyQt.QtCore import Qt, pyqtSignal, QSize
from qgis.PyQt.QtGui import QIcon, QKeySequence
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QToolButton,
    QTabWidget, QSplitter, QLabel, QStyle, QFrame, QShortcut,
    QFileDialog
)
import os
from qgis.PyQt.QtGui import QTextCursor

from .editor import EditorTabsWidget, EditorTab
from .console_widget import RConsole
from .settings_widget import RDockSettings
from ..core import plugin_settings


class RDockWidget(QDockWidget):
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
        self.run_button.setEnabled(not is_running)
        self.console.setReadOnly(is_running)

        if is_running:
            self._set_state_icon(is_running)
            self.state.setToolTip("Running")
        else:
            self._set_state_icon(is_running)
            self.state.setToolTip("Ready")
            self.console.setFocus()

    def append_result(self, line, result):

        line = "" if self._from_console else line
        self.console.add_to_console(line, result)

        if result.get("wd") and result.get("wd") != self.wd:
            self.wd = result.get("wd")
            self.set_console_header(self.wd, emit = False)

        self._from_console = False

    def append_welcome(self, result):
        self.console.moveCursor(QTextCursor.End)
        self.console.moveCursor(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        if self.console.textCursor().selectedText().strip() == self.console.prompt.strip():
            self.console.textCursor().removeSelectedText()
        
        if result.get("stdout"):
            self.console.append_raw(result["stdout"] + "\n")

        self.console.new_line()
        self.set_console_header(result.get("wd"))

    def clean_console(self, prompt):
        self.console.clean(prompt)

    def new_console_prompt(self):
        self.console.new_line()

    def console_width(self):
        return self.console.width_cols
    
    def closeEvent(self, event):
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
        # output_tabs + history + repl + console_tab/layout
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
        if is_running:
            icon = QIcon.fromTheme("media-playback-stop", self.style().standardIcon(QStyle.SP_DialogNoButton))
        else:
            icon = QIcon.fromTheme("media-playback-start", self.style().standardIcon(QStyle.SP_DialogYesButton))
        
        pm = icon.pixmap(QSize(12, 12))
        self.state.setPixmap(pm)    
        
    def _build_main_layout(self):
        # container, top_bar, splitter, setWidget
        container = QWidget()
        self.setWidget(container)

        layout = QVBoxLayout(container)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.editor_tabs)
        splitter.addWidget(self.output_tabs)
        splitter.setSizes([350, 250])

        layout.addWidget(splitter)

    def _connect_signals(self):
        self.run_button.clicked.connect(self._emit_run)
        self.settings_button.clicked.connect(self.settings.show)
        self.clear_button.clicked.connect(lambda: self.console.clean(True))
        self.save_button.clicked.connect(self.editor_tabs.save_current)
        self.open_button.clicked.connect(self.editor_tabs.open_script)
        self.restart_button.clicked.connect(lambda: self.restartRequested.emit(self.wd))
        self.wd_button.clicked.connect(self._on_change_wd)
        self.console.runRequested.connect(self._on_console_run)
        self.executionStateChanged.connect(self.set_running_state)
        self._register_shortcuts()

    def _on_change_wd(self):
        path = QFileDialog.getExistingDirectory(self, "Change working directory")
        if path:
            self.set_console_header(path)

    def _register_shortcuts(self):
        run_ctrl = QShortcut(QKeySequence("Ctrl+Return"), self)
        run_ctrl.activated.connect(self._emit_run)
        self._shortcuts.append(run_ctrl)

        run_cmd = QShortcut(QKeySequence("Meta+Return"), self)
        run_cmd.activated.connect(self._emit_run)
        self._shortcuts.append(run_cmd)

        self.editor_tabs.register_shortcuts()
        self.console.register_shortcuts()
        
    def _emit_run(self):
        editor = self.editor_tabs.currentWidget()
        if not isinstance(editor, EditorTab):
            return
        
        if editor.hasSelectedText():
            code = editor.selectedText()
        else:
            code = self._expression_at_cursor(editor)

        if not code.strip():
            return
        self.runRequested.emit(code)

    def _on_console_run(self, code):
        self._from_console = True
        self.runRequested.emit(code)

    def _expression_at_cursor(self, editor):
        line, _ = editor.getCursorPosition()
        full_code = editor.text()
        lines = full_code.splitlines()
        
        current = []
        opens = 0
        start_line = 0
        
        for i, l in enumerate(lines):
            stripped = l.strip()
            if not stripped or stripped.startswith("#"):
                if not current:
                    start_line = i + 1
                continue
            
            current.append(l)
            opens += l.count('(') + l.count('[') + l.count('{')
            opens -= l.count(')') + l.count(']') + l.count('}')
            is_pipe = l.rstrip().endswith(('|>', '%>%', '+'))
            
            if opens <= 0 and not is_pipe:
                if start_line <= line <= i:
                    return '\n'.join(current)
                current = []
                opens = 0
                start_line = i + 1
        
        return '\n'.join(current) if current else ""