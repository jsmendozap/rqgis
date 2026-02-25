from qgis.PyQt.QtCore import Qt, pyqtSignal, QSize
from qgis.PyQt.QtGui import QIcon, QKeySequence, QColor, QTextCursor
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QToolButton,
    QTabWidget, QSplitter, QLabel, QStyle, QFrame, QShortcut,
    QFileDialog, QTabBar, QMessageBox
)
import os

from .editor import EditorTab
from .console_widget import RConsole
from .settings_widget import RDockSettings


class RDockWidget(QDockWidget):
    runRequested = pyqtSignal(str)
    executionStateChanged = pyqtSignal(bool)
    restartRequested = pyqtSignal()
    changeWd = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = RDockSettings()
        self.wd = self.settings.initial_wd.filePath()
        self._last_command = None
        self._shortcuts = []
        self._handling_plus_click = False
        self._build_header()
        self._build_editor_area()
        self._build_console_area()
        self._build_main_layout()
        self._connect_signals()
        self._initialize_state()

    def set_console_header(self, r_version):
        self.console_info_left.setText(f"R {r_version}")
        self._set_console_wd(self.wd)

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

    def print_to_console(self, line, result):

        self.console.add_to_console(line, result, self._last_command)

        if result["wd"] != self.wd:
            self.wd = result["wd"]
            self._set_console_wd(self.wd, False)

        self._last_command = None

    def new_line(self):
        self.console.append(self.console.prompt)
        self.console.moveCursor(QTextCursor.End)

    def clear_cosole(self):
        self.console.clear()
        self.console.insertPlainText(self.console.prompt)

    def _build_header(self):
        # title_label, run/settings/clear buttons
        self.title = QLabel("R Console") 
        self.title.setStyleSheet("font-weight: 500; font-size: 14px;")

        self.save_button = QToolButton()
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_button.setToolTip("Save script")

        self.open_button = QToolButton()
        self.open_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
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

    def _build_editor_area(self):
        # editor_tabs + QsciScintilla + lexer + margins
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor = self._new_tab()
        self._add_plus_tab()

        corner_editor = QWidget()
        corner_layout = QHBoxLayout(corner_editor)
        corner_layout.setContentsMargins(0, 0, 4, 3)
        corner_layout.addWidget(self.run_button)
        corner_layout.addWidget(self.save_button)
        corner_layout.addWidget(self.open_button)
        corner_layout.addWidget(self.settings_button)
        self.editor_tabs.setCornerWidget(corner_editor, Qt.TopRightCorner)

    def _new_tab(self):
        tab = EditorTab()
        tab.dirtyChanged.connect(lambda _dirty, editor=tab: self._update_tab_dirty_style(self.editor_tabs.indexOf(editor)))

        position = self.editor_tabs.count()
        if position > 0 and self.editor_tabs.tabText(position - 1) == "+":
            position -= 1

        idx = self.editor_tabs.insertTab(position, tab, tab.name())
        self.editor_tabs.setCurrentIndex(idx)
        self._update_tab_dirty_style(idx)
        self._refresh_close_buttons()
        return tab

    def _add_plus_tab(self):
        plus = QWidget()
        idx = self.editor_tabs.addTab(plus, "+")
        self.editor_tabs.tabBar().setTabTextColor(idx, QColor("#666666"))
        self._refresh_close_buttons()

    def _on_editor_tab_clicked(self, index):
        if index < 0:
            return

        if self.editor_tabs.tabText(index) != "+":
            return
    
        if self._handling_plus_click:
            return

        self._handling_plus_click = True
        try:
            self.editor_tabs.removeTab(index)  
            self._new_tab()                    
            self._add_plus_tab()               
            self._refresh_close_buttons()
        finally:
            self._handling_plus_click = False

    def _close_tab(self, index):
        if index is None:
            index = self.editor_tabs.currentIndex()
        if index < 0:
            return
        if self.editor_tabs.tabText(index) == "+":
            return

        widget = self.editor_tabs.widget(index)

        if widget.is_dirty and not widget.is_empty():
            response = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"The script '{widget.name().lstrip('*')}' has unsaved changes. Do you want to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            ) 
            if response == QMessageBox.Save:
                if not self._save_editor(widget):
                    return
            elif response == QMessageBox.Cancel:
                return

        self.editor_tabs.removeTab(index)

        if widget is not None:
            widget.deleteLater()

        real_tabs = [i for i in range(self.editor_tabs.count()) if self.editor_tabs.tabText(i) != "+"]
        if not real_tabs:
            self._new_tab()
        
        self._refresh_close_buttons()

        current = self.editor_tabs.currentIndex()
        if current >= 0 and self.editor_tabs.tabText(current) == "+":
            for i in range(self.editor_tabs.count()):
                if self.editor_tabs.tabText(i) != "+":
                    self.editor_tabs.setCurrentIndex(i)
                    break

    def _update_tab_dirty_style(self, index=None):
        if index is None:
            index = self.editor_tabs.currentIndex()
        if index < 0:
            return

        editor = self.editor_tabs.widget(index)
        if editor is None:
            return

        tab_bar = self.editor_tabs.tabBar()
        
        if not isinstance(editor, EditorTab):
             return
        
        tab_bar.setTabText(index, editor.name())

        if editor.is_dirty:
            tab_bar.setTabTextColor(index, QColor("#963939"))
        else:
            tab_bar.setTabTextColor(index, QColor("black"))
    
    def _refresh_close_buttons(self):
        tab_bar = self.editor_tabs.tabBar()
        for i in range(self.editor_tabs.count()):
            if self.editor_tabs.tabText(i) == "+":
                tab_bar.setTabButton(i, QTabBar.RightSide, None)

    def _save_editor(self):
        editor = self.editor_tabs.currentWidget()

        if not isinstance(editor, EditorTab):
            return False

        path = editor.file_path
        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save R Script",
                "",
                "R Scripts (*.R);;All Files (*)",
            )
            if not path:
                return False  # cancelado

        with open(path, "w", encoding="utf-8") as f:
            f.write(editor.text())

        editor.mark_saved(path)
        index = self.editor_tabs.indexOf(editor)
        if index >= 0:
            self._update_tab_dirty_style(index)
        return True

    def _open_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open R Script",
            "",
            "R Scripts (*.R);;All Files (*)",
        )

        if not path:
            return
        
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        editor = self.editor_tabs.currentWidget()
        if not editor.is_empty():
            editor = self._new_tab()
            
        editor.setText(code)
        editor.mark_saved(path)
        self.editor_tabs.setCurrentWidget(editor)

    def _build_console_area(self):
        # output_tabs + history + repl + console_tab/layout
        self.output_tabs = QTabWidget()
        
        corner_console = QWidget()
        corner_layout = QHBoxLayout(corner_console)
        corner_layout.setContentsMargins(0, 0, 4, 3)
        corner_layout.addWidget(self.clear_button)
        corner_layout.addWidget(self.restart_button)
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
        self.console_info_left.setStyleSheet("font-weight:700;")
        self.console_info_right = QLabel("")
        self.console_info_right.setStyleSheet("color:#8a8a8a;")

        header_layout.addWidget(self.state)
        header_layout.addWidget(self.console_info_left)
        header_layout.addStretch()
        header_layout.addWidget(self.console_info_right)

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

        layout.addWidget(self.title)
        layout.addWidget(splitter)

    def _connect_signals(self):
        self.run_button.clicked.connect(self._emit_run)
        self.settings_button.clicked.connect(self.settings.show)
        self.clear_button.clicked.connect(self.clear_cosole)
        self.save_button.clicked.connect(self._save_editor)
        self.open_button.clicked.connect(self._open_script)
        self.restart_button.clicked.connect(self.restartRequested.emit)
        self.console.runRequested.connect(self._on_console_run)
        self.executionStateChanged.connect(self.set_running_state)
        self.editor_tabs.tabCloseRequested.connect(self._close_tab)
        self.editor_tabs.tabBarClicked.connect(self._on_editor_tab_clicked)
        self.editor_tabs.currentChanged.connect(lambda i: self._update_tab_dirty_style(i))
        self.settings.wdChanged.connect(self._set_console_wd)
        self._register_shortcuts()

    def _set_console_wd(self, new_path, emit = True):
        path = new_path.split(os.sep)
        self.wd = new_path
        
        if len(path) > 4:
            path = path[:2] + ["..."] + path[-2:]
            new_path = os.sep.join(path)
        
        self.console_info_right.setText(new_path)
        self.console_info_right.setToolTip(self.wd)
        if emit:
            self.changeWd.emit(self.wd)

    def _register_shortcuts(self):
        run_ctrl = QShortcut(QKeySequence("Ctrl+Return"), self)
        run_ctrl.activated.connect(self._emit_run)
        self._shortcuts.append(run_ctrl)

        run_cmd = QShortcut(QKeySequence("Meta+Return"), self)
        run_cmd.activated.connect(self._emit_run)
        self._shortcuts.append(run_cmd)

        new_tab = QShortcut(QKeySequence("Ctrl+T"), self)
        new_tab.activated.connect(self._new_tab)
        self._shortcuts.append(new_tab)

        close_tab = QShortcut(QKeySequence("Ctrl+W"), self)
        close_tab.activated.connect(lambda: self._close_tab(self.editor_tabs.currentIndex()))
        self._shortcuts.append(close_tab)

        clear = QShortcut(QKeySequence("Ctrl+L"), self)
        clear.activated.connect(self.clear_cosole)
        self._shortcuts.append(clear)

        save = QShortcut(QKeySequence("Ctrl+S"), self)
        save.activated.connect(self._save_editor)
        self._shortcuts.append(save)

    def _initialize_state(self):
        self.clear_cosole()
        self.set_running_state(False)
        self._update_tab_dirty_style()
        
    def _emit_run(self):
        editor = self.editor_tabs.currentWidget()

        if not isinstance(editor, EditorTab):
            return

        code = editor.text().strip()
        if not code:
            return
        self.runRequested.emit(code)

    def _on_console_run(self, code):
        self._last_command = code
        self.runRequested.emit(code)