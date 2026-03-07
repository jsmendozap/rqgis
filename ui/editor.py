from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor, QKeySequence, QFont
from qgis.PyQt.QtWidgets import QFrame, QTabWidget, QWidget, QFileDialog, QTabBar, QMessageBox, QShortcut
from qgis.PyQt.Qsci import QsciScintilla, QsciAPIs
from qgis.gui import QgsCodeEditorR

from ..core.utils import root_dir
import os
import re
import json

class EditorTab(QgsCodeEditorR):
    dirtyChanged = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUtf8(True)
        self.is_dirty = False
        self.file_path = None
        self.setTabWidth(2)
        self.setFrameShape(QFrame.NoFrame)
        self.textChanged.connect(self.mark_dirty)
        self._methods, self._calltips = self._load_calltips()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._handle_enter(event)
            return

        super().keyPressEvent(event)
        self._handle_autocomplete(event.text())

    def mark_saved(self, path):
        self.file_path = path
        if self.is_dirty:
            self.is_dirty = False
            self.dirtyChanged.emit(False)

    def mark_dirty(self):
        if not self.is_dirty:
            self.is_dirty = True
            self.dirtyChanged.emit(True)

    def name(self):
        base = self.file_path.split(os.sep)[-1] if self.file_path else "Untitled.R"
        return f"*{base}" if self.is_dirty else base

    def is_empty(self):
        return self.text().strip() == ""        
    
    def add_signatures(self, signatures):
        if not signatures or not hasattr(self, 'api'):
            return
        for sig in signatures:
            self.api.add(sig)
        self.api.prepare()

    def _setup_autocomplete(self, accumulated=None):
        self._force_colors_lexer()
        self.setAutoCompletionSource(QsciScintilla.AcsAPIs)
        self.setAutoCompletionThreshold(2)
        self.setAutoCompletionUseSingle(QsciScintilla.AcusNever)
        self.setCallTipsPosition(QsciScintilla.CallTipsAboveText)
        self.setCallTipsVisible(1)

        self.api = QsciAPIs(self.lexer())

        api_path = os.path.join(root_dir(), "resources", "fns_signatures.api")
        if os.path.exists(api_path):
            self.api.load(api_path)

        if accumulated:
            for sig in accumulated:
                self.api.add(sig)

        self.api.prepare()

    def _handle_enter(self, event):
        if self.isListActive():
            super().keyPressEvent(event)
            return

        line, col = self.getCursorPosition()
        opens     = self.text(line)[:col].strip().endswith(("{", "(", "[", "%>%", "|>", "+"))
        super().keyPressEvent(event)

        if opens:
            new_indent = self.indentation(line) + self.tabWidth()
            self.setIndentation(line + 1, new_indent)
            self.setCursorPosition(line + 1, new_indent)

    def _handle_autocomplete(self, char):
        line, col   = self.getCursorPosition()
        text_before = self.text(line)[:col]
        in_qgis     = bool(re.search(r'qgis\$[a-zA-Z0-9_]*$', text_before))

        self.setAutoCompletionSource(
            QsciScintilla.AcsNone if in_qgis else QsciScintilla.AcsAPIs
        )

        if char == "$" and in_qgis:
            self.SendScintilla(self.SCI_AUTOCSETSEPARATOR, 32)
            self.SendScintilla(self.SCI_AUTOCSHOW, 0, self._methods)

        elif char == "(":
            self._show_calltip(text_before)

    def _load_calltips(self):
        path = os.path.join(root_dir(), "core", "r", "calltips.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data["methods"].encode(), data["calltips"]

    def _show_calltip(self, text_before):
        for prefix, args in self._calltips.items():
            if text_before.endswith(prefix):
                encoded = args.encode("utf-8")
                self.SendScintilla(self.SCI_CALLTIPSHOW,
                    self.SendScintilla(self.SCI_GETCURRENTPOS),
                    encoded)
                break

    def _force_colors_lexer(self):
        lexer = self.lexer()
        
        if not lexer:
            print("Error: QgsCodeEditorR no inicializó un lexer base.")
            return

        fuente = QFont("Monospace", 10)
        lexer.setDefaultFont(fuente)

        is_dark_theme = self.paper().lightness() < 128

        general   = QColor("#D4D4D4") if is_dark_theme else QColor("#000000")  
        keywords  = QColor("#569CD6") if is_dark_theme else QColor("#3A3AC3")  
        strings   = QColor("#CE9178") if is_dark_theme else QColor("#2e7d32")  
        numbers   = QColor("#B5CEA8") if is_dark_theme else QColor("#098658")  
        comments  = QColor("#6A9955") if is_dark_theme else QColor("#A6AAA6")  
        operators = QColor("#569CD6") if is_dark_theme else QColor("#6A6A6D")  

        lexer.setColor(general,   0)   # Default
        lexer.setColor(comments,  1)   # Comment
        lexer.setColor(keywords,  2)   # Keyword - for, while, if
        lexer.setColor(general,   3)   # Base Keyword - print, mean
        lexer.setColor(general,   4)   # Other Keyword
        lexer.setColor(numbers,   5)   # Number
        lexer.setColor(strings,   6)   # String
        lexer.setColor(strings,   7)   # String 2
        lexer.setColor(operators, 8)   # Operator
        lexer.setColor(general,   9)   # Identifier - variables, mutate
        lexer.setColor(operators, 10)  # Infix - %in%, %>%
        lexer.setColor(operators, 11)  # Infix EOL
        lexer.setColor(strings,   12)  # Backticks
        lexer.setColor(strings,   13)  # Raw String
        lexer.setColor(strings,   14)  # Raw String 2
        lexer.setColor(strings,   15)  # Escape Sequence

        self.setLexer(lexer)

class EditorTabsWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._handling_plus_click = False
        self._shortcuts = []
        self.setTabsClosable(True)
        self._accumulated_signatures = []
        self.new_tab()
        self._add_plus_tab()

        self.tabCloseRequested.connect(self._close_tab)
        self.tabBarClicked.connect(self._on_tab_clicked)
        self.currentChanged.connect(self._update_tab_dirty_style)

    def register_shortcuts(self):
        save = QShortcut(QKeySequence("Ctrl+S"), self)
        save.activated.connect(self.save_current)
        self._shortcuts.append(save)

    def new_tab(self):
        tab = EditorTab()
        tab.dirtyChanged.connect(lambda _dirty, editor=tab: self._update_tab_dirty_style(self.indexOf(editor)))
        tab._setup_autocomplete(accumulated=self._accumulated_signatures)

        position = self.count()
        if position > 0 and self.tabText(position - 1) == "+":
            position -= 1

        idx = self.insertTab(position, tab, tab.name())
        self.setCurrentIndex(idx)
        self._update_tab_dirty_style(idx)
        self._refresh_close_buttons()
        return tab

    def save_current(self):
        return self._save_editor(self.currentWidget())

    def open_script(self):
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

        editor = self.currentWidget()
        if isinstance(editor, EditorTab) and not editor.is_empty():
            editor = self.new_tab()

        if not isinstance(editor, EditorTab):
            editor = self.new_tab()

        editor.setText(code)
        editor.mark_saved(path)
        self.setCurrentWidget(editor)

    def current_code(self):
        editor = self.currentWidget()
        if not isinstance(editor, EditorTab):
            return ""
        return editor.text()
    
    def update_signatures(self, signatures):
        self._accumulated_signatures.extend(signatures)
        for i in range(self.count()):
            editor = self.widget(i)
            if isinstance(editor, EditorTab):
                editor.add_signatures(signatures)

    def _close_tab(self, index):
        if index is None:
            index = self.currentIndex()
        if index < 0:
            return
        if self.tabText(index) == "+":
            return

        widget = self.widget(index)
        if not isinstance(widget, EditorTab):
            return

        if widget.is_dirty and not widget.is_empty():
            response = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"The script '{widget.name().lstrip('*')}' has unsaved changes. Do you want to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if response == QMessageBox.Save:
                if not self._save_editor(widget):
                    return
            elif response == QMessageBox.Cancel:
                return

        self.removeTab(index)

        if widget is not None:
            widget.deleteLater()

        real_tabs = [i for i in range(self.count()) if self.tabText(i) != "+"]
        if not real_tabs:
            self.new_tab()

        self._refresh_close_buttons()

        current = self.currentIndex()
        if current >= 0 and self.tabText(current) == "+":
            for i in range(self.count()):
                if self.tabText(i) != "+":
                    self.setCurrentIndex(i)
                    break

    def _save_editor(self, editor):
        if editor is None:
            editor = self.currentWidget()

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
                return False

        with open(path, "w", encoding="utf-8") as f:
            f.write(editor.text())

        editor.mark_saved(path)
        index = self.indexOf(editor)
        if index >= 0:
            self._update_tab_dirty_style(index)
        return True

    def _add_plus_tab(self):
        plus = QWidget()
        idx = self.addTab(plus, "+")
        self.tabBar().setTabTextColor(idx, QColor("#666666"))
        self._refresh_close_buttons()

    def _on_tab_clicked(self, index):
        if index < 0:
            return
        if self.tabText(index) != "+":
            return
        if self._handling_plus_click:
            return

        self._handling_plus_click = True
        try:
            self.removeTab(index)
            self.new_tab()
            self._add_plus_tab()
            self._refresh_close_buttons()
        finally:
            self._handling_plus_click = False

    def _update_tab_dirty_style(self, index=None):
        if index is None:
            index = self.currentIndex()
        if index < 0:
            return

        editor = self.widget(index)
        if not isinstance(editor, EditorTab):
            return

        tab_bar = self.tabBar()
        tab_bar.setTabText(index, editor.name())
        tab_bar.setTabTextColor(index, QColor("#963939") if editor.is_dirty else QColor("black"))

    def _refresh_close_buttons(self):
        tab_bar = self.tabBar()
        for i in range(self.count()):
            if self.tabText(i) == "+":
                tab_bar.setTabButton(i, QTabBar.RightSide, None)
