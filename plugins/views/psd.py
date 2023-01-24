import endaq as ed
import pandas as pd

from app.plugins import viewmodelplugin
from app.plugins.options import DataOption, NumericOption, ListOption, ListOptionPair
from app.views import ViewModel


class PSDPlugin(viewmodelplugin.ViewPlugin):
    @property
    def name(self) -> str:
        return "PSD"

    @property
    def add_to_toolbar(self) -> bool:
        return True

    @property
    def options(self) -> dict[str, DataOption]:
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

    def can_process(self, model: ViewModel) -> bool:
        return model.index_type in ("timedelta64", )

    def process(self, model: ViewModel, **kwargs) -> ViewModel:
        df = ed.endaq.calc.psd.welch(model.df, **kwargs)
        y_axis = model.y_axis
        index = y_axis.rfind(")")
        if index > 0:
            y_axis = f"{y_axis[:index]}**2/Hz)"
        return ViewModel(df, y_axis=y_axis)
