from typing import List

from PySide6.QtWidgets import QDialog, QWidget, QDialogButtonBox, QTextEdit
from PySide6.QtCore import QFileInfo, Qt
from PySide6.QtGui import QBrush, QColor, QTextFormat, QTextCursor

from pandas import DataFrame

from .ui.ui_parserdialog import Ui_Dialog
from .csvparser import parsers, ParseError, CSVParser

class ParserDialog(QDialog):
    def __init__(self, filename: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.buttonBox.button(QDialogButtonBox.Ok).setText("Parse")
        
        self.ui.typeComboBox.addItems([parser.display_name for parser in parsers])
        self.ui.typeComboBox.currentIndexChanged.connect(self.typeChanged)
        self.ui.headerRowSpinBox.valueChanged.connect(self.headerRowChanged)

        self.setCSVFile(filename)
        self.headerRowChanged(self.ui.headerRowSpinBox.value())

        self._df = None
    
    @property
    def sampleRate(self) -> int:
        return self.ui.sampleRateSpinBox.value()

    @property
    def df(self) -> DataFrame:
        return self._df

    def setCSVFile(self, filename: str) -> None:
        info = QFileInfo(filename)
        self.setWindowTitle(info.fileName())

        with open(filename) as csvfile:
            self.ui.csvViewer.setPlainText(csvfile.read())

        self._filename = filename

        # Try all of the specific parsers to see
        # if any successfully parse the CSV file.
        for i, parser_class in enumerate(parsers):
            if i == 0:
                continue

            parser = parser_class(filename)
            try:
                df = parser.parse()
            except ParseError:
                #self.ui.typeComboBox.setItemData(i, QBrush(Qt.red), Qt.ForegroundRole)
                self.ui.typeComboBox.setItemData(i, QBrush(Qt.red), Qt.BackgroundRole)
                continue

            self.ui.sampleRateSpinBox.setValue(parser.sample_rate)
            self.ui.headerRowSpinBox.setValue(parser.header_row)
            self.ui.typeComboBox.setCurrentIndex(i)
            self._df = df


    def typeChanged(self, index: int) -> None:
        parser_class = parsers[index]
        self.ui.sampleRateSpinBox.setEnabled(parser_class.sample_rate is None)
        self.ui.headerRowSpinBox.setEnabled(parser_class.header_row is None)
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

        index = self.ui.typeComboBox.currentIndex()
        parser_class = parsers[index]
        parser = parser_class(self._filename)

        if self.ui.headerRowSpinBox.isEnabled():
            parser.header_row = self.ui.headerRowSpinBox.value()

        try: 
            self._df = parser.parse()
        except ParseError as ex:
            print(ex)
            return

        if index != 0:
            self.ui.sampleRateSpinBox.setValue(parser.sample_rate)

        return super().accept()
