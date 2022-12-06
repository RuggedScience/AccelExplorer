import csv
import re

import pandas as pd

from app.categories import CSVParser, ParseError


class NULabsCSVParser(CSVParser):
    name = 'NU Labs'
    header_row = 16
    sample_rate = 0

    def parse(self, filename: str, **kwargs) -> pd.DataFrame:
        with open(filename, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                name = row[0]
                value = row[1]
                if re.search('sample rate', name, re.IGNORECASE):
                    self.sample_rate = int(value)
                    break

        if self.sample_rate == 0:
            raise ParseError('Cound not find sample rate')

        return super().parse(filename, **kwargs)