import endaq as ed
import pandas as pd

from app.plugins import viewmodelplugin
from app.plugins.options import DataOption, NumericOption, ListOption, ListOptionPair
from app.views import ViewModel


class ButterworthFilter(viewmodelplugin.FilterPlugin):
    @property
    def name(self) -> str:
        return "Butterworth Filter"

    @property
    def options(self) -> dict[str, DataOption]:
        return {
            "type": ListOption(
                "Type",
                [
                    ListOptionPair("High Pass", "high_pass"),
                    ListOptionPair("Low Pass", "low_pass"),
                ],
            ),
            "cutoff": NumericOption("Cutoff (Hz)", 1, 1, None),
            "half_order": NumericOption("Half Order", 3, 0, None),
        }

    def can_process(self, model: ViewModel) -> bool:
        return model.index_type in ("timedelta64", "datetime64")

    def process(self, model: ViewModel, **kwargs) -> ViewModel:
        filter_type = kwargs.pop("type", "high_pass")
        cutoff = kwargs.pop("cutoff", 1)

        # Clamp the cutoff to the max allowed value if it's too high
        fs = model.sample_rate
        max_cutoff = (fs / 2) - 1
        cutoff = min(max_cutoff, cutoff)

        if filter_type == "high_pass":
            kwargs["low_cutoff"] = cutoff
        else:
            kwargs["high_cutoff"] = cutoff

        df = ed.endaq.calc.filters.butterworth(model.df, **kwargs)
        return ViewModel(df, y_axis=model.y_axis)
