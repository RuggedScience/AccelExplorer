__all__ = ["HWiNFOParser"]

import csv

from pathlib import Path

import numpy as np

from app.plugins import parserplugins
from app.views import ViewModel


class HWiNFOParser(parserplugins.CSVParser):
    def parse(self, file: Path) -> ViewModel:
        usecols = self._get_headers(file)
        try:
            df = self._parse_to_df(
                file=file,
                encoding="iso-8859-1",
                quoting=csv.QUOTE_MINIMAL,
                parse_dates=[['Date', 'Time']],
                date_format="%d.%m.%Y %H:%M:%S.%f",
                index_col='Date_Time',
                usecols=usecols,
            )
        except ValueError as e:
            raise parserplugins.ParseError("Missing Date/Time columns")
        return ViewModel(df, y_axis="")

    def _get_headers(self, file: Path) -> list[str]:
        line = ""
        with file.open("r", encoding="iso-8859-1") as f:
            line = f.readline()

        # Parse the headers using the built in CSV lib
        reader = csv.reader([line], quoting=csv.QUOTE_MINIMAL)
        headers = list(reader)[0]
        return [header for header in headers if header]
