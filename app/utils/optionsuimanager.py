from typing import Any, Callable, Dict

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
    QWidget,
    QCheckBox,
)

from app.plugins.options import DataOption, ListOption, NumericOption, BoolOption


class OptionsUiManager:
    def __init__(self, layout: QFormLayout, options: Dict[str, DataOption] = {}):
        self._layout = layout
        self._options = options
        self._widgets: Dict[str, QWidget] = {}
        self._callback = None

    @property
    def change_callback(self) -> Callable | None:
        return self._callback

    @change_callback.setter
    def change_callback(self, callback: Callable) -> None:
        for widget in self._widgets.values():
            if isinstance(widget, QComboBox):
                if self._callback:
                    widget.currentTextChanged.diconnect(self._callback) #type: ignore
                widget.currentTextChanged.connect(callback)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                if self._callback:
                    widget.valueChanged.disconnect(self._callback)
                widget.valueChanged.connect(callback)

        self._callback = callback

    @property
    def options(self) -> Dict[str, DataOption]:
        return self._options.copy()

    @options.setter
    def options(self, options: Dict[str, DataOption]):
        self._options = options.copy()
        for widget in self._widgets.values():
            self._layout.removeRow(widget)

        self._widgets.clear()

        for k, v in options.items():
            if not isinstance(k, str):
                continue

            if isinstance(v, NumericOption):
                min = v.min or -99999999
                max = v.max or 99999999

                if isinstance(v.value, int):
                    widget = QSpinBox()
                    widget.setRange(int(min), int(max))
                    widget.setValue(v.value)
                elif isinstance(v.value, float):
                    widget = QDoubleSpinBox()
                    widget.setRange(float(min), float(max))
                    widget.setValue(v.value)
                else:
                    raise TypeError("Numeric options must be either int or float types")

                if self._callback:
                    widget.valueChanged.connect(self._callback)
            elif isinstance(v, ListOption):
                widget = QComboBox()
                widget.addItems([i.name for i in v.options])
                if self._callback:
                    widget.currentTextChanged.connect(self._callback)
            elif isinstance(v, BoolOption):
                widget = QCheckBox()
                widget.setChecked(v.checked)
            else:
                raise TypeError("Invalid option type")

            self._layout.addRow(v.name, widget)
            self._widgets[k] = widget

    @property
    def values(self) -> Dict[str, Any]:
        values = {}
        for k, widget in self._widgets.items():
            value = None
            if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                value = widget.value()
            elif isinstance(widget, QComboBox):
                list_option = self._options[k]
                assert isinstance(list_option, ListOption)

                text = widget.currentText()
                options = list_option.options
                for option in options:
                    if option.name == text:
                        value = option.value
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()

            if value is not None:
                values[k] = value

        return values

    @property
    def widgets(self) -> Dict[str, QWidget]:
        return self._widgets.copy()
