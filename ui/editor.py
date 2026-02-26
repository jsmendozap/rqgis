from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QFont, QColor, QKeySequence
from qgis.PyQt.QtWidgets import QFrame, QTabWidget, QWidget, QFileDialog, QTabBar, QMessageBox, QShortcut
from qgis.PyQt.Qsci import QsciScintilla, QsciLexerPython

try:
    from qgis.PyQt.Qsci import QsciLexerR
except ImportError:
    QsciLexerR = None

class EditorTab(QsciScintilla):
    dirtyChanged = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUtf8(True)
        self.is_dirty = True
        self.file_path = None
        self._configure_editor()
        self.textChanged.connect(self.mark_dirty)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.NoModifier:
            line, col = self.getCursorPosition()
            text = self.text(line)
            before_cursor = text[:col].strip() if text else ""

            super().keyPressEvent(event)

            if before_cursor.endswith(("{", "(", "[", "%>%", "|>", "+")):
                new_line = line + 1
                prev_indent = self.indentation(line)
                self.setIndentation(new_line, prev_indent + self.tabWidth())
                self.setCursorPosition(new_line, prev_indent + self.tabWidth())
        else:
            super().keyPressEvent(event)

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
        base = self.file_path.split("/")[-1] if self.file_path else "Untitled.R"
        return f"*{base}" if self.is_dirty else base

    def is_empty(self):
        return self.text().strip() == ""

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
        self.setTabWidth(2)
        self.setIndentationsUseTabs(False)
        self.setIndentationGuides(True)

        if QsciLexerR is not None:
            self.setLexer(QsciLexerR(self))
        else:
            self.setLexer(QsciLexerPython(self))


class EditorTabsWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._handling_plus_click = False
        self._shortcuts = []
        self.setTabsClosable(True)
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
