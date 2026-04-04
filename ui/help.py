from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox

class HelpDialog(QDialog):
    def __init__(self, html, parent=None):
        super().__init__(parent)
        self.setWindowTitle("R Help")
        self.resize(800, 600)
        layout = QVBoxLayout(self)
        self.browser = QTextBrowser()
        self.browser.setHtml(html)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(self.browser)
        layout.addWidget(buttons)