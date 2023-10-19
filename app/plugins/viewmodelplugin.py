from abc import ABC, abstractmethod

from yapsy.IPlugin import IPlugin

from PySide6.QtGui import QIcon

from app.views import ViewModel
from .options import DataOption


class ViewModelPlugin(IPlugin, ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def icon(self) -> QIcon | None:
        return None

    @property
    def add_to_toolbar(self) -> bool:
        return False

    @property
    def options(self) -> dict[str, DataOption]:
        return {}

    @abstractmethod
    def can_process(self, model: ViewModel) -> bool:
        pass

    @abstractmethod
    def process(self, model: ViewModel, **kwargs) -> ViewModel:
        pass


class FilterPlugin(ViewModelPlugin):
    pass


class ViewPlugin(ViewModelPlugin):
    @property
    def display_markers(self) -> bool:
        return False
