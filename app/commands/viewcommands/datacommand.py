from typing import TYPE_CHECKING

from .viewcommand import ViewCommand

if TYPE_CHECKING:
    from pandas import DataFrame
    from PySide6.QtGui import QUndoCommand
    from app.viewcontroller import ViewController


class DataCommand(ViewCommand):
    def __init__(
        self,
        title: str,
        controller: "ViewController",
        old_df: "DataFrame",
        new_df: "DataFrame",
        parent: "QUndoCommand" = None,
    ):
        super().__init__(
            title=title,
            controller=controller,
            old_df=old_df,
            new_df=new_df,
            parent=parent,
        )

    def id(self) -> int:
        return 2
