from typing import List

from PySide6.QtGui import QPixmap, QMouseEvent
from PySide6.QtWidgets import QWidget, QMdiSubWindow, QHBoxLayout, QVBoxLayout, QLabel, QGraphicsView, QSpacerItem, QSizePolicy, QRubberBand, QFrame
from PySide6.QtCore import Qt, Signal


class WindowWidget(QFrame):
    clicked = Signal(QMdiSubWindow)
    def __init__(self, window: QMdiSubWindow, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._window = window
        widget = window.widget()
        if isinstance(widget, QGraphicsView):
            pix = widget.grab(widget.sceneRect().toRect())
        elif isinstance(widget, QWidget):
            pix = QPixmap(widget.size())
            widget.render(pix)
        
        layout = QVBoxLayout()
        p = QLabel()
        p.setPixmap(pix)
        p.setScaledContents(True)
        layout.addWidget(QLabel(window.windowTitle()))
        layout.addWidget(p)
        self.setLayout(layout)

        self.setStyleSheet('''
            WindowWidget:hover {
                border: 3px solid black;
                border-radius: 3px;
            }
        ''')

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            event.accept()
            self.clicked.emit(self._window)
        return super().mouseReleaseEvent(event)

class WindowSelector(QRubberBand):
    window_selected = Signal(QMdiSubWindow)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(QRubberBand.Rectangle, *args, **kwargs)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

    def _window_selected(self, window: QMdiSubWindow):
        self.window_selected.emit(window)

    def set_windows(self, windows: List[QMdiSubWindow]):
        layout = QHBoxLayout()
        layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Fixed))
        for window in windows:
            w = WindowWidget(window)
            w.clicked.connect(self._window_selected)
            w.setMaximumSize(200, 200)
            layout.addWidget(w)

        layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.setLayout(layout)
