import pandas as pd

from yapsy.IPlugin import IPlugin


class ParseError(Exception):
    pass


class CSVParser(IPlugin):
    name = "Generic Parser"

    sample_rate = None
    header_row = None

    def parse(self, filename: str, **kwargs) -> pd.DataFrame:
        if self.header_row is None:
            self.header_row = 1

        df = pd.read_csv(filename, header=self.header_row - 1)
        df.columns = df.columns.str.replace(r'''[:,',",\s]+''', '_', regex=True)
        return df


class Filter(IPlugin):
    name = "Base Filter"

    def filter(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        return df