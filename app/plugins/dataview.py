from typing import TYPE_CHECKING

from .dataplugin import DataPlugin

if TYPE_CHECKING:
    from typing import Dict
    import pandas as pd
    from .options import DataOption


class DataView(DataPlugin):
    # Name displayed in the drop down menu
    # name = "Base Data View"
    # Titles for the x and y axes displayed on the chart
    x_title = ""
    y_title = ""

    @property
    def options(self) -> "Dict[str, DataOption]":
        return {}

    def generate(self, df: "pd.DataFrame", **kwargs) -> "pd.DataFrame":
        return df