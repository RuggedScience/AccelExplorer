from typing import Dict

import pandas as pd


class ParseError(Exception):
    pass


class CSVParser:
    name = "Generic CSV Parser"

    extension = 'csv'

    header_row = None
    sample_rate = None
    time_units = None

    def _process_df(self, df: pd.DataFrame) -> pd.DataFrame:
        # Cleanup column names. Fixes issues with DataFrame.itertuples.
        df.columns = df.columns.str.replace(r'''[:,',",\s]+''', '_', regex=True)

        if self.time_units:
            # Assume time is the first column
            time_axis = df.iloc(axis=1)[0].name
            if self.time_units == 'timestamp':
                df[time_axis] = pd.to_timedelta(df[time_axis])
            else:
                start_time = df[time_axis][0]
                if start_time != 0:
                    df[time_axis] = df[time_axis].apply(lambda x: x - start_time)
                df[time_axis] = pd.to_timedelta(df[time_axis], unit=self.time_units)

            df.set_index(time_axis, drop=True, inplace=True)
        elif self.sample_rate:
            spacing = 1 / self.sample_rate
            df.set_index(
                pd.to_timedelta([spacing * i for i in range(len(df))], unit="S"),
                inplace=True,
            )

        df.index.rename('Time (s)', inplace=True)
        return df

    def parse(self, filename: str, **kwargs) -> pd.DataFrame:
        if self.header_row is None:
            self.header_row = 1

        df = pd.read_csv(filename, header=self.header_row - 1)
        return self._process_df(df)


class DataFilter:
    name = "Base Data Filter"

    def get_options(self, df: pd.DataFrame) -> Dict[str, float]:
        return {}

    def filter(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        return df

class DataView:
    name = "Base Data View"
    y_title = "Acceleration (g's)"

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        return df