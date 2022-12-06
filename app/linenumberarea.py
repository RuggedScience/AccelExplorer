from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPaintEvent

if TYPE_CHECKING:
    from .csvviewer import CSVViewer

class LineNumberArea(QWidget):
    def __init__(self, viewer: "CSVViewer") -> None:
        super().__init__(viewer)
        self._viewer = viewer

    def sizeHint(self) -> QSize:
        return QSize(self._viewer.lineNumberAreaWidth(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._viewer.lineNumberAreaPaintEvent(event)