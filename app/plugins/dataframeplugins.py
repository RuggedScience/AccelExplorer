from abc import ABC, abstractmethod

import pandas as pd
from yapsy.IPlugin import IPlugin

from PySide6.QtGui import QIcon

from app.utils import classproperty
from .options import DataOption


class DataFramePlugin(IPlugin, ABC):
    def __init__(self):
        self._df = None
        super().__init__()

    @classproperty
    @abstractmethod
    def name(cls) -> str:
        pass

    @classproperty
    def icon(cls) -> str | QIcon:
        return None

    @classproperty
    def add_to_toolbar(cls) -> bool:
        return False

    @classproperty
    def options(cls) -> dict[str, DataOption]:
        return {}

    @classmethod
    @abstractmethod
    def can_process(cls, df: pd.DataFrame) -> bool:
        pass

    def set_df(self, df: pd.DataFrame):
        self._df = df

    @abstractmethod
    def process(self, **kwargs) -> pd.DataFrame:
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

    @classproperty
    def display_markers(self) -> bool:
        return False
