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
        # Only keep columns with numbers
        df = df.select_dtypes(include=["number"])
        # Drop columns that contain only NaN values
        df.dropna(axis="columns", how="all", inplace=True)
        for col in df:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise ValueError("All columns must be numeric")

        if df.empty:
            raise ParseError("No numeric data found")

        if sample_rate:
            spacing = 1 / sample_rate
            df.set_index(
                pd.to_timedelta([spacing * i for i in range(len(df))], unit="S"),
                inplace=True,
            )
        elif index_type and index_type != "number":
            time_units = index_type
            if index_type == "timestamp":
                time_units = None
            df.index = pd.to_timedelta(df.index, unit=time_units)

            start_time = df.index[0]
            df.index = df.index - start_time

        if df.index.inferred_type == "timedelta64":
            df.index.rename("Time (s)", inplace=True)

        return df
