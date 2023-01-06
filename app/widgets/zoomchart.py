from typing import Dict, List, Tuple

from PySide6.QtCharts import QChartView, QValueAxis
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QCursor, QKeyEvent, QMouseEvent, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QApplication

from .callout import Callout


def control_pressed() -> bool:
    modifiers = QApplication.keyboardModifiers()
    return modifiers == Qt.ControlModifier


class ZoomChart(QChartView):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setRubberBand(
            QChartView.HorizontalRubberBand | QChartView.ClickThroughRubberBand
        )
        self._callouts: List[Callout] = []

        self._tool_tip = self.add_callout(QPointF(0, 0), "")
        self._tool_tip.hide()
        self._prev_ranges: Dict[QValueAxis, Tuple[float, float]] = None

        self._last_mouse_pos = None

    @property
    def tooltip(self) -> Callout:
        return self._tool_tip

    def show_tooltip(self, pos: "QPointF", text: str) -> None:
        self._tool_tip.set_anchor(pos)
        self._tool_tip.set_text(text)
        self._tool_tip.update_geometry()
        self._tool_tip.show()

    def keep_tooltip(self) -> None:
        self._tool_tip = self.add_callout(QPointF(0, 0), "")
        self._tool_tip.hide()

    def add_callout(self, pos: "QPointF", text: str) -> Callout:
        callout = Callout(self.chart())
        callout.set_text(text)
        callout.set_anchor(pos)
        callout.setZValue(11)
        callout.update_geometry()
        callout.show()
        self._callouts.append(callout)
        return callout

    def _zoom_x(self, factor: float) -> None:
        rect = self.chart().plotArea()
        original_width = rect.width()
        original_center = rect.center()
        rect.setWidth(original_width / factor)
        rect.moveCenter(original_center)
        self.chart().zoomIn(rect)

    def _zoom_y(self, factor: float) -> None:
        rect = self.chart().plotArea()
        original_height = rect.height()
        original_center = rect.center()
        rect.setWidth(original_height / factor)
        rect.moveCenter(original_center)
        self.chart().zoomIn(rect)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if (
            control_pressed()
            and self.rubberBand() != QChartView.RubberBand.NoRubberBand
        ):
            factor = 0
            if event.angleDelta().y() > 0:
                factor = 2.0
            else:
                factor = 0.5

            if self.rubberBand() & QChartView.HorizontalRubberBand:
                self._zoom_x(factor)
            elif self.rubberBand() & QChartView.VerticalRubberBand:
                self._zoom_y(factor)
            elif self.rubberBand() & QChartView.RectangleRubberBand:
                self.chart().zoom(factor)
            event.accept()
            self._update_callouts()
        return super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and control_pressed()
        ):
            QApplication.setOverrideCursor(QCursor(Qt.SizeAllCursor))
            self._last_mouse_pos = event.pos()

            # Store the previous axis ranges
            # so we can reset the view later.
            if self._prev_ranges is None:
                self._prev_ranges = {}
                for axis in self.chart().axes():
                    if isinstance(axis, QValueAxis):
                        self._prev_ranges[axis] = (axis.min(), axis.max())

            event.accept()
        else:
            QApplication.restoreOverrideCursor()
            return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MiddleButton or (
            event.buttons() & Qt.LeftButton and control_pressed()
        ):
            if self._last_mouse_pos is None:
                self._last_mouse_pos = event.pos()

            d_pos = event.pos() - self._last_mouse_pos

            if self.rubberBand() & QChartView.HorizontalRubberBand:
                d_pos.setY(0)
            elif self.rubberBand() & QChartView.VerticalRubberBand:
                d_pos.setX(0)

            self.chart().scroll(-d_pos.x(), d_pos.y())
            self._last_mouse_pos = event.pos()
            self._update_callouts()
        else:
            QApplication.restoreOverrideCursor()
            return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._last_mouse_pos = None
        QApplication.restoreOverrideCursor()
        super().mouseReleaseEvent(event)
        # This handles cases where the rubber band tool was
        # used to zoom in or right click was used to zoom out.
        self._update_callouts()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if control_pressed() and event.key() == Qt.Key_R:
            chart = self.chart()
            chart.zoomReset()
            if not self._prev_ranges is None:
                for axis, range in self._prev_ranges.items():
                    axis.setRange(*range)

        self._update_callouts()
        return super().keyReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        # Resize first, then update callouts
        super().resizeEvent(event)
        self._update_callouts()

    def _update_callouts(self) -> None:
        # Remove any deleted callouts.
        callouts = []
        for callout in self._callouts:
            if callout.delete:
                callout.scene().removeItem(callout)
                continue
                # This causes a crash when a tooltip is saved and then deleted.
                # TODO: Figure out WHY!
                # self.scene().removeItem(callout)
            else:
                callout.update_geometry()
                callouts.append(callout)
        self._callouts = callouts
        self.scene().update()