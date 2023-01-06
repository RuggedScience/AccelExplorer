from .modifydatacommand import ModifyDataCommand


class CropCommand(ModifyDataCommand):
    def __init__(self, controller, old_df, new_df, *args, **kwargs):
        super().__init__("Crop", controller, old_df, new_df, *args, **kwargs)

    def undo(self) -> None:
        super().undo()
        self._controller.fit_contents()

    def redo(self) -> None:
        super().redo()
        self._controller.fit_contents()
