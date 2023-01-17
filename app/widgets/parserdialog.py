import linecache
from collections.abc import Iterable

import pandas as pd
from PySide6.QtCore import QFileInfo
from PySide6.QtWidgets import QCheckBox, QDialog, QMessageBox, QWidget

from app.plugins.parserplugins import CSVParser, ParseError
from app.ui.ui_parserdialog import Ui_Dialog


class ParserDialog(QDialog):
    def __init__(
        self,
        files: list[str],
        parent: QWidget = None,
    ) -> None:
        if not isinstance(files, Iterable):
            files = [files]
        elif len(files) == 0:
            raise ValueError("No files to parse")

        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self._column_checkboxes: dict[str, QCheckBox] = {}
        self._dfs: dict[str, pd.DataFrame] = {}
        self._skipped_files = set()

        self.ui.headerRowSpinBox.valueChanged.connect(self._headerRowChanged)
        self.ui.csvViewer.lineNumberChanged.connect(self.ui.headerRowSpinBox.setValue)
        self.ui.indexComboBox.currentTextChanged.connect(self._indexChanged)

        self.ui.skip_button.clicked.connect(self._skip)
        self.ui.parse_button.clicked.connect(self._parse_next)
        self.ui.parseAll_button.clicked.connect(self._parse_all)
        self.ui.finish_button.clicked.connect(self.accept)
        self.ui.cancel_button.clicked.connect(self.reject)

        self.ui.skip_button.setHidden(len(files) == 1)
        self.ui.parseAll_button.setHidden(len(files) == 1)
        self.ui.finish_button.setHidden(len(files) == 1)

        self.set_files(files)

    @property
    def _current_file(self) -> str:
        return self._files[self._file_index]

    def set_files(self, files: Iterable[str]) -> None:
        self._file_index = 0
        self._previous_headers = []
        self._files: list = list(files)
        self._handle_file_changed()

    def _handle_file_changed(self) -> None:
        filename = self._files[self._file_index]
        info = QFileInfo(filename)
        self.setWindowTitle(
            f"{self._file_index + 1} / {len(self._files)} - {info.fileName()}"
        )

        with open(filename) as csvfile:
            self.ui.csvViewer.setPlainText(csvfile.read())

        self._headerRowChanged(self.ui.headerRowSpinBox.value())

    def _set_next_file(self) -> bool:
        if self._file_index + 1 >= len(self._files):
            self.ui.skip_button.setEnabled(False)
            return False

        self._file_index += 1
        self.ui.skip_button.setEnabled(True)
        self._handle_file_changed()
        return True

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

    def _get_headers(self, filename: str) -> list[str]:
        lineno = self.ui.headerRowSpinBox.value()
        headers = linecache.getline(filename, lineno).strip().split(",")
        # Remove blank headers
        return [header for header in headers if header]

    def _update_headers(self) -> None:
        filename = self._files[self._file_index]
        headers = self._get_headers(filename)
        # If the headers didn't change, lets keep everything the same.
        # Prevents the current item from resetting when switching to
        # next file if the files are the same format.
        if set(headers) == set(self._previous_headers):
            return

        self._previous_headers = headers
        while self.ui.headerLayout.count():
            child = self.ui.headerLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._column_checkboxes.clear()

        for header in headers:
            cb = QCheckBox(header)
            cb.setChecked(True)
            self.ui.headerLayout.addWidget(cb)
            self._column_checkboxes[header] = cb

        self.ui.indexComboBox.clear()
        self.ui.indexComboBox.addItems(["None"] + headers + ["Sample Rate"])
        self.ui.indexComboBox.setCurrentIndex(0)
        self.ui.indexTypeComboBox.setCurrentIndex(0)
        self._indexChanged()

    def _parse(self, filename: str) -> bool:
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
            self._dfs[filename] = parser.parse(
                filename,
                header_row=header_row,
                usecols=usecols,
                index_col=index,
                index_type=index_type,
                sample_rate=sample_rate,
            )
            # If we have at least one file parsed
            # we can let the user finish. Otherwise
            # they should just click cancel.
            self.ui.finish_button.setEnabled(True)
            return True
        except ValueError as ex:
            QMessageBox.warning(
                self,
                "Parsing Error",
                "Unable to parse file.\nVerify the header row is correct.",
            )
        except ParseError as ex:
            QMessageBox.warning(self, "Parsing Error", str(ex))

        return False

    def _skip(self) -> None:
        self._skipped_files.add(self._current_file)
        self._set_next_file()

    def _parse_next(self) -> bool:
        filename = self._current_file
        if self._parse(filename):
            if not self._set_next_file():
                self.accept()

    def _parse_all(self) -> None:
        # Store the current headers. We only want to parse
        # files with the exact same headers.
        headers = None
        while True:
            filename = self._current_file
            if headers is None:
                headers = set(self._get_headers(filename))

            if headers == set(self._get_headers(filename)):
                if not self._parse(filename):
                    break

            if not self._set_next_file():
                break

        files = set(self._files)
        # Get all remaining files that haven't been parsed
        unparsed_files = files.difference(set(self._dfs.keys()))
        # Remove files the user skipped
        unparsed_files = unparsed_files.difference(self._skipped_files)

        if unparsed_files:
            self.set_files(unparsed_files)
        else:
            self.accept()

    def exec(self) -> pd.DataFrame:
        self._dfs.clear()
        self.ui.finish_button.setDisabled(True)
        ret = super().exec()
        if ret:
            return self._dfs.copy()
