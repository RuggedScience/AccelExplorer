import pandas as pd

from .dataplugin import DataPlugin


class DataFilter(DataPlugin):
    def filter(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        return df
