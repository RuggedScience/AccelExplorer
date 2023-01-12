__all__ = ["AllenCSVParser"]

import linecache
from typing import Dict

import pandas as pd

from app.plugins import parserplugins


class AllenCSVParser(parserplugins.AccelCSVParser):
    @property
    def display_name(self) -> str:
        return "Allen Parser"

    @property
    def header_row(self) -> int:
        return 29

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

        # First column should be time which we don't need since
        # AccelCSVParser uses the sample rate to create a time index.
        df.drop(df.columns[0], axis="columns", inplace=True)

        col_name = df.columns[0]
        df[col_name] = df[col_name].apply(lambda x: (6.6 - x) * 200)
        df.rename(columns={col_name: "Acceleration"}, inplace=True)
        return df

    def _get_sample_rate(self, filename: str) -> int:
        sample_rate_row = linecache.getline(filename=filename, lineno=22).lower()
        if sample_rate_row.startswith("sampling period"):
            value = sample_rate_row.split(",")[1]
            try:
                return int(1 / float(value))
            except:
                pass

        raise parserplugins.ParseError("Could not find sample rate")
