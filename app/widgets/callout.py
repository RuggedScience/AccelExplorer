from typing import TYPE_CHECKING

from PySide6.QtWidgets import QGraphicsItem, QGraphicsSceneMouseEvent
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFont, QPainterPath, QColor, QFontMetrics, QPen

if TYPE_CHECKING:
    from PySide6.QtCharts import QChart


class Callout(QGraphicsItem):
    def __init__(self, chart: "QChart") -> None:
        QGraphicsItem.__init__(self, chart)
        self._chart = chart
        self._text = ""
        self._textRect = QRectF()
        self._anchor = QPointF()
        self._font = QFont()
        self._rect = QRectF()
        self._custom_offset = None
        self.delete = False
        self.setZValue(11)

    @property
    def anchor(self) -> QPointF:
        return self._chart.mapToPosition(self._anchor)

    def boundingRect(self) -> QRectF:
        anchor = self.mapFromParent(self.anchor)
        rect = QRectF()
        rect.setLeft(min(self._rect.left(), anchor.x()))
        rect.setRight(max(self._rect.right(), anchor.x()))
        rect.setTop(min(self._rect.top(), anchor.y()))
        rect.setBottom(max(self._rect.bottom(), anchor.y()))

        return rect

    def paint(self, painter, option, widget) -> None:
        path = QPainterPath()
        path.addRoundedRect(self._rect, 5, 5)
        anchor = self.mapFromParent(self.anchor)
        if not self._rect.contains(anchor) and not self._anchor.isNull():
            point1 = QPointF()
            point2 = QPointF()

            # establish the position of the anchor point in relation to _rect
            above = anchor.y() <= self._rect.top()
            above_center = (
                anchor.y() > self._rect.top() and anchor.y() <= self._rect.center().y()
            )
            below_center = (
                anchor.y() > self._rect.center().y()
                and anchor.y() <= self._rect.bottom()
            )
            below = anchor.y() > self._rect.bottom()

            on_left = anchor.x() <= self._rect.left()
            left_of_center = (
                anchor.x() > self._rect.left() and anchor.x() <= self._rect.center().x()
            )
            right_of_center = (
                anchor.x() > self._rect.center().x()
                and anchor.x() <= self._rect.right()
            )
            on_right = anchor.x() > self._rect.right()

            # get the nearest _rect corner.
            x = (on_right + right_of_center) * self._rect.width()
            y = (below + below_center) * self._rect.height()
            corner_case = (
                (above and on_left)
                or (above and on_right)
                or (below and on_left)
                or (below and on_right)
            )
            vertical = abs(anchor.x() - x) > abs(anchor.y() - y)

            x1 = (
                x
                + left_of_center * 10
                - right_of_center * 20
                + corner_case * int(not vertical) * (on_left * 10 - on_right * 20)
            )
            y1 = (
                y
                + above_center * 10
                - below_center * 20
                + corner_case * vertical * (above * 10 - below * 20)
            )
            point1.setX(x1)
            point1.setY(y1)

            x2 = (
                x
                + left_of_center * 20
                - right_of_center * 10
                + corner_case * int(not vertical) * (on_left * 20 - on_right * 10)
            )
            y2 = (
                y
                + above_center * 20
                - below_center * 10
                + corner_case * vertical * (above * 20 - below * 10)
            )
            point2.setX(x2)
            point2.setY(y2)

            path.moveTo(point1)
            path.lineTo(anchor)
            path.lineTo(point2)
            path = path.simplified()

        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawPath(path)
        painter.drawText(self._textRect, self._text)

    def set_text(self, text: str) -> None:
        self._text = text
        metrics = QFontMetrics(self._font)
        boundingRect = metrics.boundingRect(0, 0, 150, 150, Qt.AlignmentFlag.AlignLeft, self._text) #type: ignore
        self._textRect = QRectF(boundingRect)
        self._textRect.translate(5, 5)
        self.prepareGeometryChange()
        self._rect = self._textRect.adjusted(-5, -5, 5, 5)

    def set_anchor(self, point: QPointF) -> None:
        self._anchor = point

    def update_geometry(self) -> None:
        self.prepareGeometryChange()
        offset = QPointF(10, -50)
        if self._custom_offset:
            offset = self._custom_offset
        self.setPos(self.anchor + offset)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._rect.contains(event.pos()):
            event.setAccepted(True)
        else:
            event.setAccepted(False)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._rect.contains(event.pos()):
            pos = self.mapToParent(event.pos() - event.buttonDownPos(Qt.MouseButton.LeftButton))
            self._custom_offset = pos - self.anchor

            self.setPos(pos)
            event.setAccepted(True)
        else:
            event.setAccepted(False)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._rect.contains(event.pos()):
            self.hide()
            self.delete = True
            event.setAccepted(True)
        else:
            event.setAccepted(False)
