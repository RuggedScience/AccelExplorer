from PySide6.QtWidgets import (
    QMdiArea,
    QWidget,
    QMdiSubWindow,
    QApplication
)
from PySide6.QtGui import QMouseEvent, QResizeEvent, QKeyEvent
from PySide6.QtCore import QRect, QPoint, QChildEvent, Qt, QObject, QEvent

from .windowselector import WindowSelector


class SnapMdiArea(QMdiArea):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._snap_margin = 30
        self._snap_rect = None
        self._drag_start_position = QPoint()
        self._snap_rect = None
        self._rubber_band = WindowSelector(self)
        self._rubber_band.hide()
        self._window_selector = WindowSelector(self)
        self._window_selector.hide()
        self._window_selector.window_selected.connect(self._handle_window_selected)

    def _release_snap(self) -> None:
        self._rubber_band.hide()
        self._window_selector.hide()

    def _handle_window_selected(self, sub_window: QMdiSubWindow) -> None:
        if sub_window:
            sub_window.showNormal()
            sub_window.setGeometry(self._rubber_band.geometry())
            self._release_snap()

    def addSubWindow(
        self, widget: QWidget, flags: Qt.WindowFlags = None
    ) -> QMdiSubWindow:
        if flags is None:
            sw = super().addSubWindow(widget)
        else:
            sw = super().addSubWindow(widget, flags)
        return sw

    def childEvent(self, childEvent: QChildEvent) -> None:
        child = childEvent.child()
        if isinstance(child, QMdiSubWindow):
            if childEvent.added():
                child.installEventFilter(self)
            elif childEvent.removed():
                child.removeEventFilter(self)
                if child in self._tiled_windows:
                    del self._tiled_windows[child]
        return super().childEvent(childEvent)

    def resizeEvent(self, resizeEvent: QResizeEvent) -> None:
        self._release_snap()
        old_size = resizeEvent.oldSize()
        new_size = resizeEvent.size()
        windows = []
        for window in self.subWindowList():
            rect = window.geometry()
            # TODO: This should be more general to support quadrant snapping in the future.

            # Snapped to top
            if rect.top() == 0 and rect.height() == old_size.height():
                # Snapped to the left
                if rect.left() == 0:
                    rect = QRect(0, 0, new_size.width() / 2, new_size.height())
                # Snapped to the right
                else:
                    rect = QRect(
                        new_size.width() / 2, 0, new_size.width() / 2, new_size.height()
                    )
            # Snapped to the left
            elif rect.left() == 0 and rect.width() == old_size.width():
                # Snapped to the top
                if rect.top() == 0:
                    rect = QRect(0, 0, new_size.width(), new_size.height() / 2)
                # Snapped to the bottom
                else:
                    rect = QRect(
                        0,
                        new_size.height() / 2,
                        new_size.width(),
                        new_size.height() / 2,
                    )

            if rect != window.geometry():
                windows.append((window, rect))

        # Calculate sizes before the event since
        # the event will change window sizes.
        # Then after the event set the sizes.
        super().resizeEvent(resizeEvent)

        for window, rect in windows:
            window.setGeometry(rect)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self._release_snap()

        return super().keyReleaseEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        self._release_snap()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if isinstance(obj, QMdiSubWindow):
            if event.type() == QEvent.MouseButtonPress:
                mouseEvent = QMouseEvent(event)
                h = obj.height() - obj.widget().height()
                if mouseEvent.buttons() == Qt.LeftButton:
                    # We need to account for the resize handle so we don't trigger a snap when resizing.
                    # Unfortunately contentsMargins.top() accounts for the entire title bar.
                    # Use one of the other margins and assume they are all the same.
                    # TODO: Find a better solution to this.
                    if (
                        mouseEvent.y() < h
                        and mouseEvent.y() >= obj.contentsMargins().left()
                    ):
                        self._drag_start_position = mouseEvent.pos()

            elif event.type() == QEvent.MouseMove:
                mouseEvent = QMouseEvent(event)
                if self._drag_start_position:
                    dPos = mouseEvent.pos() - self._drag_start_position
                    if dPos.manhattanLength() >= QApplication.startDragDistance():
                        obj.setProperty("dragging", True)

                mPos = obj.mapToParent(mouseEvent.pos())
                if obj.property("dragging") == True:
                    if mPos.y() < self._snap_margin:
                        self._snap_rect = QRect()
                        self._snap_rect.setTopLeft(QPoint(0, 0))
                        self._snap_rect.setSize(self.size())
                    elif mPos.x() < self._snap_margin:
                        self._snap_rect = QRect()
                        self._snap_rect.setTopLeft(QPoint(0, 0))
                        self._snap_rect.setWidth(self.width() / 2)
                        self._snap_rect.setHeight(self.height())
                    elif mPos.x() > self.width() - self._snap_margin:
                        w = self.width() / 2
                        self._snap_rect = QRect()
                        self._snap_rect.setTopLeft(QPoint(w, 0))
                        self._snap_rect.setWidth(w)
                        self._snap_rect.setHeight(self.height())
                    elif mPos.y() > self.height() - self._snap_margin:
                        h = self.height() / 2
                        self._snap_rect = QRect()
                        self._snap_rect.setTopLeft(QPoint(0, h))
                        self._snap_rect.setWidth(self.width())
                        self._snap_rect.setHeight(h)
                    else:
                        self._snap_rect = None

                    if self._snap_rect:
                        self._rubber_band.setGeometry(
                            self._snap_rect.adjusted(5, 5, -5, -5)
                        )
                        self._rubber_band.show()
                    else:
                        self._rubber_band.hide()

            elif event.type() == QEvent.MouseButtonRelease:
                if self._snap_rect and self._snap_rect.isValid():
                    if self._snap_rect.size() != self.size():
                        obj.setGeometry(self._snap_rect)

                        sw_list = self.subWindowList()
                        sw_list.remove(obj)
                        sw = None

                        if (
                            self._snap_rect.left() == 0
                            and self._snap_rect.height() == self.height()
                        ):
                            self._snap_rect.moveLeft(self._snap_rect.right())
                        else:
                            self._snap_rect.moveTopLeft(QPoint(0, 0))

                        if len(sw_list) == 1:
                            sw = sw_list[0]
                            sw.setGeometry(self._snap_rect)
                            self._rubber_band.hide()
                        else:
                            self._rubber_band.hide()
                            self._rubber_band.setGeometry(self._snap_rect)
                            self._window_selector.set_windows(sw_list)
                            self._window_selector.show()
                            self._window_selector.setGeometry(self._snap_rect)
                            for window in sw_list:
                                window.showMinimized()
                    else:
                        self._rubber_band.hide()
                        obj.showMaximized()

                self._snap_rect = None
                self._drag_start_position = None
                obj.setProperty("dragging", False)

        return False
