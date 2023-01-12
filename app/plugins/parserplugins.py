import linecache
import os
from abc import ABC, abstractmethod
from typing import Dict, List

import pandas as pd
from yapsy.IPlugin import IPlugin

from .options import DataOption, ListOption, ListOptionPair, NumericOption


class ParseError(Exception):
    pass


class ParserPlugin(IPlugin, ABC):
    def __init__(self):
        super().__init__()

    @staticmethod
    @abstractmethod
    def supported_extensions() -> List[str]:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
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

    @property
    def display_name(self) -> str:
        return "CSV Parser"

    @property
    def header_row(self) -> int:
        return None

    @property
    def options(self) -> Dict[str, DataOption]:
        return {}

    def get_headers(self, filename: str, line: int, **kwargs) -> List[str]:
        return linecache.getline(filename, lineno=line).strip().split(",")

    def can_parse(self, filename: str) -> bool:
        return os.path.exists(filename)

    def parse(self, filename: str, **kwargs) -> pd.DataFrame:
        header_row = kwargs.pop("header_row", self.header_row) or 1

        df = pd.read_csv(filename, header=header_row - 1, **kwargs)
        df.dropna(axis="columns", inplace=True)
        if df.isna().values.any():
            raise ValueError()

        for col in df:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise ValueError()

        return df


class AccelCSVParser(CSVParser):
    @property
    def display_name(self) -> str:
        return "Accel Parser"

    @property
    def options(self) -> Dict[str, DataOption]:
        return {
            "time_units": ListOption(
                "Time Measurement",
                [
                    ListOptionPair("None", None),
                    ListOptionPair("Timestamp", "timestamp"),
                    ListOptionPair("Seconds", "s"),
                    ListOptionPair("Milliseconds", "ms"),
                    ListOptionPair("Microseconds", "us"),
                    ListOptionPair("Nanoseconds", "ns"),
                ],
            ),
            "sample_rate": NumericOption("Sample Rate(hz)", 1000, 1, None),
        }

    def get_headers(self, filename: str, line: int, **kwargs) -> List[str]:
        headers = super().get_headers(filename, line, **kwargs)

        if not headers:
            return headers

        time_units = kwargs.pop("time_units", None)
        if time_units is not None:
            headers.pop(0)

        return headers

    def parse(self, filename: str, **kwargs) -> pd.DataFrame:
        time_units = kwargs.pop("time_units", None)
        sample_rate = kwargs.pop("sample_rate", None)

        if time_units:
            usecols = kwargs.pop("usecols", None)
            if usecols:
                line = kwargs.get("header_row", 1)
                headers = self.get_headers(filename, line)
                usecols.append(headers[0])
                kwargs["usecols"] = usecols

        df = super().parse(filename, **kwargs)

        if not time_units and not sample_rate:
            raise ParseError(
                "Sample rate or time measurment for the first column required"
            )

        if time_units:
            # Assume time is the first column
            time_axis = df.iloc(axis=1)[0].name
            if time_units == "timestamp":
                df[time_axis] = pd.to_timedelta(df[time_axis])
            else:
                start_time = df[time_axis][0]
                if start_time != 0:
                    df[time_axis] = df[time_axis].apply(
                        lambda x: x - start_time)
                df[time_axis] = pd.to_timedelta(df[time_axis], unit=time_units)

            df.set_index(time_axis, drop=True, inplace=True)
        elif sample_rate:
            spacing = 1 / sample_rate
            df.set_index(
                pd.to_timedelta(
                    [spacing * i for i in range(len(df))], unit="S"),
                inplace=True,
            )

        df.index.rename("Time (s)", inplace=True)
        return df
