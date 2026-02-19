from qgis.PyQt.QtCore import Qt, pyqtSignal, QEvent, QSize
from qgis.PyQt.QtGui import QIcon, QFont, QTextCursor, QKeySequence, QColor
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
)



class RConsoleDockWidget(QDockWidget):
    runRequested = pyqtSignal(str)
    settingsRequested = pyqtSignal()
    executionStateChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._repl_history = []
        self._repl_history_index = -1
        self._current_file_path = None
        self._is_dirty = True
        self._shortcuts = []
        self._build_header()
        self._build_editor_area()
        self._build_console_area()
        self._build_main_layout()
        self._connect_signals()
        self._initialize_state()

    def _build_header(self):
        # title_label, run/settings/clear buttons
        self.title = QWidget()
        self.title_layout = QHBoxLayout(self.title)
        self.title_label = QLabel("R Console") 
        self.title_label.setStyleSheet("font-weight: 500; font-size: 14px;")
        self.state = QLabel()
        self.state.setFixedSize(12, 12)

        self.title_layout.addWidget(self.state)    
        self.title_layout.addWidget(self.title_label)

        self.save_button = QToolButton()
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_button.setToolTip("Save")

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
        self.editor = QsciScintilla()
        self.editor.setUtf8(True)
        
        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        self.editor.setFont(font)
        self.editor.setMarginsFont(font)

        self.editor.setMarginType(0, QsciScintilla.NumberMargin)
        self.editor.setMarginWidth(0, "00")
        self.editor.setMarginLineNumbers(0, True)
        self.editor.setMarginsForegroundColor(Qt.gray)
        self.editor.setFrameShape(QFrame.NoFrame)
        self.editor.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        if QsciLexerR is not None:
            self.editor.setLexer(QsciLexerR(self.editor))
        else:
            self.editor.setLexer(QsciLexerPython(self.editor))
        self.editor_tabs.addTab(self.editor, "Untitled1.R")

        corner_editor = QWidget()
        corner_layout = QHBoxLayout(corner_editor)
        corner_layout.setContentsMargins(0, 0, 4, 3)
        corner_layout.addWidget(self.save_button)
        corner_layout.addWidget(self.run_button)
        corner_layout.addWidget(self.settings_button)
        self.editor_tabs.setCornerWidget(corner_editor, Qt.TopRightCorner)

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

        self.console_info_left = QLabel("R 4.3.1")
        self.console_info_left.setStyleSheet("font-weight:700;")
        self.console_info_right = QLabel("~/QGIS_R/")
        self.console_info_right.setStyleSheet("color:#8a8a8a;")

        header_layout.addWidget(self.console_info_left)
        header_layout.addStretch()
        header_layout.addWidget(self.console_info_right)

        # History
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setFrameShape(QFrame.NoFrame)
        self.history.setObjectName("consoleHistory")

        # REPL row
        repl_row = QWidget()
        repl_row.setObjectName("replRow")
        repl_layout = QHBoxLayout(repl_row)
        repl_layout.setContentsMargins(8, 6, 8, 6)
        repl_layout.setSpacing(6)

        self.prompt_label = QLabel(">")
        self.prompt_label.setStyleSheet("color:#1f4ea8; font-weight:700;")

        self.repl = QLineEdit()
        self.repl.installEventFilter(self)
        self.repl.setPlaceholderText("Type R code here and press Enter to execute...")
        self.repl.setFrame(False)

        repl_layout.addWidget(self.prompt_label)
        repl_layout.addWidget(self.repl)

        # Compose shell
        shell_layout.addWidget(header)
        shell_layout.addWidget(self.history)
        shell_layout.addWidget(repl_row)

        tab_layout.addWidget(self.console_shell)
        self.output_tabs.addTab(console_tab, "Console")

        # Style for integrated look
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
            #replRow {
                border-top: 1px solid #e3e6eb;
                background: #f7f8fa;
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
        # clicked.connect(...), returnPressed.connect(...)
        self.run_button.clicked.connect(self._emit_run)
        self.settings_button.clicked.connect(self.settingsRequested.emit)
        self.clear_button.clicked.connect(self._clear_console)
        self.save_button.clicked.connect(self._save_script)
        self.repl.returnPressed.connect(self._emit_repl_run)
        self._register_shortcuts()
        self.executionStateChanged.connect(self.set_running_state)
        self.editor.textChanged.connect(self._on_editor_changed)

    def _register_shortcuts(self):
        run_ctrl = QShortcut(QKeySequence("Ctrl+Return"), self)
        run_ctrl.activated.connect(self._emit_run)
        self._shortcuts.append(run_ctrl)

        run_cmd = QShortcut(QKeySequence("Meta+Return"), self)
        run_cmd.activated.connect(self._emit_run)
        self._shortcuts.append(run_cmd)

        repl_shift_enter = QShortcut(QKeySequence("Shift+Return"), self.repl)
        repl_shift_enter.activated.connect(self._emit_repl_run)
        self._shortcuts.append(repl_shift_enter)

    def set_running_state(self, is_running):
        self.run_button.setEnabled(not is_running)
        self.repl.setEnabled(not is_running)

        if is_running:
            self._set_state_icon(is_running)
            self.state.setToolTip("Running")
            self.prompt_label.setText("…")
        else:
            self._set_state_icon(is_running)
            self.state.setToolTip("Ready")
            self.prompt_label.setText(">")
            self.repl.setFocus()

    def _initialize_state(self):
        self._clear_console()
        self.set_running_state(False)
        self._update_tab_dirty_style()
        
    def _emit_run(self):
        code = self.editor.text()
        self.runRequested.emit(code)

    def _emit_repl_run(self):
        code = self.repl.text().strip()
        if not code:
            return
        self._repl_history.append(code)
        self._repl_history_index = len(self._repl_history)
        self.runRequested.emit(code)
        self.repl.clear()

    def eventFilter(self, obj, event):
        if obj is self.repl and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self._show_previous_repl_history()
                return True
            if event.key() == Qt.Key_Down:
                self._show_next_repl_history()
                return True
        return super().eventFilter(obj, event)
    
    def _show_previous_repl_history(self):
        if not self._repl_history:
            return
        if self._repl_history_index > 0:
            self._repl_history_index -= 1
        self.repl.setText(self._repl_history[self._repl_history_index])

    def _show_next_repl_history(self):
        if not self._repl_history:
            return
        if self._repl_history_index < len(self._repl_history) - 1:
            self._repl_history_index += 1
            self.repl.setText(self._repl_history[self._repl_history_index])
        else:
            self._repl_history_index = len(self._repl_history)
            self.repl.clear()

    def _set_state_icon(self, is_running):
        if is_running:
            icon = QIcon.fromTheme("media-playback-stop", self.style().standardIcon(QStyle.SP_DialogNoButton))
        else:
            icon = QIcon.fromTheme("media-playback-start", self.style().standardIcon(QStyle.SP_DialogYesButton))
        
        pm = icon.pixmap(QSize(12, 12))
        self.state.setPixmap(pm)

    def _clear_console(self):
        self.history.clear()

    def _save_script(self):
        path = self._current_file_path

        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, "Save R Script", "", "R Scripts (*.R);;All Files (*)")
            if not path:
                return
            self._current_file_path = path

        with open(path, "w", encoding="utf-8") as f:
            f.write(self.editor.text())

        self._current_file_path = path
        tab_name = path.split("/")[-1]
        self.editor_tabs.setTabText(self.editor_tabs.currentIndex(), tab_name)
        self._is_dirty = False
        self._update_tab_dirty_style()

    def _update_tab_dirty_style(self):
        index = self.editor_tabs.currentIndex()
        tab_bar = self.editor_tabs.tabBar()
        if self._is_dirty:
            tab_bar.setTabTextColor(index, QColor("#963939"))
            tab_bar.setTabText(index, f"*{tab_bar.tabText(index).lstrip('*')}")
        else:
            tab_bar.setTabTextColor(0, QColor("black"))
            tab_bar.setTabTextColor(index, QColor("black"))

    def _on_editor_changed(self):
        if not self._is_dirty:
            self._is_dirty = True
            self._update_tab_dirty_style()

    def append_output(self, text):
        self.history.append(text)

    def append_command(self, text):
        self.history.append(self._render_repl_command_html(text))

    def append_error(self, text):
        cursor = self.history.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.history.setTextCursor(cursor)
        self.history.insertHtml(f"<span style='color: red;'>{text}</span><br>")
        self.history.ensureCursorVisible()

    def _render_repl_command_html(self, text):
        BLUE_PROMPT = "#0E0ED0"   # > azul oscuro
        BLUE_FUNC = "#0E0ED0"     # funcion + parentesis
        GREEN_STR = "#2e7d32"     # strings
        BLACK_ARG = "#111111"     # argumentos no string

        s = text
        out = [f"<span style='color:{BLUE_PROMPT};'>&gt; </span>"]

        # Busca inicio de llamada: nombre(...)
        i = s.find("(")
        if i == -1:
            # Sin paréntesis: todo como "función/comando"
            out.append(f"<span style='color:{BLUE_FUNC};'>{html.escape(s)}</span>")
            return "".join(out)

        # Parte izquierda: nombre de función
        func_name = s[:i]
        out.append(f"<span style='color:{BLUE_FUNC};'>{html.escape(func_name)}</span>")

        # Desde el primer "(" en adelante
        in_string = False
        quote_char = ""
        escape = False

        # El paréntesis y estructura de llamada en azul; contenido en negro/verde
        out.append(f"<span style='color:{BLUE_FUNC};'>(</span>")

        for ch in s[i + 1:]:
            if in_string:
                # Dentro de string: verde (incluye comillas)
                if escape:
                    out.append(f"<span style='color:{GREEN_STR};'>{html.escape(ch)}</span>")
                    escape = False
                    continue
                if ch == "\\":
                    out.append(f"<span style='color:{GREEN_STR};'>\\</span>")
                    escape = True
                    continue
                out.append(f"<span style='color:{GREEN_STR};'>{html.escape(ch)}</span>")
                if ch == quote_char:
                    in_string = False
                    quote_char = ""
                continue

            # Fuera de string
            if ch in ("'", '"'):
                in_string = True
                quote_char = ch
                out.append(f"<span style='color:{GREEN_STR};'>{html.escape(ch)}</span>")
            elif ch in ("(", ")"):
                out.append(f"<span style='color:{BLUE_FUNC};'>{html.escape(ch)}</span>")
            else:
                out.append(f"<span style='color:{BLACK_ARG};'>{html.escape(ch)}</span>")

        return "".join(out)
