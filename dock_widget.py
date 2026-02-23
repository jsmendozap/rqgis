from qgis.PyQt.QtCore import Qt, pyqtSignal, QEvent, QSize
from qgis.PyQt.QtGui import QIcon, QFont, QKeySequence, QColor
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


class RConsoleDockWidget(QDockWidget):
    runRequested = pyqtSignal(str)
    settingsRequested = pyqtSignal()
    executionStateChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._repl_history = []
        self._repl_history_index = -1
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

        repl_shift_enter = QShortcut(QKeySequence("Shift+Return"), self.repl)
        repl_shift_enter.activated.connect(self._emit_repl_run)
        self._shortcuts.append(repl_shift_enter)

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
        editor = self.editor_tabs.currentWidget()

        if not isinstance(editor, EditorTab):
            return

        code = editor.text().strip()
        if not code:
            return
        self.runRequested.emit(code)

    def _emit_repl_run(self):
        code = self.repl.text().strip()
        if not code:
            return
        
        self._add_to_repl_history(code)
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
    
    def _add_to_repl_history(self, command):
        self._repl_history.append(command)
        self._repl_history_index = len(self._repl_history)

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

    def _append_output(self, text):
        lines = text.splitlines()
        command = lines[0] if lines else ""
        output = "\n".join(lines[1:]) if len(lines) > 1 else ""

        self.history.append(self._render_repl_command_html(command))
        
        if output:
            rendered_output = (
                "<pre style='line-height:1.5;'>"
                f"{html.escape(output)}"
                "</pre>"
            )
            self.history.append(rendered_output)
            
        self._add_to_repl_history(command)

    def _append_error(self, text):
        self.history.append(f"<span style='color: red;'>{text}</span>")

    def print_to_console(self, line, result):
        if result["error"] is not None:
            self._append_output(f"{line}\n")
            self._append_error(f"{result['error']}")
        
        if result["stdout"]:
            self._append_output(f"{line}\n{result['stdout']}")

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
