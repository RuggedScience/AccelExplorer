__all__ = ["NULabsCSVParser"]

import linecache

from typing import Dict

import pandas as pd

from app.plugins import parserplugins


class NULabsCSVParser(parserplugins.AccelCSVParser):
    @property
    def display_name(self) -> str:
        return "NU Parser"

    @property
    def header_row(self) -> int:
        return 16

    @property
    def options(self) -> Dict[str, parserplugins.DataOption]:
        return {}

    def can_parse(self, filename: str) -> bool:
        try:
            self._get_sample_rate(filename)
        except:
            return False
        return True

    def parse(self, filename: str, **kwargs) -> pd.DataFrame:
        sample_rate = self._get_sample_rate(filename)
        df = super().parse(filename, sample_rate=sample_rate, **kwargs)
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
