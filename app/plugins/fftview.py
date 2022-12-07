import pandas as pd
import numpy as np
from scipy.fft import fft, fftfreq
from endaq.calc.utils import sample_spacing


from app.categories import DataView


class FFTView(DataView):
    name = "FFT"

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        N = len(df)
        spacing = sample_spacing(df)

        freq = fftfreq(N, spacing)[: N // 2]

        df_fft = pd.DataFrame()
        for name in df.columns:
            yf = fft(df[name].values)
            y_plot = 2.0 / N * np.abs(yf[0 : N // 2])

            df_fft = pd.concat(
                [
                    df_fft,
                    pd.DataFrame(
                        {"Frequency (Hz)": freq[1:], name: y_plot[1:]}
                    ).set_index("Frequency (Hz)"),
                ],
                axis=1,
            )

        return df_fft
