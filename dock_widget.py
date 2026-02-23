from qgis.PyQt.QtCore import Qt, pyqtSignal, QSize, QRegularExpression
from qgis.PyQt.QtGui import QIcon, QFont, QKeySequence, QColor, QTextCursor, QSyntaxHighlighter, QTextCharFormat
from qgis.PyQt.Qsci import QsciScintilla, QsciLexerPython
import html

try:
    from qgis.PyQt.Qsci import QsciLexerR
except ImportError:
    QsciLexerR = None

from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QToolButton,
    QTabWidget,
    QSplitter,
    QLabel,
    QStyle, 
    QFrame,
    QLineEdit,
    QShortcut,
    QFileDialog,
    QTabBar,
    QMessageBox,
)

class EditorTab(QsciScintilla):
    dirtyChanged = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUtf8(True)
        self._is_dirty = True
        self.file_path = None
        self._configure_editor()
        self.textChanged.connect(self.mark_dirty)

    def _configure_editor(self):
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        self.setFont(font)
        self.setMarginsFont(font)

        self.setMarginType(0, QsciScintilla.NumberMargin)
        self.setMarginWidth(0, "00")
        self.setMarginLineNumbers(0, True)
        self.setMarginsForegroundColor(Qt.gray)
        self.setFrameShape(QFrame.NoFrame)
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        self.setAutoIndent(True)

        if QsciLexerR is not None:
            self.setLexer(QsciLexerR(self))
        else:
            self.setLexer(QsciLexerPython(self))

    def mark_saved(self, path):
        self.file_path = path
        if self._is_dirty:
            self._is_dirty = False
            self.dirtyChanged.emit(False)

    def mark_dirty(self):
        if not self._is_dirty:
            self._is_dirty = True
            self.dirtyChanged.emit(True)

    def name(self):
        base = self.file_path.split("/")[-1] if self.file_path else "Untitled.R"
        return f"*{base}" if self._is_dirty else base

class RHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []
        self._error_blocks = set()

        promptFormat = QTextCharFormat()
        promptFormat.setForeground(QColor("#0E0ED0"))
        promptFormat.setFontWeight(QFont.Bold)
        
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor("#2e7d32"))
        
        funcFormat = QTextCharFormat()
        funcFormat.setForeground(QColor("#0E0ED0"))
        
        self.errorFormat = QTextCharFormat()
        self.errorFormat.setForeground(QColor("red"))

        self.highlightingRules.append((QRegularExpression(r"^> "), promptFormat))
        self.highlightingRules.append((QRegularExpression(r"\".*\""), stringFormat))
        self.highlightingRules.append((QRegularExpression(r"'.*'"), stringFormat))
        self.highlightingRules.append((QRegularExpression(r"\b[A-Za-z0-9_.]+(?=\()"), funcFormat))

    def highlightBlock(self, text):
        if self.currentBlock().blockNumber() in self._error_blocks:
            self.setFormat(0, len(text), self.errorFormat)
            return
        for pattern, fmt in self.highlightingRules:
            match = pattern.match(text)
            while match.hasMatch():
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
                match = pattern.match(text, match.capturedStart() + match.capturedLength())

    def mark_error_block(self, block):
        self._error_blocks.add(block.blockNumber())
        self.rehighlightBlock(block)

class RConsole(QTextEdit):
    runRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.prompt = "> "
        self.history_list = []
        self.history_index = 0
        self.setAcceptRichText(False)
        self.setReadOnly(False)
        
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        self.setFont(font)
        
        self.insertPlainText(self.prompt)
        self._highlighter = RHighlighter(self.document())

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        
        if cursor.blockNumber() < self.document().blockCount() - 1:
            if not cursor.hasSelection():
                self.moveCursor(QTextCursor.End)

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() == Qt.NoModifier:
                self._handle_enter()
                return
        
        if event.key() == Qt.Key_Backspace:
            line_text = self.document().lastBlock().text()
            if len(line_text) <= len(self.prompt):
                return

        if event.key() == Qt.Key_Up:
            if self.history_index > 0:
                self.history_index -= 1
                self._replace_current_input(self.history_list[self.history_index])
            return

        if event.key() == Qt.Key_Down:
            if self.history_index < len(self.history_list):
                self.history_index += 1
                text = self.history_list[self.history_index] if self.history_index < len(self.history_list) else ""
                self._replace_current_input(text)
            return

        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self.textCursor().blockNumber() < self.document().blockCount() - 1:
            self.moveCursor(QTextCursor.End)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.textCursor().blockNumber() < self.document().blockCount() - 1:
            self.moveCursor(QTextCursor.End)

    def _handle_enter(self):
        self.moveCursor(QTextCursor.End)
        self.moveCursor(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        line = self.textCursor().selectedText()

        if line.startswith(self.prompt):
            cmd = line[len(self.prompt):]
        elif line.strip().startswith(">"):
            cmd = line.strip().lstrip(">").strip()
        else:
            cmd = line

        if cmd.strip():
            self.history_list.append(cmd)
            self.history_index = len(self.history_list)
            self.moveCursor(QTextCursor.End)
            self.runRequested.emit(cmd)
        else:
            self.append("")

    def _replace_current_input(self, text):
        self.moveCursor(QTextCursor.End)
        self.moveCursor(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        self.textCursor().removeSelectedText()
        self.insertPlainText(self.prompt + text)

class RDockWidget(QDockWidget):
    runRequested = pyqtSignal(str)
    settingsRequested = pyqtSignal()
    executionStateChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_command = None
        self._shortcuts = []
        self._handling_plus_click = False
        self._build_header()
        self._build_editor_area()
        self._build_console_area()
        self._build_main_layout()
        self._connect_signals()
        self._initialize_state()

    def _build_header(self):
        # title_label, run/settings/clear buttons
        self.title = QLabel("R Console") 
        self.title.setStyleSheet("font-weight: 500; font-size: 14px;")

        self.save_button = QToolButton()
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_button.setToolTip("Save script")

        self.run_button = QToolButton()
        self.run_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.run_button.setToolTip("Run (Ctrl/Cmd+Enter)")

        self.settings_button = QToolButton()
        self.settings_button.setIcon(QIcon.fromTheme("preferences-system", self.style().standardIcon(QStyle.SP_FileDialogDetailedView)))
        self.settings_button.setToolTip("Settings")

        self.clear_button = QToolButton()
        self.clear_button.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        self.clear_button.setToolTip("Clear")

    def _build_editor_area(self):
        # editor_tabs + QsciScintilla + lexer + margins
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor = self._new_tab()
        self._add_plus_tab()

        corner_editor = QWidget()
        corner_layout = QHBoxLayout(corner_editor)
        corner_layout.setContentsMargins(0, 0, 4, 3)
        corner_layout.addWidget(self.save_button)
        corner_layout.addWidget(self.run_button)
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

    def _build_console_area(self):
        # output_tabs + history + repl + console_tab/layout
        self.output_tabs = QTabWidget()
        
        corner_console = QWidget()
        corner_layout = QHBoxLayout(corner_console)
        corner_layout.setContentsMargins(0, 0, 4, 3)
        corner_layout.addWidget(self.clear_button)
        self.output_tabs.setCornerWidget(corner_console, Qt.TopRightCorner)

        # ---- Console tab container ----
        console_tab = QWidget()
        tab_layout = QVBoxLayout(console_tab)
        tab_layout.setContentsMargins(3, 3, 3, 3)

        # ---- Unified console shell ----
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

        self.console_info_left = QLabel("R 4.3.1")
        self.console_info_left.setStyleSheet("font-weight:700;")
        self.console_info_right = QLabel("~/QGIS_R/")
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
        self.settings_button.clicked.connect(self.settingsRequested.emit)
        self.clear_button.clicked.connect(self._clear_console)
        self.save_button.clicked.connect(self._save_script)
        self.console.runRequested.connect(self._on_console_run)
        self.executionStateChanged.connect(self.set_running_state)
        self.editor_tabs.tabCloseRequested.connect(self._close_tab)
        self.editor_tabs.tabBarClicked.connect(self._on_editor_tab_clicked)
        self.editor_tabs.currentChanged.connect(lambda i: self._update_tab_dirty_style(i))
        self._register_shortcuts()

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

        if widget._is_dirty:
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

    def _refresh_close_buttons(self):
        tab_bar = self.editor_tabs.tabBar()
        for i in range(self.editor_tabs.count()):
            if self.editor_tabs.tabText(i) == "+":
                tab_bar.setTabButton(i, QTabBar.RightSide, None)

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
        clear.activated.connect(self._clear_console)
        self._shortcuts.append(clear)

        save = QShortcut(QKeySequence("Ctrl+S"), self)
        save.activated.connect(self._save_script)
        self._shortcuts.append(save)

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

    def _initialize_state(self):
        self._clear_console()
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

    def _set_state_icon(self, is_running):
        if is_running:
            icon = QIcon.fromTheme("media-playback-stop", self.style().standardIcon(QStyle.SP_DialogNoButton))
        else:
            icon = QIcon.fromTheme("media-playback-start", self.style().standardIcon(QStyle.SP_DialogYesButton))
        
        pm = icon.pixmap(QSize(12, 12))
        self.state.setPixmap(pm)

    def _clear_console(self):
        self.console.clear()
        self.console.insertPlainText(self.console.prompt)

    def _save_script(self):
        editor = self.editor_tabs.currentWidget()
        self._save_editor(editor)

    def _save_editor(self, editor):
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

        if editor._is_dirty:
            tab_bar.setTabTextColor(index, QColor("#963939"))
        else:
            tab_bar.setTabTextColor(index, QColor("black"))

    def print_to_console(self, line, result):
        if line != self._last_command:
            self.console.moveCursor(QTextCursor.End)
            cursor = self.console.textCursor()
            cursor.select(QTextCursor.BlockUnderCursor)
            if cursor.selectedText().strip() == self.console.prompt.strip():
                cursor.removeSelectedText()
                cursor.insertText(self.console.prompt + line)
            else:
                self.console.append(self.console.prompt + line)

        if result["error"] is not None:
            self.console.append(result["error"])
            self.console._highlighter.mark_error_block(self.console.document().lastBlock())

        if result["stdout"]:
            self.console.append(f"<pre style='margin:0;'>{html.escape(result['stdout'])}</pre>")

        self._last_command = None

    def new_line(self):
        self.console.append(self.console.prompt)
        self.console.moveCursor(QTextCursor.End)