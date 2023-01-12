import os
from abc import ABC, abstractmethod
from typing import List

import pandas as pd
from yapsy.IPlugin import IPlugin


class ParseError(Exception):
    pass


class ParserPlugin(IPlugin, ABC):
    def __init__(self):
        super().__init__()

    @staticmethod
    @abstractmethod
    def supported_extensions() -> List[str]:
        pass

    @abstractmethod
    def can_parse(self, filename: str) -> bool:
        pass

    @abstractmethod
    def parse(self, filename: str, **kwargs) -> pd.DataFrame:
        pass


class CSVParser(ParserPlugin):
    @staticmethod
    def supported_extensions() -> List[str]:
        return ["csv"]

    def can_parse(self, filename: str) -> bool:
        return os.path.exists(filename)

    def parse(
        self,
        filename: str,
        header_row: int = 1,
        index_type: str = None,
        sample_rate: int = None,
        **kwargs,
    ) -> pd.DataFrame:
        if index_type:
            index_type = index_type.lower()

        df = pd.read_csv(filename, header=header_row - 1, **kwargs)
        df.dropna(axis="columns", inplace=True)
        if df.isna().values.any():
            raise ValueError()

        for col in df:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise ValueError()

        if sample_rate:
            spacing = 1 / sample_rate
            df.set_index(
                pd.to_timedelta([spacing * i for i in range(len(df))], unit="S"),
                inplace=True,
            )
        elif index_type and index_type != "number":
            time_units = None
            if index_type != "timestamp":
                time_units = index_type
                start_time = df.index[0]
                if start_time != 0:
                    df.index = df.index - start_time
            df.index = pd.to_timedelta(df.index, unit=time_units)
            df.index.rename("Time (s)", inplace=True)
        return df
