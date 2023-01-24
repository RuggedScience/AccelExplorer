import pandas as pd

from app.plugins import viewmodelplugin
from app.plugins.options import DataOption, NumericOption
from app.views import ViewModel


class MovingRms(viewmodelplugin.ViewPlugin):
    @property
    def name(self) -> str:
        return "Moving RMS"

    @property
    def options(self) -> dict[str, DataOption]:
        return {
            "steps": NumericOption("Steps", 100, 1, None),
        }

    def can_process(self, model: ViewModel) -> bool:
        return model is not None

    def process(self, model: ViewModel, **kwargs) -> ViewModel:
        df = model.df
        steps = kwargs.get("steps", 100)
        n = int(df.shape[0] / steps)
        df = df.abs().rolling(n).std().iloc[::n]
        return ViewModel(df, y_axis=model.y_axis)
