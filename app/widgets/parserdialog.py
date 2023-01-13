import linecache
from typing import Dict

import pandas as pd
from PySide6.QtCore import QFileInfo
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QMessageBox, QWidget

from app.plugins.parserplugins import CSVParser, ParseError
from app.ui.ui_parserdialog import Ui_Dialog


class ParserDialog(QDialog):
    def __init__(
        self,
        filename: str,
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self._column_checkboxes: Dict[str, QCheckBox] = {}

        self.ui.buttonBox.button(QDialogButtonBox.Ok).setText("Parse")

        self.ui.headerRowSpinBox.valueChanged.connect(self._headerRowChanged)
        self.ui.csvViewer.lineNumberChanged.connect(self.ui.headerRowSpinBox.setValue)
        self.ui.indexComboBox.currentTextChanged.connect(self._indexChanged)

        self.setCSVFile(filename)
        self._update_headers()
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

    def _indexChanged(self) -> None:
        currentIndex = self.ui.indexComboBox.currentText()
        for name, cb in self._column_checkboxes.items():
            if name == currentIndex:
                cb.setChecked(True)
            cb.setHidden(name == currentIndex)

        self.ui.indexTypeComboBox.setEnabled(
            currentIndex not in ("None", "Sample Rate")
        )
        self.ui.sampleRateSpinBox.setEnabled(currentIndex == "Sample Rate")

    def _headerRowChanged(self, value: int) -> None:
        self.ui.csvViewer.setCurrentLine(value)
        self._update_headers()

    def _update_headers(self) -> None:
        while self.ui.headerLayout.count():
            child = self.ui.headerLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._column_checkboxes.clear()

        lineno = self.ui.headerRowSpinBox.value()
        headers = linecache.getline(self._filename, lineno).strip().split(",")
        # Remove blank headers
        headers = [header for header in headers if header]
        for header in headers:
            cb = QCheckBox(header)
            cb.setChecked(True)
            self.ui.headerLayout.addWidget(cb)
            self._column_checkboxes[header] = cb

        self.ui.indexComboBox.clear()
        self.ui.indexComboBox.addItems(["None", "Sample Rate"] + headers)
        self.ui.indexComboBox.setCurrentIndex(0)
        self._indexChanged()

    def accept(self) -> None:
        header_row = self.ui.headerRowSpinBox.value()
        parser = CSVParser()

        usecols = []
        for cb in self._column_checkboxes.values():
            if cb.isChecked():
                usecols.append(cb.text())

        index = self.ui.indexComboBox.currentText()
        index_type = None
        sample_rate = None
        if index == "None":
            index = None
        elif index == "Sample Rate":
            index = None
            sample_rate = self.ui.sampleRateSpinBox.value()
        else:
            index_type = self.ui.indexTypeComboBox.currentText()

        try:
            self._df = parser.parse(
                self._filename,
                header_row=header_row,
                usecols=usecols,
                index_col=index,
                index_type=index_type,
                sample_rate=sample_rate,
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
