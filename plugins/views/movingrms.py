import pandas as pd

from app.utils import classproperty
from app.plugins import dataframeplugins
from app.plugins.options import DataOption, NumericOption


class MovingRms(dataframeplugins.ViewPlugin):
    @classproperty
    def name(cls) -> str:
        return "Moving RMS"

    @property
    def x_title(self) -> str:
        return "Time (s)"

    @property
    def y_title(self) -> str:
        return "Acceleration (g)"

    @classproperty
    def options(cls) -> dict[str, DataOption]:
        return {
            "steps": NumericOption("Steps", 100, 1, None),
        }

    @classmethod
    def can_process(cls, df: pd.DataFrame) -> bool:
        return True

    def process(self, **kwargs) -> pd.DataFrame:
        df = self._df
        steps = kwargs.get("steps", 100)
        n = int(df.shape[0] / steps)
        return df.abs().rolling(n).std().iloc[::n]
