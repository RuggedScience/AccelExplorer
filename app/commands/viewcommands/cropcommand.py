from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from typing import Dict, List
    from pandas import DataFrame
    from PySide6.QtCore import QPointF
    from app.viewcontroller import ViewController


class CropCommand(QUndoCommand):
    def __init__(
        self,
        controller: "ViewController",
        old_df: "DataFrame",
        new_df: "DataFrame",
        old_points: "Dict[str, List[QPointF]]",
        new_points: "Dict[str, List[QPointF]]",
        parent: QUndoCommand = None,
    ):
        super().__init__(
            "Crop",
            parent=parent,
        )

        self._controller = controller
        self._old_df = old_df
        self._new_df = new_df
        self._old_points = old_points
        self._new_points = new_points

    def _update_view(self, df, points):
        self._controller._df = df
        for series in self._controller:
            name = series.name
            p = points.get(name)
            if p is not None:
                series.points = p
        self._controller._axis_range_changed()
        self._controller.fit_contents()

    def redo(self) -> None:
        self._update_view(self._new_df, self._new_points)

    def undo(self) -> None:
        self._update_view(self._old_df, self._old_points)
