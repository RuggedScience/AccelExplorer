__all__ = ['NULabsCSVParser']

import csv
import re

import pandas as pd

from app.categories import CSVParser, ParseError


class NULabsCSVParser(CSVParser):
    name = 'NU Labs'
    header_row = 16
    time_units = 'Milliseconds'

    def parse(self, filename: str, **kwargs) -> pd.DataFrame:
        # We don't use the sample rate but this helps
        # determine if this is actually a NU labs file.
        sample_rate = None
        with open(filename, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                name = row[0]
                value = row[1]
                if re.search('sample rate', name, re.IGNORECASE):
                    sample_rate = int(value)
                    break

        if not sample_rate:
            raise ParseError('Cound not find sample rate')

        return super().parse(filename, **kwargs)