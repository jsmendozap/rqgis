"""QtGui compatibility shims that preserve PyQt5-style enum names on Qt6."""

from qgis.PyQt.QtGui import QFont as _QFont, QTextCursor as _QTextCursor
from .utils import scoped


class _QTextCursorCompat:
    End = scoped(_QTextCursor, "MoveOperation", "End") or _QTextCursor.End
    StartOfBlock = scoped(_QTextCursor, "MoveOperation", "StartOfBlock") or _QTextCursor.StartOfBlock
    KeepAnchor = scoped(_QTextCursor, "MoveMode", "KeepAnchor") or _QTextCursor.KeepAnchor

    def __getattr__(self, name):
        return getattr(_QTextCursor, name)


class _QFontCompat:
    TypeWriter = scoped(_QFont, "StyleHint", "TypeWriter") or _QFont.TypeWriter

    def __getattr__(self, name):
        return getattr(_QFont, name)


QTextCursor = _QTextCursorCompat()
QFont = _QFontCompat()
