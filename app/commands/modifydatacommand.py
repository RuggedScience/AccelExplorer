import pandas as pd

from PySide6.QtGui import QUndoCommand

from app.viewcontroller import ViewController


class ModifyDataCommand(QUndoCommand):
    def __init__(
        self,
        title: str,
        controller: ViewController,
        old_df: pd.DataFrame,
        new_df: pd.DataFrame,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._title = title
        self._controller = controller
        self._old_df = old_df
        self._new_df = new_df

        self.setText(f"{self._title} - {self._controller.name}")

    def undo(self) -> None:
        self._controller.df = self._old_df

    def redo(self) -> None:
        self._controller.df = self._new_df
