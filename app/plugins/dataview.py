from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict
    import pandas as pd
    from .option import DataOption


class DataView:
    # Name displayed in the drop down menu
    name = "Base Data View"
    # Titles for the x and y axes displayed on the chart
    x_title = ""
    y_title = ""

    def generate(self, df: "pd.DataFrame", **kwargs) -> "pd.DataFrame":
        return df

    @property
    def options(self) -> "Dict[str, DataOption]":
        return {}
