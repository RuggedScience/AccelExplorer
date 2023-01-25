import endaq as ed
import pandas as pd

from PySide6.QtGui import QIcon

from app.plugins import viewmodelplugin
from app.plugins.options import DataOption, NumericOption, ListOption, ListOptionPair
from app.views import ViewModel


class SRSPlugin(viewmodelplugin.ViewPlugin):
    @property
    def name(self) -> str:
        return "SRS"

    @property
    def add_to_toolbar(self) -> bool:
        return True

    @property
    def display_markers(self) -> bool:
        return True

    @property
    def options(self) -> dict[str, DataOption]:
        return {
            "min_freq": NumericOption("Min Freq", 10, 1, None),
            "max_freq": NumericOption("Max Freq", 1000, 1, None),
            "dampening": NumericOption("Dampening", 5, 0, 100),
            "mode": ListOption(
                "Mode", [ListOptionPair("SRS", "srs"), ListOptionPair("PVSS", "pvss")]
            ),
        }

    def can_process(self, model: ViewModel) -> bool:
        return model.index_type in ("timedelta64",)

    def process(self, model: ViewModel, **kwargs) -> ViewModel:
        min_x = kwargs.pop("min_freq", 10)
        max_x = kwargs.pop("max_freq", 1000)
        dampening = kwargs.pop("dampening", 5) / 100
        df = model.df.dropna(how="any")
        srs = ed.endaq.calc.shock.shock_spectrum(
            df,
            damp=dampening,
            init_freq=min_x,
            **kwargs,
        )
        # Clamp to max value. init_freq parameter will handle min value.
        srs = srs[srs.index <= max_x]
        return ViewModel(srs, y_axis="Peak Acceleration (g)")
