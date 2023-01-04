__all__ = ["NULabsCSVParser"]

import linecache

import pandas as pd

from app.categories import CSVParser, ParseError


class NULabsCSVParser(CSVParser):
    name = "NU Labs"
    header_row = 16
    time_units = "Milliseconds"

    def can_parse(self, filename: str) -> bool:
        sample_rate_row = linecache.getline(filename, 8).lower()
        return sample_rate_row.startswith("sample rate")

    def parse(self, filename: str) -> pd.DataFrame:
        if not self.can_parse(filename):
            raise ParseError("Cound not find sample rate")

        return super().parse(filename)
