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
