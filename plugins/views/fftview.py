from typing import Dict

import numpy as np
import pandas as pd
import endaq as ed


from app.plugins import dataframeplugins
from app.plugins.options import DataOption, NumericOption


class FFTView(dataframeplugins.ViewPlugin):
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
        }

    def can_process(self, df: pd.DataFrame) -> bool:
        return df.index.inferred_type in ["timedelta64", "datetime64"]

    def process(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)

        fft: pd.DataFrame = ed.calc.fft.fft(df)
        fft = fft[(fft.index >= min_x) & (fft.index <= max_x)]
        return fft
