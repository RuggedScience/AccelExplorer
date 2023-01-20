import endaq as ed
import pandas as pd

from PySide6.QtGui import QIcon

from app.plugins import dataframeplugins
from app.plugins.options import DataOption, NumericOption


class FFTPlugin(dataframeplugins.ViewPlugin):
    @property
    def name(self) -> str:
        return "FFT"

    @property
    def icon(self) -> str | QIcon:
        return QIcon(":/icons/fft.png")

    @property
    def add_to_toolbar(self) -> bool:
        return True

    @property
    def x_title(self) -> str:
        return "Frequency (Hz)"

    @property
    def y_title(self) -> str:
        return "Magnitude"

    @property
    def options(self) -> dict[str, DataOption]:
        return {
            "min_freq": NumericOption("Min Freq", 10, 1, None),
            "max_freq": NumericOption("Max Freq", 1000, 1, None),
        }

    def can_process(self, df: pd.DataFrame) -> bool:
        return df.index.inferred_type == "timedelta64"

    def process(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)
        fft: pd.DataFrame = ed.calc.fft.fft(df)
        # Clamp to min / max values
        return fft[(fft.index >= min_x) & (fft.index <= max_x)]
