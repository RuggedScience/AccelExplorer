import pandas as pd

from app.plugins import dataframeplugins
from app.plugins.options import DataOption, NumericOption


class MovingPeak(dataframeplugins.ViewPlugin):
    @property
    def name(self) -> str:
        return "Moving Peak"

    @property
    def x_title(self) -> str:
        return "Time (s)"

    @property
    def y_title(self) -> str:
        return "Acceleration (g)"

    @property
    def options(self) -> dict[str, DataOption]:
        return {
            "steps": NumericOption("Steps", 100, 1, None),
        }

    def can_process(self, df: pd.DataFrame) -> bool:
        return True

    def process(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        steps = kwargs.get("steps", 100)
        n = int(df.shape[0] / steps)
        return df.abs().rolling(n).max().iloc[::n]
