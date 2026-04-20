"""QtCore compatibility shims that preserve PyQt5-style enum names on Qt6."""

from qgis.PyQt.QtCore import Qt as _Qt
from .utils import scoped


class _QtCompat:
    BlockingQueuedConnection = (
        scoped(_Qt, "ConnectionType", "BlockingQueuedConnection") or _Qt.BlockingQueuedConnection
    )
    RightDockWidgetArea = scoped(_Qt, "DockWidgetArea", "RightDockWidgetArea") or _Qt.RightDockWidgetArea
    TopRightCorner = scoped(_Qt, "Corner", "TopRightCorner") or _Qt.TopRightCorner
    Vertical = scoped(_Qt, "Orientation", "Vertical") or _Qt.Vertical
    NoModifier = scoped(_Qt, "KeyboardModifier", "NoModifier") or _Qt.NoModifier
    Key_Return = scoped(_Qt, "Key", "Key_Return") or _Qt.Key_Return
    Key_Enter = scoped(_Qt, "Key", "Key_Enter") or _Qt.Key_Enter
    Key_Backspace = scoped(_Qt, "Key", "Key_Backspace") or _Qt.Key_Backspace
    Key_Delete = scoped(_Qt, "Key", "Key_Delete") or _Qt.Key_Delete
    Key_Left = scoped(_Qt, "Key", "Key_Left") or _Qt.Key_Left
    Key_Up = scoped(_Qt, "Key", "Key_Up") or _Qt.Key_Up
    Key_Down = scoped(_Qt, "Key", "Key_Down") or _Qt.Key_Down
    CustomContextMenu = scoped(_Qt, "ContextMenuPolicy", "CustomContextMenu") or _Qt.CustomContextMenu
    KeepAspectRatio = scoped(_Qt, "AspectRatioMode", "KeepAspectRatio") or _Qt.KeepAspectRatio
    SmoothTransformation = (
        scoped(_Qt, "TransformationMode", "SmoothTransformation") or _Qt.SmoothTransformation
    )

    def __getattr__(self, name):
        return getattr(_Qt, name)


Qt = _QtCompat()
