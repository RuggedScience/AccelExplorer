import pandas as pd
import endaq

from app.categories import DataView


class SRSView(DataView):
    name = "SRS"
    x_title = "Frequency"
    y_title = "Magnitude"

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        srs: pd.DataFrame = endaq.calc.shock.shock_spectrum(
            df, damp=0.05, init_freq=1, mode="srs"
        )
        # If the max frequency is less than the default max x value
        # update the max x value to the max frequency
        self.x_range = (0, min(self.x_range[1], srs.index.max()))
        return srs
