from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from app.viewcontroller import ViewController, ViewSeries


class RenameViewCommand(QUndoCommand):
    def __init__(
        self,
        controller: "ViewController",
        name: str,
        parent: QUndoCommand = None,
    ):
        self._controller = controller
        self._old_name = controller.name
        self._new_name = name
        super().__init__(f"Rename {self._old_name} to {self._new_name}", parent)

    def redo(self) -> None:
        self._controller._rename(self._new_name)

    def undo(self) -> None:
        self._controller._rename(self._old_name)


class RenameSeriesCommand(QUndoCommand):
    def __init__(
        self,
        controller: "ViewController",
        series: "ViewSeries",
        name: str,
        parent: QUndoCommand = None,
    ):
        self._controller = controller
        self._series = series
        self._old_name = series.name
        self._new_name = name

        super().__init__(f"Rename series {self._old_name} to {self._new_name}", parent)

    def redo(self) -> None:
        self._controller._rename_series(self._series, self._new_name)

    def undo(self) -> None:
        self._controller._rename_series(self._series, self._old_name)
