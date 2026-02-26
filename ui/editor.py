from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QFrame
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
