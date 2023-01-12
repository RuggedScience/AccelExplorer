from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPainterPath, qRgba


class MarkerGenerator:
    def __init__(self, size: int = 15):
        self.size = size

        self._index = 0
        self._functions = [
            MarkerGenerator.square,
            MarkerGenerator.triangle,
            MarkerGenerator.circle,
        ]

    def next(self, color) -> None:
        if self._index >= len(self._functions):
            self._index = 0

        f = self._functions[self._index]
        self._index += 1
        return f(self.size, color)

    def reset(self) -> None:
        self._index = 0

    @staticmethod
    def _get_image(size: int) -> QImage:
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(qRgba(0, 0, 0, 0))
        return image

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
