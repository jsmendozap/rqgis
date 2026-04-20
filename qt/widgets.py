"""QtWidgets compatibility shims that preserve PyQt5-style enum names on Qt6."""

from qgis.PyQt.QtWidgets import (
    QDialogButtonBox as _QDialogButtonBox,
    QFrame as _QFrame,
    QGraphicsView as _QGraphicsView,
    QListView as _QListView,
    QMessageBox as _QMessageBox,
    QStyle as _QStyle,
    QTabBar as _QTabBar,
)

from .utils import scoped


class _QStyleCompat:
    SP_DialogSaveButton = scoped(_QStyle, "StandardPixmap", "SP_DialogSaveButton") or _QStyle.SP_DialogSaveButton
    SP_FileDialogStart = scoped(_QStyle, "StandardPixmap", "SP_FileDialogStart") or _QStyle.SP_FileDialogStart
    SP_MediaPlay = scoped(_QStyle, "StandardPixmap", "SP_MediaPlay") or _QStyle.SP_MediaPlay
    SP_FileDialogDetailedView = (
        scoped(_QStyle, "StandardPixmap", "SP_FileDialogDetailedView") or _QStyle.SP_FileDialogDetailedView
    )
    SP_DialogResetButton = scoped(_QStyle, "StandardPixmap", "SP_DialogResetButton") or _QStyle.SP_DialogResetButton
    SP_BrowserReload = scoped(_QStyle, "StandardPixmap", "SP_BrowserReload") or _QStyle.SP_BrowserReload
    SP_BrowserStop = scoped(_QStyle, "StandardPixmap", "SP_BrowserStop") or _QStyle.SP_BrowserStop
    SP_DirOpenIcon = scoped(_QStyle, "StandardPixmap", "SP_DirOpenIcon") or _QStyle.SP_DirOpenIcon
    SP_DialogNoButton = scoped(_QStyle, "StandardPixmap", "SP_DialogNoButton") or _QStyle.SP_DialogNoButton
    SP_DialogYesButton = scoped(_QStyle, "StandardPixmap", "SP_DialogYesButton") or _QStyle.SP_DialogYesButton

    def __getattr__(self, name):
        return getattr(_QStyle, name)


class _QFrameCompat:
    NoFrame = scoped(_QFrame, "Shape", "NoFrame") or _QFrame.NoFrame

    def __getattr__(self, name):
        return getattr(_QFrame, name)


class _QDialogButtonBoxCompat:
    Ok = scoped(_QDialogButtonBox, "StandardButton", "Ok") or _QDialogButtonBox.Ok
    Cancel = scoped(_QDialogButtonBox, "StandardButton", "Cancel") or _QDialogButtonBox.Cancel
    Close = scoped(_QDialogButtonBox, "StandardButton", "Close") or _QDialogButtonBox.Close
    Save = scoped(_QDialogButtonBox, "StandardButton", "Save") or _QDialogButtonBox.Save

    def __getattr__(self, name):
        return getattr(_QDialogButtonBox, name)


class _QMessageBoxCompat:
    Save = scoped(_QMessageBox, "StandardButton", "Save") or _QMessageBox.Save
    Discard = scoped(_QMessageBox, "StandardButton", "Discard") or _QMessageBox.Discard
    Cancel = scoped(_QMessageBox, "StandardButton", "Cancel") or _QMessageBox.Cancel
    Yes = scoped(_QMessageBox, "StandardButton", "Yes") or _QMessageBox.Yes
    No = scoped(_QMessageBox, "StandardButton", "No") or _QMessageBox.No

    def __getattr__(self, name):
        return getattr(_QMessageBox, name)


class _QTabBarCompat:
    RightSide = scoped(_QTabBar, "ButtonPosition", "RightSide") or _QTabBar.RightSide

    def __getattr__(self, name):
        return getattr(_QTabBar, name)


class _QGraphicsViewCompat:
    ScrollHandDrag = scoped(_QGraphicsView, "DragMode", "ScrollHandDrag") or _QGraphicsView.ScrollHandDrag

    def __getattr__(self, name):
        return getattr(_QGraphicsView, name)


class _QListViewCompat:
    IconMode = scoped(_QListView, "ViewMode", "IconMode") or _QListView.IconMode
    LeftToRight = scoped(_QListView, "Flow", "LeftToRight") or _QListView.LeftToRight
    Adjust = scoped(_QListView, "ResizeMode", "Adjust") or _QListView.Adjust

    def __getattr__(self, name):
        return getattr(_QListView, name)


QStyle = _QStyleCompat()
QFrame = _QFrameCompat()
QDialogButtonBox = _QDialogButtonBoxCompat()
QMessageBox = _QMessageBoxCompat()
QTabBar = _QTabBarCompat()
QGraphicsView = _QGraphicsViewCompat()
QListView = _QListViewCompat()
