import pandas as pd
import endaq

from app.categories import DataView

class SRSView(DataView):
    name = "SRS"

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        freqs = endaq.calc.utils.logfreqs(df, init_freq=1, bins_per_octave=12)
        srs = endaq.calc.shock.shock_spectrum(df, freqs=freqs, damp=0.05, mode='srs')
        return srs
            
            