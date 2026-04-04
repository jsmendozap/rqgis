from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QListWidget, QListWidgetItem, QListView, QMenu, QApplication
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWebSockets import QWebSocket
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize, Qt, QUrl, QTimer, pyqtSignal

class PlotPanel(QWidget):
    plotAdded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._plots = []
        self._setup_socket_connection()
        self._setup_ui()

    def connect_to_server(self, data):
        self._port = data[0]
        self._token = data[1]
        self._socket.open(QUrl(f"ws://127.0.0.1:{self._port}/"))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._show_context_menu)

        self.thumbnails = QListWidget()
        self.thumbnails.setMaximumHeight(63)
        self.thumbnails.setIconSize(QSize(80, 60))
        self.thumbnails.setViewMode(QListView.IconMode)
        self.thumbnails.setFlow(QListView.LeftToRight)
        self.thumbnails.setWrapping(False)
        self.thumbnails.setResizeMode(QListView.Adjust)
        self.thumbnails.setStyleSheet("QListWidget::item { border: 1px solid lightgray; margin: 1px; }")
        self.thumbnails.itemClicked.connect(self._on_thumbnail_clicked)

        layout.addWidget(self.view)
        layout.addWidget(self.thumbnails)

    def _add_plot(self, data):
        pixmap = QPixmap()
        pixmap.loadFromData(data)

        if len(self._plots) >= 10:
            self._plots.pop(0)
            self.thumbnails.takeItem(0)

        self._plots.insert(0, pixmap)
        self._change_thumbnails_height()

        item = QListWidgetItem()
        item.setIcon(QIcon(pixmap.scaled(80, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
        self.thumbnails.insertItem(0, item)

        self.thumbnails.setCurrentRow(0)
        self._show_plot(self._plots[0])
        self.plotAdded.emit()

    def _show_plot(self, pixmap):
        self.scene.clear()
        self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())

    def _on_thumbnail_clicked(self, item):
        self._show_plot(self._plots[self.thumbnails.row(item)])

    def _setup_socket_connection(self):
        self._port = None
        self._token = None
        self._socket = QWebSocket()
        self._network = QNetworkAccessManager()
        self._network.finished.connect(self._on_image_ready)
        self._socket.textMessageReceived.connect(self._on_socket_message)
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(200)
        self._debounce.timeout.connect(self._fetch_plot)

    def _on_socket_message(self, message):
        self._debounce.start()

    def _fetch_plot(self):
        url = QUrl(f"http://127.0.0.1:{self._port}/plot?token={self._token}&renderer=png")
        self._network.get(QNetworkRequest(url))

    def _on_image_ready(self, reply):
        data = reply.readAll().data()
        reply.deleteLater()
        self._add_plot(data)

    def _change_thumbnails_height(self):
        if len(self._plots) > 4:
            self.thumbnails.setMaximumHeight(77)
        else:
            self.thumbnails.setMaximumHeight(63)

    def _show_context_menu(self, pos):
        menu = QMenu()
        
        row = self.thumbnails.currentRow()
        if row < 0:
            return
        
        action = menu.addAction("Copy to clipboard")
        action.triggered.connect(lambda: QApplication.clipboard().setPixmap(self._plots[row]))
        menu.exec_(self.view.mapToGlobal(pos))
        

