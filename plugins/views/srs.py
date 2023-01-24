import endaq as ed
import pandas as pd

from PySide6.QtGui import QIcon

from app.plugins import viewmodelplugin
from app.plugins.options import DataOption, NumericOption
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
        }

    def can_process(self, model: ViewModel) -> bool:
        return model.index_type in ("timedelta64", )

    def process(self, model: ViewModel, **kwargs) -> ViewModel:
        min_x = kwargs.get("min_freq", 10)
        max_x = kwargs.get("max_freq", 1000)
        dampening = kwargs.get("dampening", 5) / 100
        srs = ed.endaq.calc.shock.shock_spectrum(
            model.df,
            damp=dampening,
            init_freq=min_x,
            mode="srs",
        )
        # Clamp to max value. init_freq parameter will handle min value.
        srs = srs[srs.index <= max_x]
        return ViewModel(srs, y_axis="Peak Acceleration (g)")
