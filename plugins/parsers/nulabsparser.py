__all__ = ["NULabsCSVParser"]

import linecache
from pathlib import Path

from app.plugins import parserplugins
from app.views import ViewModel


class NULabsCSVParser(parserplugins.CSVParser):
    def parse(self, file: Path) -> ViewModel:
        sample_rate = self._get_sample_rate(file)
        df = self._parse_to_df(file=file, sample_rate=sample_rate, header_row=16)
        df = df.iloc[:, 1:]
        return ViewModel(df, y_axis="Acceleration (g)")

    def _get_sample_rate(self, file: Path) -> int:
        sample_rate_row = linecache.getline(str(file), 8).lower()
        if sample_rate_row.startswith("sample rate"):
            value = sample_rate_row.split(",")[1]
            try:
                return int(value)
            except:
                pass

        raise parserplugins.ParseError("Could not find sample rate")
