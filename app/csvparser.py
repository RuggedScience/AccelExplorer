import csv
import re
import sys
from typing import List, Type

import pandas as pd


class ParseError(Exception):
    pass

class CSVParser:
    # These should be set by any subclasses
    display_name = 'Generic'
    sample_rate = None
    header_row = None
    
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def parse(self) -> pd.DataFrame:
        if self.header_row is None:
            self.header_row = 1

        df = pd.read_csv(self.filename, header=self.header_row - 1)
        df.columns = df.columns.str.replace(r'''[:,',",\s]+''', '_', regex=True)
        return df


class NULabsCSVParser(CSVParser):
    display_name = 'NU Labs'
    header_row = 16
    sample_rate = 0

    def parse(self) -> pd.DataFrame:
        with open(self.filename, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                name = row[0]
                value = row[1]
                if re.search('sample rate', name, re.IGNORECASE):
                    self.sample_rate = int(value)
                    break

        if self.sample_rate == 0:
            raise ParseError('Cound not find sample rate')

        return super().parse()

class AllenCSVParser(CSVParser):
    display_name = 'Allen'
    header_row = 29
    sample_rate = 0

    def parse(self) -> pd.DataFrame:
        with open(self.filename, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                name = row[0]
                value = row[1]
                if re.search('sampling period', name, re.IGNORECASE):
                    self.sample_rate = int(1 / float(value))
                    break

        if self.sample_rate == 0:
            raise ParseError('Could not find sample rate')

        df = super().parse()
        df.columns.values[0] = "Time"
        df.columns.values[1] = "Voltage"
        df = df[['Time', 'Voltage']]
        df["g_s"] = df['Voltage'].apply(lambda x: (6.6 - x) * 200)
        df.drop('Voltage', axis=1, inplace=True)
        return df

parsers: List[Type[CSVParser]] = [CSVParser, NULabsCSVParser, AllenCSVParser]