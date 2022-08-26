import csv
import re

import pandas as pd

class ParseError(Exception):
    pass

class CSVParser:
    __display_name__ = 'Generic CSV Parser (1000Hz sample)'

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self._sample_rate = None    

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def parse(self, header_row: int = 1) -> pd.DataFrame:
        df = pd.read_csv(self.filename, header=header_row)
        return df


class NULabsCSVParser(CSVParser):
    __display_name__ = 'NU Labs CSV parser'

    def parse(self) -> pd.DataFrame:
        sample_rate = None
        header_row = None
        with open(self.filename, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                name = row[0]
                value = row[1]
                if re.search('sample rate', name, re.IGNORECASE):
                    sample_rate = int(value)

                if 'X:' in name and 'Y:' in value:
                    header_row = reader.line_num - 1
                    break

        if sample_rate is None or header_row is None:
            raise ParseError('CSV is not a valid NU Labs file')

        self._sample_rate = sample_rate
        return super().parse(header_row)
