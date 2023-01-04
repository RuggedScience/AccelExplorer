import pandas as pd
import endaq

from app.categories import DataView


class SRSView(DataView):
    name = "SRS"
    x_title = "Frequency"
    y_title = "Magnitude"

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        srs = endaq.calc.shock.shock_spectrum(df, damp=0.05, init_freq=1, mode="srs")
        return srs
