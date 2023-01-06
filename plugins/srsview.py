from typing import Dict

import pandas as pd
import endaq

from app.plugins import dataview
from app.plugins.options import DataOption, NumericOption


class SRSView(dataview.DataView):
    name = "SRS"
    x_title = "Frequency"
    y_title = "Magnitude"

    def generate(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)
        dampening = kwargs.get("dampening", 5) / 100
        srs: pd.DataFrame = endaq.calc.shock.shock_spectrum(
            df, damp=dampening, init_freq=min_x, mode="srs"
        )

        return srs[srs.index <= max_x]

    @property
    def options(self) -> Dict[str, DataOption]:
        return {
            "min_freq": NumericOption("Min Frequency", 10, 1, None),
            "max_freq": NumericOption("Max Frequency", 1000, 1, None),
            "dampening": NumericOption("Dampening", 5, 0, 100),
        }
