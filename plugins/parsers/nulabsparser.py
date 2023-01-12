__all__ = ["NULabsCSVParser"]

import linecache

from typing import Dict

import pandas as pd

from app.plugins import parserplugins


class NULabsCSVParser(parserplugins.CSVParser):
    def can_parse(self, filename: str) -> bool:
        try:
            self._get_sample_rate(filename)
        except:
            return False
        return True

    def parse(self, filename: str) -> pd.DataFrame:
        sample_rate = self._get_sample_rate(filename)
        df = super().parse(filename, sample_rate=sample_rate, header_row=16)
        return df.iloc[:, 1:]

    def _get_sample_rate(self, filename: str) -> int:
        sample_rate_row = linecache.getline(filename, 8).lower()
        if sample_rate_row.startswith("sample rate"):
            value = sample_rate_row.split(",")[1]
            try:
                return int(value)
            except:
                pass

        raise parserplugins.ParseError("Could not find sample rate")
