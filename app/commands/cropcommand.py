from typing import TYPE_CHECKING

from PySide6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from app.views.viewcontroller import ViewController
    from app.views.viewmodel import ViewModel


class CropCommand(QUndoCommand):
    def __init__(
        self,
        controller: "ViewController",
        old_model: "ViewModel",
        new_model: "ViewModel",
        parent: QUndoCommand = None,
    ):
        super().__init__(
            "Crop",
            parent=parent,
        )

        self._controller = controller
        self._old_model = old_model
        self._new_model = new_model

    def redo(self) -> None:
        self._controller.set_model(self._new_model, undo=False)

    def undo(self) -> None:
        self._controller.set_model(self._old_model, undo=False)
