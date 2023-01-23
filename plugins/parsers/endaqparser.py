__all__ = ["EndaqParser"]
import os

import endaq as ed
import pandas as pd

from app.plugins import parserplugins


class EndaqParser(parserplugins.ParserPlugin):
    @staticmethod
    def supported_extensions() -> tuple[str]:
        return ("ide",)

    def parse(self, filename: str, **kwargs) -> pd.DataFrame:
        df = ed.endaq.ide.get_primary_sensor_data(
            name=filename, measurement_type=ed.ide.ACCELERATION
        )
        # Convert index from datetime to timedelta
        series = df.index.to_series()
        df.index = series - series[0]
        return df
