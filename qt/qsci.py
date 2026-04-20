"""Qsci compatibility shims that preserve PyQt5-style enum names on Qt6."""

from qgis.PyQt.Qsci import QsciScintilla as _QsciScintilla, QsciAPIs

from .utils import scoped


class _QsciScintillaCompat:
    AcsAPIs = scoped(_QsciScintilla, "AutoCompletionSource", "AcsAPIs") or _QsciScintilla.AcsAPIs
    AcsNone = scoped(_QsciScintilla, "AutoCompletionSource", "AcsNone") or _QsciScintilla.AcsNone
    AcusNever = (
        scoped(_QsciScintilla, "AutoCompletionUseSingle", "AcusNever") or _QsciScintilla.AcusNever
    )
    CallTipsAboveText = (
        scoped(_QsciScintilla, "CallTipsPosition", "CallTipsAboveText") or _QsciScintilla.CallTipsAboveText
    )
    NoFoldStyle = scoped(_QsciScintilla, "FoldStyle", "NoFoldStyle") or _QsciScintilla.NoFoldStyle

    def __getattr__(self, name):
        return getattr(_QsciScintilla, name)


QsciScintilla = _QsciScintillaCompat()
