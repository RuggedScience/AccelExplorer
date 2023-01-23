import endaq as ed
import pandas as pd

from app.plugins import dataframeplugins
from app.plugins.options import DataOption, NumericOption, ListOption, ListOptionPair
from app.utils import classproperty, get_sample_frequency


class Bessel(dataframeplugins.FilterPlugin):
    @classproperty
    def name(cls) -> str:
        return "Bessel Filter"

    @classproperty
    def options(cls) -> dict[str, DataOption]:
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
            "norm": ListOption(
                "Normalization",
                [
                    ListOptionPair("Phase", "phase"),
                    ListOptionPair("Delay", "delay"),
                    ListOptionPair("Magnitude", "mag"),
                ],
            ),
        }

    @classmethod
    def can_process(cls, df: pd.DataFrame) -> bool:
        return df.index.inferred_type in ["timedelta64", "datetime64"]

    def process(self, **kwargs) -> pd.DataFrame:
        filter_type = kwargs.pop("type", "high_pass")
        cutoff = kwargs.pop("cutoff", 1)

        # Clamp the cutoff to the max allowed value if it's too high
        fs = get_sample_frequency(self._df)
        max_cutoff = (fs / 2) - 1
        cutoff = min(max_cutoff, cutoff)

        if filter_type == "high_pass":
            kwargs["low_cutoff"] = cutoff
        else:
            kwargs["high_cutoff"] = cutoff

        return ed.endaq.calc.filters.bessel(self._df, **kwargs)
