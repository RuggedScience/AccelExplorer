from abc import ABC, abstractmethod
from typing import Dict

import pandas as pd
from yapsy.IPlugin import IPlugin

from .options import DataOption


class DataFramePlugin(IPlugin, ABC):
    @property
    def options(self) -> Dict[str, DataOption]:
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
