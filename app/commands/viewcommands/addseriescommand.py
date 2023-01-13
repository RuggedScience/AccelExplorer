from typing import TYPE_CHECKING

import pandas as pd
from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from typing import Dict, List

    from PySide6.QtCore import QPointF

    from app.viewcontroller import ViewController


class AddDataCommand(QUndoCommand):
    def __init__(
        self,
        name: str,
        controller: "ViewController",
        df: "pd.DataFrame",
        points: "Dict[str, List[QPointF]]",
        parent: QUndoCommand = None,
    ):
        super().__init__(f"Add {name}", parent)

        self._controller = controller
        self._df = df
        self._points = points

    def redo(self) -> None:
        self._controller._add_data(self._df, self._points)
        self._controller.fit_contents()
        pass

    def undo(self) -> None:
        self._controller._remove_data(self._df)
        self._controller.fit_contents()
        pass
