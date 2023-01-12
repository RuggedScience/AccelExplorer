from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from pandas import DataFrame
    from app.viewcontroller import ViewController, AxisRanges


class ViewCommand(QUndoCommand):
    def __init__(
        self,
        title: str,
        controller: "ViewController",
        old_df: "DataFrame" = None,
        new_df: "DataFrame" = None,
        old_ranges: "AxisRanges" = None,
        new_ranges: "AxisRanges" = None,
        parent: QUndoCommand = None,
    ):
        super().__init__(title, parent)

        self._controller = controller

        self._old_df = old_df
        self._new_df = new_df

        self._old_ranges = old_ranges
        self._new_ranges = new_ranges

    def id(self) -> int:
        return 1

    def undo(self) -> None:
        if self._old_df is not None:
            self._controller._replace_data(self._old_df)

        if self._old_ranges is not None:
            self._controller.setAxisRanges(*self._old_ranges, block=True)

    def redo(self) -> None:
        if self._new_df is not None:
            self._controller._replace_data(self._new_df)

        if self._new_ranges is not None:
            self._controller.setAxisRanges(*self._new_ranges, block=True)

    def mergeWith(self, other: QUndoCommand) -> bool:
        if isinstance(other, ViewCommand):
            if other._new_df is not None:
                self._new_df = other._new_df

            if other._new_ranges is not None:
                self._new_ranges = other._new_ranges
            return True
        return False
