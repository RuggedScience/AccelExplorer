from typing import Dict

import pandas as pd
import endaq as ed


from app.plugins import dataview
from app.plugins.options import DataOption, NumericOption


class FFTView(dataview.DataView):
    name = "FFT"
    x_title = "Frequency"
    y_title = "Magnitude"

    def generate(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)

        fft: pd.DataFrame = ed.calc.fft.fft(df)
        return fft[(fft.index >= min_x) & (fft.index <= max_x)]

    @property
    def options(self) -> Dict[str, DataOption]:
        return {
            "min_freq": NumericOption("Min Frequency", 10, 1, None),
            "max_freq": NumericOption("Max Frequency", 1000, 1, None),
        }
