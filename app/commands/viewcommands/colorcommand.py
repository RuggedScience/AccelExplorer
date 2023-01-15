from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from PySide6.QtGui import QColor
    from app.viewcontroller import ViewController, ViewSeries


class ColorCommand(QUndoCommand):
    def __init__(
        self,
        series: "ViewSeries",
        color: "QColor",
        parent: QUndoCommand = None,
    ):
        self._series = series
        self._old_color = series.color
        self._new_color = color
        super().__init__(f"{series.name} color changed", parent)

    def redo(self) -> None:
        self._series._set_color(self._new_color)

    def undo(self) -> None:
        self._series._set_color(self._old_color)
