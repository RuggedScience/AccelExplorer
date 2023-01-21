import endaq as ed
import pandas as pd

from PySide6.QtGui import QIcon

from app.utils import classproperty
from app.plugins import dataframeplugins
from app.plugins.options import DataOption, NumericOption


class FFTPlugin(dataframeplugins.ViewPlugin):
    @classproperty
    def name(cls) -> str:
        return "FFT"

    @classproperty
    def icon(cls) -> str | QIcon:
        return None
        # return QIcon(":/icons/fft.png")

    @classproperty
    def add_to_toolbar(cls) -> bool:
        return True

    @property
    def x_title(self) -> str:
        return "Frequency (Hz)"

    @property
    def y_title(self) -> str:
        return "Magnitude"

    @classproperty
    def options(cls) -> dict[str, DataOption]:
        return {
            "min_freq": NumericOption("Min Freq", 10, 1, None),
            "max_freq": NumericOption("Max Freq", 1000, 1, None),
        }

    @classmethod
    def can_process(cls, df: pd.DataFrame) -> bool:
        return df.index.inferred_type == "timedelta64"

    def process(self, **kwargs) -> pd.DataFrame:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)
        fft: pd.DataFrame = ed.endaq.calc.fft.fft(self._df)
        # Clamp to min / max values
        return fft[(fft.index >= min_x) & (fft.index <= max_x)]
