from typing import Dict, List

import pandas as pd
from PySide6.QtCore import QFileInfo
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QMessageBox, QWidget

from app.utils.optionsuimanager import OptionsUiManager
from app.plugins.parserplugins import CSVParser, ParseError
from app.ui.ui_parserdialog import Ui_Dialog


class ParserDialog(QDialog):
    def __init__(
        self,
        filename: str,
        parsers: List[CSVParser],
        default_parser: CSVParser = None,
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self._options_manager = OptionsUiManager(self.ui.optionsLayout)
        self._options_manager.change_callback = self._update_headers

        self.ui.buttonBox.button(QDialogButtonBox.Ok).setText("Parse")

        self._parsers: Dict[str, CSVParser] = {
            parser.display_name: parser for parser in parsers
        }

        self.ui.typeComboBox.addItems(self._parsers.keys())

        self.ui.typeComboBox.currentTextChanged.connect(self._typeChanged)
        self.ui.headerRowSpinBox.valueChanged.connect(self._headerRowChanged)
        self.ui.csvViewer.lineNumberChanged.connect(self.ui.headerRowSpinBox.setValue)

        self.setCSVFile(filename)

        if default_parser:
            self.ui.typeComboBox.setCurrentText(default_parser.display_name)

        self._typeChanged()

        self._df = None

    @property
    def df(self) -> pd.DataFrame:
        return self._df

    @property
    def _parser(self) -> CSVParser:
        parser_name = self.ui.typeComboBox.currentText()
        return self._parsers[parser_name]

    def setCSVFile(self, filename: str) -> None:
        info = QFileInfo(filename)
        self.setWindowTitle(info.fileName())

        with open(filename) as csvfile:
            self.ui.csvViewer.setPlainText(csvfile.read())

        self._filename = filename

    def _typeChanged(self) -> None:
        parser_type = self.ui.typeComboBox.currentText()
        parser = self._parsers[parser_type]

        header_row = parser.header_row or 1
        self.ui.headerRowSpinBox.setValue(header_row)
        self._headerRowChanged(header_row)

        self._options_manager.options = parser.options

    def _headerRowChanged(self, value: int) -> None:
        self.ui.csvViewer.setCurrentLine(value)
        self._update_headers()

    def _update_headers(self) -> None:
        while self.ui.headerLayout.count():
            child = self.ui.headerLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        line = self.ui.headerRowSpinBox.value()
        options = self._options_manager.values
        headers = self._parser.get_headers(self._filename, line, **options)
        for header in headers:
            cb = QCheckBox(header)
            cb.setChecked(True)
            self.ui.headerLayout.addWidget(cb)

    def accept(self) -> None:
        header_row = self.ui.headerRowSpinBox.value()
        parser = self._parsers[self.ui.typeComboBox.currentText()]

        usecols = []
        for i in range(self.ui.headerLayout.count()):
            item = self.ui.headerLayout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, QCheckBox):
                if widget.isChecked():
                    usecols.append(widget.text())

        try:
            options = self._options_manager.values
            self._df = parser.parse(
                self._filename, header_row=header_row, usecols=usecols, **options
            )
            return super().accept()
        except ValueError as ex:
            QMessageBox.warning(
                self,
                "Parsing Error",
                "Unable to parse file.\nVerify the header row is correct.",
            )
        except ParseError as ex:
            QMessageBox.warning(self, "Parsing Error", str(ex))

    def exec(self) -> pd.DataFrame:
        ret = super().exec()
        if ret:
            return self._df
