import endaq as ed
import pandas as pd

from PySide6.QtGui import QIcon

from app.plugins import dataframeplugins
from app.plugins.options import DataOption, NumericOption
from app.utils import classproperty


class SRSPlugin(dataframeplugins.ViewPlugin):
    @classproperty
    def name(cls) -> str:
        return "SRS"

    @classproperty
    def icon(cls) -> str | QIcon:
        return None
        # return QIcon(":/icons/srs.png")

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
    def display_markers(self) -> bool:
        return True

    @classproperty
    def options(cls) -> dict[str, DataOption]:
        return {
            "min_freq": NumericOption("Min Freq", 10, 1, None),
            "max_freq": NumericOption("Max Freq", 1000, 1, None),
            "dampening": NumericOption("Dampening", 5, 0, 100),
        }

    @classmethod
    def can_process(cls, df: pd.DataFrame) -> bool:
        return df.index.inferred_type == "timedelta64"

    def process(self, **kwargs) -> pd.DataFrame:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)
        dampening = kwargs.get("dampening", 5) / 100
        srs: pd.DataFrame = ed.calc.shock.shock_spectrum(
            self._df,
            damp=dampening,
            init_freq=min_x,
            mode="srs",
        )
        # Clamp to max value. init_freq parameter will handle min value.
        return srs[srs.index <= max_x]
