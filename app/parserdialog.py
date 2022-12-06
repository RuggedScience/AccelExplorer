import os
from typing import List

from yapsy.PluginManager import PluginManager, PluginManagerSingleton
from PySide6.QtWidgets import QDialog, QWidget, QDialogButtonBox, QTextEdit
from PySide6.QtCore import QFileInfo, Qt
from PySide6.QtGui import QBrush, QColor, QTextFormat, QTextCursor

import pandas as pd

from .ui.ui_parserdialog import Ui_Dialog
from .categories import CSVParser, ParseError

class ParserDialog(QDialog):
    def __init__(self, filename: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.buttonBox.button(QDialogButtonBox.Ok).setText("Parse")

        pm: PluginManager = PluginManagerSingleton.get()
    
        self.parsers = {'Generic Parser': CSVParser()}
        for plugin in pm.getPluginsOfCategory("Parsers"):
            if isinstance(plugin.plugin_object, CSVParser):
                self.parsers[plugin.plugin_object.name] = plugin.plugin_object

        self.ui.typeComboBox.addItems(self.parsers.keys())

        self.ui.typeComboBox.currentTextChanged.connect(self.typeChanged)
        self.ui.headerRowSpinBox.valueChanged.connect(self.headerRowChanged)

        self.setCSVFile(filename)
        self.headerRowChanged(self.ui.headerRowSpinBox.value())

        self._df = None
    
    @property
    def sampleRate(self) -> int:
        return self.ui.sampleRateSpinBox.value()

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
        for i, parser in enumerate(self.parsers.values()):
            # If either one of these is none, the parser requires
            # user input to properly work. Skip those.
            if parser.sample_rate is None or parser.header_row is None:
                continue

            try:
                df = parser.parse(filename)
            except (ParseError):
                self.ui.typeComboBox.setItemData(i, QBrush(Qt.red), Qt.BackgroundRole)
                continue

            self.ui.sampleRateSpinBox.setValue(parser.sample_rate)
            self.ui.headerRowSpinBox.setValue(parser.header_row)
            self.ui.typeComboBox.setCurrentIndex(i)
            self._df = df


    def typeChanged(self, text: str) -> None:
        parser = self.parsers[text]
        self.ui.sampleRateSpinBox.setEnabled(parser.sample_rate is None)
        self.ui.headerRowSpinBox.setEnabled(parser.header_row is None)
        self._df = None

    def headerRowChanged(self, value: int) -> None:
        selection = QTextEdit.ExtraSelection()    
        lineColor = QColor(Qt.yellow).lighter(160)

        selection.format.setBackground(lineColor)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)

        block = self.ui.csvViewer.document().findBlockByLineNumber(value - 1)
        selection.cursor = QTextCursor(block)
        selection.cursor.clearSelection()

        self.ui.csvViewer.setExtraSelections([selection])

        self.ui.csvViewer.setTextCursor(selection.cursor);

    def accept(self) -> None:
        # If the auto parsing worked we are done already.
        if self._df is not None:
            return super().accept()

        name = self.ui.typeComboBox.currentText()
        parser = self.parsers[name]

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

    @staticmethod
    def supported_extensions() -> List[str]:
        return ['csv']