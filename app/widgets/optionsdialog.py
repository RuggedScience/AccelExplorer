from typing import Any, Dict

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from app.utils.optionsuimanager import OptionsUiManager
from app.plugins.options import DataOption


class OptionsDialog(QDialog):
    def __init__(self, options: Dict[str, DataOption], parent: QWidget = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout()
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        self._options_manager = OptionsUiManager(form_layout)
        self._options_manager.options = options

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    @property
    def values(self) -> Dict[str, Any]:
        return self._options_manager.values

    def exec(self) -> Dict[str, Any]:
        if super().exec():
            return self.values
