from typing import Dict
from abc import ABC, abstractmethod

from .options import DataOption


class DataPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def options(self) -> "Dict[str, DataOption]":
        return {}
