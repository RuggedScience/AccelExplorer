from typing import Dict

import pandas as pd


class DataFilter:
    name = "Base Data Filter"

    def filter(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        return df
