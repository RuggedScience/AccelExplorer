from typing import Dict, List
from abc import ABC, abstractmethod

from .options import DataOption


class DataPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def options(self) -> Dict[str, DataOption]:
        return {}

    @property
    def index_types(self) -> List[str]:
        return None
