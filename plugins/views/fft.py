import endaq as ed
import pandas as pd

from app.plugins import viewmodelplugin
from app.plugins.options import DataOption, NumericOption
from app.views import ViewModel


class FFTPlugin(viewmodelplugin.ViewPlugin):
    @property
    def name(self) -> str:
        return "FFT"

    @property
    def add_to_toolbar(self) -> bool:
        return True

    @property
    def options(self) -> dict[str, DataOption]:
        return {
            "min_freq": NumericOption("Min Freq", 10, 1, None),
            "max_freq": NumericOption("Max Freq", 1000, 1, None),
        }

    def can_process(self, model: ViewModel) -> bool:
        return model.index_type in ("timedelta64",)

    def process(self, model: ViewModel, **kwargs) -> ViewModel:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)

        df = model.df.dropna(how="any")
        fft = ed.endaq.calc.fft.fft(df)
        # Clamp to min / max values
        fft = fft[(fft.index >= min_x) & (fft.index <= max_x)]
        return ViewModel(fft, y_axis="Magnitude")
