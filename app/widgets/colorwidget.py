from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPaintEvent, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget, QSpacerItem, QSizePolicy

if TYPE_CHECKING:
    from PySide6.QtGui import QMouseEvent


class ColorWidget(QWidget):
    clicked = Signal()

    def __init__(
        self,
        color: QColor,
        round: bool = False,
        size: QSize = QSize(16, 16),
        border_width: int = 2,
        border_color: QColor = QColor(Qt.black),
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._size = size
        self._widget = _ColorWidget(color, round=round, parent=self)
        self._widget.setFixedSize(size)
        self._widget.border_width = border_width
        self._widget.border_color = border_color

        layout = QHBoxLayout()
        item = QSpacerItem(1, 1, QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        layout.addItem(item)
        layout.addWidget(self._widget)
        item = QSpacerItem(1, 1, QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        layout.addItem(item)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self._clicked = False

    def sizeHint(self) -> QSize:
        return self._size

    @property
    def color(self) -> QColor:
        return self._widget.color

    @color.setter
    def color(self, color: QColor) -> None:
        self._widget.color = color

    @property
    def border_width(self) -> int:
        return self._widget.border_width

    @border_width.setter
    def border_width(self, width: int) -> None:
        self._widget.border_width = width

    @property
    def border_color(self) -> QColor:
        return self._widget.border_color

    @border_color.setter
    def border_color(self, color: QColor) -> None:
        self._widget.border_color = color

    def mousePressEvent(self, event: "QMouseEvent") -> None:
        if event.button() == Qt.LeftButton:
            self._clicked = True
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: "QMouseEvent") -> None:
        if self._clicked:
            self._clicked = False
            self.clicked.emit()

        return super().mouseReleaseEvent(event)


class _ColorWidget(QFrame):
    def __init__(
        self, color: QColor, round: bool = True, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._round = round
        self._color = None
        self.color = color

        self._border_width = 0
        self._border_color = QColor(Qt.black)

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, color: QColor) -> None:
        if color != self._color:
            self._color = color
            pal = self.palette()
            pal.setColor(pal.ColorRole.Window, color)
            pal.setColor(pal.ColorRole.Base, color)
            self.setPalette(pal)
            self.repaint()

    @property
    def border_width(self) -> int:
        return self._border_width

    @border_width.setter
    def border_width(self, width: int) -> None:
        if width is None or width < 0:
            raise ValueError("Must be a valid width")
        self._border_width = width
        self.repaint()

    @property
    def border_color(self) -> QColor:
        return self._border_color

    @border_color.setter
    def border_color(self, color: QColor) -> None:
        if color is None:
            raise ValueError("Must be a valid color")
        self._border_color = color
        self.repaint()

    def paintEvent(self, _: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pal = self.palette()
        path = QPainterPath()
        pen = QPen(self._border_color, self._border_width)
        painter.setPen(pen)
        brush = QBrush(pal.window().color())
        painter.setBrush(brush)

        rect = self.rect()
        if self._round:
            path.addEllipse(rect)
        else:
            path.addRect(rect)
        painter.setClipPath(path)

        painter.fillPath(path, painter.brush())

        if self._border_width and self._border_color:
            painter.strokePath(path, painter.pen())
