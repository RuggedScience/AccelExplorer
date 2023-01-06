from typing import Dict, Any
from numbers import Number

from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QDialogButtonBox,
)

from .plugins import DataOption, NumericOption


class OptionsDialog(QDialog):
    def __init__(self, options: Dict[str, DataOption], parent: QWidget = None) -> None:
        super().__init__(parent)

        self._options = options

        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self._widgets: Dict[str, QWidget] = {}
        for k, v in options.items():
            if not isinstance(k, str):
                continue

            label = QLabel(v.name, self)
            if isinstance(v, NumericOption):
                widget = self._get_spin_box(v.value, v.min, v.max)

            form_layout.addRow(label, widget)
            self._widgets[k] = widget

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _get_spin_box(self, value: Number, min: Number, max: Number) -> QWidget:
        if min is None:
            min = -99999999
        if max is None:
            max = 99999999

        if isinstance(value, int):
            sb = QSpinBox(self)
        elif isinstance(value, float):
            sb = QDoubleSpinBox(self)
        else:
            raise TypeError("Value must be int or float")

        sb.setRange(min, max)
        sb.setValue(value)
        return sb

    @property
    def values(self) -> Dict[str, Any]:
        values = {}
        for k, widget in self._widgets.items():
            if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                value = widget.value()
            else:
                continue

            values[k] = value

        return values
