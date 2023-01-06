__all__ = ["NULabsCSVParser"]

import linecache

import pandas as pd

from app.plugins import CSVParser, ParseError


class NULabsCSVParser(CSVParser):
    name = "NU Labs"
    header_row = 16
    sample_rate = 0

    def _get_sample_rate(self, filename: str) -> int:
        sample_rate_row = linecache.getline(filename, 8).lower()
        if sample_rate_row.startswith("sample rate"):
            value = sample_rate_row.split(",")[1]
            try:
                return int(value)
            except:
                pass

        raise ParseError("Could not find sample rate")

    def can_parse(self, filename: str) -> bool:
        try:
            self._get_sample_rate(filename)
        except:
            return False
        return True

    def parse(self, filename: str) -> pd.DataFrame:
        self.sample_rate = self._get_sample_rate(filename)
        df = super().parse(filename)
        return df.iloc[:, 1:]
