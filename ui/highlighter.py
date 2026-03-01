from qgis.PyQt.QtCore import QRegularExpression
from qgis.PyQt.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

class RHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlightingRules = []

        promptFormat = QTextCharFormat()
        promptFormat.setForeground(QColor("#0E0ED0"))
        promptFormat.setFontWeight(QFont.Bold)
        
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor("#2e7d32"))
        
        funcFormat = QTextCharFormat()
        funcFormat.setForeground(QColor("#0E0ED0"))

        self.highlightingRules.append((QRegularExpression(r"^> "), promptFormat))
        self.highlightingRules.append((QRegularExpression(r'"[^"]*"'), stringFormat))
        self.highlightingRules.append((QRegularExpression(r"'[^']*'"), stringFormat))
        self.highlightingRules.append((QRegularExpression(r"\b[A-Za-z0-9_.]+(?=\()"), funcFormat))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlightingRules:
            match = pattern.match(text)
            while match.hasMatch():
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
                match = pattern.match(text, match.capturedStart() + match.capturedLength())
