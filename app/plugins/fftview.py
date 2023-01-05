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
        # If the max frequency is less than the default max x value
        # update the max x value to the max frequency
        self.x_range = (0, min(self.x_range[1], fft.index.max()))
        return fft
