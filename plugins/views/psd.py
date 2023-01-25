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
            "min_freq": NumericOption("Min Freq", 10, 1, None),
            "max_freq": NumericOption("Max Freq", 1000, 1, None),
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
        return model.index_type in ("timedelta64",)

    def process(self, model: ViewModel, **kwargs) -> ViewModel:
        min_x = kwargs.pop("min_freq", 10)
        max_x = kwargs.pop("max_freq", 1000)

        df = model.df.dropna(how="any")
        psd = ed.endaq.calc.psd.welch(df, **kwargs)
        psd = psd[(psd.index >= min_x) & (psd.index <= max_x)]
        y_axis = model.y_axis

        # PSD results in the same y-axis units but squared per Hz.
        # Find the closing parentheses that contains the unit and add "^2/Hz" to it.
        # Example: "Acceleration (g)" becomes "Acceleration (g^2/Hz)""
        index = y_axis.rfind(")")
        if index > 0:
            y_axis = f"{y_axis[:index]}^2/Hz)"

        return ViewModel(psd, y_axis=y_axis)
