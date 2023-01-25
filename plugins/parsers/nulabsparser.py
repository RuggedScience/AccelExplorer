__all__ = ["NULabsCSVParser"]

import linecache

from app.plugins import parserplugins
from app.views import ViewModel


class NULabsCSVParser(parserplugins.CSVParser):
    def can_parse(self, filename: str) -> bool:
        try:
            self._get_sample_rate(filename)
        except:
            return False
        return True

    def parse(self, filename: str) -> ViewModel:
        sample_rate = self._get_sample_rate(filename)
        df = self._parse_to_df(
            filename=filename, sample_rate=sample_rate, header_row=16
        )
        df = df.iloc[:, 1:]
        return ViewModel(df, y_axis="Acceleration (g)")

    def _get_sample_rate(self, filename: str) -> int:
        sample_rate_row = linecache.getline(filename, 8).lower()
        if sample_rate_row.startswith("sample rate"):
            value = sample_rate_row.split(",")[1]
            try:
                return int(value)
            except:
                pass

        raise parserplugins.ParseError("Could not find sample rate")
