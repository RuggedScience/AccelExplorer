from abc import ABC, abstractmethod

import endaq as ed
import pandas as pd
from yapsy.IPlugin import IPlugin

from PySide6.QtGui import QIcon

from .options import DataOption, NumericOption


class DataFramePlugin(IPlugin, ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def icon(self) -> str | QIcon:
        return None

    @property
    def add_to_toolbar(self) -> bool:
        return False

    @property
    def options(self) -> dict[str, DataOption]:
        return {}

    @abstractmethod
    def can_process(self, df: pd.DataFrame) -> bool:
        pass

    @abstractmethod
    def process(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        pass


class FilterPlugin(DataFramePlugin):
    """Just used to organize filters and views"""

    pass


class ViewPlugin(DataFramePlugin):
    @property
    @abstractmethod
    def x_title(self) -> str:
        pass

    @property
    @abstractmethod
    def y_title(self) -> str:
        pass

    @property
    def display_markers(self) -> bool:
        return False


class FFTPlugin(ViewPlugin):
    @property
    def name(self) -> str:
        return "FFT"

    @property
    def icon(self) -> str | QIcon:
        return QIcon(":/icons/fft.png")

    @property
    def add_to_toolbar(self) -> bool:
        return True

    @property
    def x_title(self) -> str:
        return "Frequency (Hz)"

    @property
    def y_title(self) -> str:
        return "Magnitude"

    @property
    def options(self) -> dict[str, DataOption]:
        return {
            "min_freq": NumericOption("Min Freq", 10, 1, None),
            "max_freq": NumericOption("Max Freq", 1000, 1, None),
        }

    def can_process(self, df: pd.DataFrame) -> bool:
        return df.index.inferred_type == "timedelta64"

    def process(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)
        fft: pd.DataFrame = ed.calc.fft.fft(df)
        # Clamp to min / max values
        return fft[(fft.index >= min_x) & (df.index <= max_x)]


class SRSPlugin(ViewPlugin):
    @property
    def name(self) -> str:
        return "SRS"

    @property
    def icon(self) -> str | QIcon:
        return QIcon(":/icons/srs.png")

    @property
    def add_to_toolbar(self) -> bool:
        return True

    @property
    def x_title(self) -> str:
        return "Frequency (Hz)"

    @property
    def y_title(self) -> str:
        return "Magnitude"

    @property
    def display_markers(self) -> bool:
        return True

    @property
    def options(self) -> dict[str, DataOption]:
        return {
            "min_freq": NumericOption("Min Freq", 10, 1, None),
            "max_freq": NumericOption("Max Freq", 1000, 1, None),
            "dampening": NumericOption("Dampening", 5, 0, 100),
        }

    def can_process(self, df: pd.DataFrame) -> bool:
        return df.index.inferred_type == "timedelta64"

    def process(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)
        dampening = kwargs.get("dampening", 5) / 100
        srs: pd.DataFrame = ed.calc.shock.shock_spectrum(
            df,
            damp=dampening,
            init_freq=min_x,
            mode="srs",
        )
        # Clamp to max value. init_freq parameter will handle min value.
        return srs[srs.index <= max_x]
