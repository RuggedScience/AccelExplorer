from typing import Dict, List

import pandas as pd
import endaq

from app.plugins import dataframeplugins
from app.plugins.options import DataOption, NumericOption


class SRSView(dataframeplugins.ViewPlugin):
    @property
    def x_title(self) -> str:
        return "Frequency"

    @property
    def y_title(self) -> str:
        return "Magnitude"

    @property
    def options(self) -> Dict[str, DataOption]:
        return {
            "min_freq": NumericOption("Min Frequency", 10, 1, None),
            "max_freq": NumericOption("Max Frequency", 1000, 1, None),
            "dampening": NumericOption("Dampening", 5, 0, 100),
        }

    def can_process(self, df: pd.DataFrame) -> bool:
        return df.index.inferred_type in ["timedelta64", "datetime64"]

    def process(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)
        dampening = kwargs.get("dampening", 5) / 100
        srs: pd.DataFrame = endaq.calc.shock.shock_spectrum(
            df, damp=dampening, init_freq=min_x, mode="srs"
        )

        return srs[srs.index <= max_x]
