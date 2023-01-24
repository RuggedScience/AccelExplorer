from collections.abc import Callable

from PySide6.QtGui import QUndoCommand


class GenericCommand(QUndoCommand):
    def __init__(
        self,
        title: str,
        undo: Callable[[], None],
        redo: Callable[[], None],
        parent: QUndoCommand = None,
    ):
        super().__init__(title, parent)
        self._undo = undo
        self._redo = redo

    def undo(self) -> None:
        self._undo()

    def redo(self) -> None:
        self._redo()
