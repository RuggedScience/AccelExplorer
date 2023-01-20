from enum import IntEnum, auto

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPainterPath, qRgba


class MarkerShape(IntEnum):
    SQUARE = auto()
    TRIANGLE = auto()
    CIRCLE = auto()


class MarkerGenerator:
    def __init__(self):
        self._current_shape = 0

    def next_shape(self) -> MarkerShape:
        try:
            self._current_shape = MarkerShape(self._current_shape + 1)
        except ValueError:
            self._current_shape = MarkerShape(1)

        return self._current_shape

    def reset(self) -> None:
        self._index = 0

    @staticmethod
    def _get_image(size: int) -> QImage:
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(qRgba(0, 0, 0, 0))
        return image

    @staticmethod
    def get_marker(shape: MarkerShape, size: int, color) -> QImage:
        if shape == MarkerShape.SQUARE:
            return MarkerGenerator.square(size, color)
        if shape == MarkerShape.TRIANGLE:
            return MarkerGenerator.triangle(size, color)
        if shape == MarkerShape.CIRCLE:
            return MarkerGenerator.circle(size, color)

    @staticmethod
    def square(size: int, color) -> QImage:
        image = MarkerGenerator._get_image(size)
        painter = QPainter()
        painter.begin(image)
        painter.fillRect(0, 0, size, size, color)
        painter.end()
        return image

    @staticmethod
    def triangle(size: int, color) -> QImage:
        image = MarkerGenerator._get_image(size)
        painter = QPainter()
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(size, size / 2.0)
        path.lineTo(0, size)
        painter.begin(image)
        painter.fillPath(path, color)
        painter.end()
        return image

    @staticmethod
    def circle(size: int, color) -> QImage:
        image = MarkerGenerator._get_image(size)
        painter = QPainter()
        painter.begin(image)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.end()
        return image
