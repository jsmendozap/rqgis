from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QColor, QKeySequence
from qgis.PyQt.QtWidgets import QTextEdit, QShortcut
import html

from ..qt.core import Qt
from ..qt.gui import QFont, QTextCursor

class RConsole(QTextEdit):
    runRequested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.prompt = "> "
        self.history_list = []
        self.history_index = 0
        self._shortcuts = []
        self.setAcceptRichText(False)
        self.setReadOnly(False)
        self._width_cols = 80

        font = QFont("Monospace")
        font.setStyleHint(QFont.TypeWriter)
        self.setFont(font)

        self.selectionChanged.connect(self._clamp_selection)

    def register_shortcuts(self):
        clear = QShortcut(QKeySequence("Ctrl+L"), self)
        clear.activated.connect(lambda: self.clean(True))
        self._shortcuts.append(clear)

    def add_to_console(self, line, result):
        if line:
            self.moveCursor(QTextCursor.End)
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            if cursor.selectedText().strip() == self.prompt.strip():
                cursor.removeSelectedText()
                cursor.insertText(self.prompt + line)
            else:
                self.setTextColor(QColor("#1D1DC3"))
                self.append(self.prompt + line)
            self._reset_hscroll()

            if "\n" not in line:
                self.history_list.append(line)
                self.history_index = len(self.history_list)

        if result.error is not None:
            self.append(f"<span style='color:#c0392b;'>Error: {html.escape(result.error)}</span>")
            self._reset_hscroll()

        if result.stdout:
            self.append(f"<pre style='margin:0;'>{html.escape(result.stdout)}</pre>")
            self._reset_hscroll()

    def append_raw(self, text):
        if text:
            self.append(f"<pre style='margin:0;'>{html.escape(text)}</pre>")
            self._reset_hscroll()

    def clean(self, prompt):
        self.clear()
        if prompt:
            self.insertPlainText(self.prompt)
        self._reset_hscroll()

    def new_line(self):
        self.setTextColor(QColor("#1D1DC3"))
        self.append(self.prompt)
        self.moveCursor(QTextCursor.End)
        self._reset_hscroll()

    @property
    def width_cols(self):
        return self._width_cols

    def keyPressEvent(self, event):
        cursor = self.textCursor()

        if cursor.blockNumber() < self.document().blockCount() - 1:
            if not cursor.hasSelection():
                self.moveCursor(QTextCursor.End)

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() == Qt.NoModifier:
                self._handle_enter()
                return

        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Left):
            prompt_end = self.document().lastBlock().position() + len(self.prompt)
            if cursor.position() <= prompt_end and not cursor.hasSelection():
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

        cursor = self.textCursor()
        prompt_end = self.document().lastBlock().position() + len(self.prompt)
        if (cursor.blockNumber() == self.document().blockCount() - 1
                and cursor.position() < prompt_end
                and not cursor.hasSelection()):
            cursor.setPosition(prompt_end)
            self.setTextCursor(cursor)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        cursor = self.textCursor()
        if not cursor.hasSelection():
            prompt_end = self.document().lastBlock().position() + len(self.prompt)
            if cursor.blockNumber() < self.document().blockCount() - 1:
                self.moveCursor(QTextCursor.End)
            elif cursor.position() < prompt_end:
                cursor.setPosition(prompt_end)
                self.setTextCursor(cursor)

    def insertFromMimeData(self, source):
        if source.hasText():
            text = source.text()
            if "\n" in text or "\r" in text:
                return
            cursor = self.textCursor()
            prompt_end = self.document().lastBlock().position() + len(self.prompt)
            if cursor.position() < prompt_end:
                self.moveCursor(QTextCursor.End)
            self.textCursor().insertText(text)

    def createStandardContextMenu(self):
        menu = super().createStandardContextMenu()
        restricted = {"Cut", "Paste", "Cortar", "Pegar",
                      "Ausschneiden", "Einfügen", "Couper", "Coller"}
        for action in menu.actions():
            if action.text() in restricted:
                action.setEnabled(False)
        return menu

    def resizeEvent(self, event):
        super().resizeEvent(event)
        char_width = self.fontMetrics().averageCharWidth()
        if char_width > 0:
            self._width_cols = max(40, int(self.viewport().width() / char_width) - 20)

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

    def _replace_current_input(self, text):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(self.prompt + text)
        self.setTextCursor(cursor)
        self._reset_hscroll()

    def _clamp_selection(self):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return

        block_start = self.document().lastBlock().position()
        prompt_end = block_start + len(self.prompt)

        start = min(cursor.selectionStart(), cursor.selectionEnd())
        end = max(cursor.selectionStart(), cursor.selectionEnd())

        if start < prompt_end <= end:
            self.blockSignals(True)
            cursor.setPosition(end)
            cursor.setPosition(prompt_end, QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)
            self.blockSignals(False)

    def _reset_hscroll(self):
        bar = self.horizontalScrollBar()
        if bar is not None:
            bar.setValue(0)
