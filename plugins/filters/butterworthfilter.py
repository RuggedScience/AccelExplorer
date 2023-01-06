from typing import Dict

import endaq as ed
import pandas as pd

from app.plugins import datafilter
from app.plugins.options import DataOption, NumericOption


class ButterworthFilter(datafilter.DataFilter):
    @property
    def name(self) -> str:
        return "Butterworth"

    @property
    def options(self) -> Dict[str, DataOption]:
        return {
            "low_cutoff": NumericOption("Low Cutoff", 1.0, 0, None),
            "high_cutoff": NumericOption("High Cutoff", 0.0, 0, None),
            "half_order": NumericOption("Half Order", 3, 0, None),
        }

    def filter(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        if kwargs.get("low_cutoff") == 0:
            kwargs.pop("low_cutoff")
        if kwargs.get("high_cutoff") == 0:
            kwargs.pop("high_cutoff")

        return ed.endaq.calc.filters.butterworth(df, **kwargs)
