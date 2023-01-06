from typing import List

from PySide6.QtWidgets import QDialog, QWidget, QDialogButtonBox
from PySide6.QtCore import QFileInfo, Qt
from PySide6.QtGui import QBrush

import pandas as pd

from .utils import get_plugin_manager
from .ui.ui_parserdialog import Ui_Dialog
from .plugins import CSVParser, ParseError


class ParserDialog(QDialog):
    def __init__(self, filename: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.buttonBox.button(QDialogButtonBox.Ok).setText("Parse")

        pm = get_plugin_manager()
        pm.setCategoriesFilter({"Parsers": CSVParser})
        pm.collectPlugins()

        self.parsers = {"Generic Parser": CSVParser()}
        for plugin in pm.getPluginsOfCategory("Parsers"):
            if isinstance(plugin.plugin_object, CSVParser):
                self.parsers[plugin.plugin_object.name] = plugin.plugin_object

        self.ui.typeComboBox.addItems(self.parsers.keys())

        self.ui.typeComboBox.currentTextChanged.connect(self._typeChanged)
        self.ui.timeUnitsComboBox.currentTextChanged.connect(self._update_ui)
        self.ui.headerRowSpinBox.valueChanged.connect(self._headerRowChanged)
        self.ui.csvViewer.lineNumberChanged.connect(self.ui.headerRowSpinBox.setValue)

        self.setCSVFile(filename)
        self._headerRowChanged(self.ui.headerRowSpinBox.value())

        self._df = None

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    def setCSVFile(self, filename: str) -> None:
        info = QFileInfo(filename)
        self.setWindowTitle(info.fileName())

        with open(filename) as csvfile:
            self.ui.csvViewer.setPlainText(csvfile.read())

        self._filename = filename

        # Try all of the specific parsers to see
        # if any successfully parse the CSV file.

        found = False
        for i, parser in enumerate(self.parsers.values()):
            # If either one of these is none, the parser requires
            # user input to properly work. Skip those.
            if (
                parser.sample_rate is None and parser.time_units is None
            ) or parser.header_row is None:
                continue

            if parser.can_parse(filename):
                if not found:
                    self.ui.typeComboBox.setCurrentIndex(i)
                    self._update_ui()
                    found = True
            else:
                self.ui.typeComboBox.setItemData(i, QBrush(Qt.red), Qt.BackgroundRole)

    def _typeChanged(self) -> None:
        parser_type = self.ui.typeComboBox.currentText()
        parser = self.parsers[parser_type]

        self.ui.timeUnitsComboBox.setCurrentText(parser.time_units or "None")

        if parser.header_row:
            self.ui.headerRowSpinBox.setValue(parser.header_row)

        self._update_ui()

    def _update_ui(self) -> None:
        parser_type = self.ui.typeComboBox.currentText()
        parser = self.parsers[parser_type]

        self.ui.timeUnitsComboBox.setEnabled(parser.time_units is None)

        time_units = self.ui.timeUnitsComboBox.currentText()
        self.ui.sampleRateSpinBox.setEnabled(
            parser.sample_rate is None and time_units == "None"
        )

        self.ui.headerRowSpinBox.setEnabled(parser.header_row is None)

    def _headerRowChanged(self, value: int) -> None:
        self.ui.csvViewer.setCurrentLine(value)

    def accept(self) -> None:
        name = self.ui.typeComboBox.currentText()
        parser = self.parsers[name]

        time_units = self.ui.timeUnitsComboBox.currentText()
        if self.ui.timeUnitsComboBox.isEnabled() and time_units != "None":
            parser.time_units = time_units.lower()
        else:
            parser.sample_rate = self.ui.sampleRateSpinBox.value()

        if self.ui.headerRowSpinBox.isEnabled():
            parser.header_row = self.ui.headerRowSpinBox.value()

        try:
            self._df = parser.parse(self._filename)
        except ParseError as ex:
            print(ex)
            return

        if parser.sample_rate != None:
            self.ui.sampleRateSpinBox.setValue(parser.sample_rate)

        return super().accept()
