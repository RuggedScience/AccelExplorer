__all__ = ["EndaqParser"]

import endaq as ed

from app.plugins import parserplugins
from app.views import ViewModel


class EndaqParser(parserplugins.ParserPlugin):
    @staticmethod
    def supported_extensions() -> tuple[str]:
        return ("ide",)

    def parse(self, filename: str, **kwargs) -> ViewModel:
        df = ed.endaq.ide.get_primary_sensor_data(
            name=filename, measurement_type=ed.ide.ACCELERATION
        )
        # Convert index from datetime to timedelta
        series = df.index.to_series()
        df.index = series - series[0]
        return ViewModel(df, y_axis="Acceleration (g)")
