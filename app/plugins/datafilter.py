import pandas as pd

from . import dataplugin


class DataFilter(dataplugin.DataPlugin):
    def filter(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        return df
