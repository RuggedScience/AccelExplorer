import pandas as pd
import endaq as ed


from app.categories import DataView


class FFTView(DataView):
    name = "FFT"
    x_title = "Frequency"
    y_title = "Magnitude"

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        fft: pd.DataFrame = ed.calc.fft.fft(df)
        # Remove all negative frequencies since it's a mirror
        fft = fft[fft.index >= 1]
        return fft
