import endaq as ed
import pandas as pd

from app.plugins import dataframeplugins
from app.plugins.options import DataOption, NumericOption, ListOption, ListOptionPair
from app.utils import classproperty


class PSDPlugin(dataframeplugins.ViewPlugin):
    @classproperty
    def name(cls) -> str:
        return "PSD"

    @classproperty
    def add_to_toolbar(cls) -> bool:
        return True

    @property
    def x_title(self) -> str:
        return "Frequency (Hz)"

    @property
    def y_title(self) -> str:
        return "Amplitude"

    @classproperty
    def options(cls) -> dict[str, DataOption]:
        return {
            "bin_width": NumericOption("Bin Width", 1, 1, None),
            "scaling": ListOption(
                "Scaling",
                [
                    ListOptionPair("Density", "density"),
                    ListOptionPair("Spectrum", "spectrum"),
                    ListOptionPair("Parseval", "parseval"),
                ],
            ),
        }

    @classmethod
    def can_process(cls, df: pd.DataFrame) -> bool:
        return df.index.inferred_type == "timedelta64"

    def process(self, **kwargs) -> pd.DataFrame:
        return ed.endaq.calc.psd.welch(self._df, **kwargs)
