from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd
from yapsy.IPlugin import IPlugin

from app.utils import generate_time_index
from app.views import ViewModel


class ParseError(Exception):
    pass


class ParserPlugin(IPlugin, ABC):
    def __init__(self):
        super().__init__()

    @staticmethod
    @abstractmethod
    def supported_extensions() -> tuple[str]:
        pass

    @abstractmethod
    def parse(self, file: Path, **kwargs) -> ViewModel:
        pass


class CSVParser(ParserPlugin):
    @staticmethod
    def supported_extensions() -> tuple[str]:
        return ("csv",)

    def _parse_to_df(
        self,
        file: Path,
        header_row: int = 1,
        index_type: str = None,
        sample_rate: int = None,
        **kwargs,
    ) -> pd.DataFrame:
        if index_type:
            index_type = index_type.lower()

        df = pd.read_csv(file, header=header_row - 1, **kwargs)
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
            index = generate_time_index(sample_rate, size=len(df))
            df.set_index(index, inplace=True)
        elif index_type and index_type != "number":
            time_units = index_type
            if index_type == "timestamp":
                time_units = None

            index = pd.to_timedelta(df.index, unit=time_units)
            index = index - index[0]
            df.set_index(index, inplace=True)
        if df.index.inferred_type == "timedelta64":
            df.index.rename("Time (s)", inplace=True)

        return df

    def parse(
        self,
        file: Path,
        x_axis_title="",
        y_axis_title="",
        **kwargs,
    ) -> ViewModel:
        df = self._parse_to_df(file=file, **kwargs)
        return ViewModel(df, y_axis=y_axis_title)
