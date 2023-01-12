from typing import Dict, List

import endaq as ed
import pandas as pd

from app.plugins import dataframeplugins
from app.plugins.options import DataOption, NumericOption


class ButterworthFilter(dataframeplugins.FilterPlugin):
    @property
    def options(self) -> Dict[str, DataOption]:
        return {
            "low_cutoff": NumericOption("Low Cutoff", 1.0, 0, None),
            "high_cutoff": NumericOption("High Cutoff", 0.0, 0, None),
            "half_order": NumericOption("Half Order", 3, 0, None),
        }

    def can_process(self, df: pd.DataFrame) -> bool:
        return df.index.inferred_type in ["timedelta64", "datetime64"]

    def process(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        if kwargs.get("low_cutoff") == 0:
            kwargs.pop("low_cutoff")
        if kwargs.get("high_cutoff") == 0:
            kwargs.pop("high_cutoff")

        return ed.endaq.calc.filters.butterworth(df, **kwargs)
