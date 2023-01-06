__all__ = ["AllenCSVParser"]

import linecache

import pandas as pd

from app.plugins import parsers


class AllenCSVParser(parsers.CSVParser):
    name = "Allen"
    header_row = 29
    sample_rate = 0

    def _get_sample_rate(self, filename: str) -> int:
        sample_rate_row = linecache.getline(filename=filename, lineno=22).lower()
        if sample_rate_row.startswith("sampling period"):
            value = sample_rate_row.split(",")[1]
            try:
                return int(1 / float(value))
            except:
                pass

        raise parsers.ParseError("Could not find sample rate")

    def can_parse(self, filename: str) -> bool:
        try:
            self._get_sample_rate(filename)
        except:
            return False
        return True

    def parse(self, filename: str) -> pd.DataFrame:
        self.sample_rate = self._get_sample_rate(filename)
        df = pd.read_csv(filename, header=self.header_row - 1)
        df.columns.values[0] = "Time"
        df.columns.values[1] = "Voltage"
        df = df[["Voltage"]]
        df["g_s"] = df["Voltage"].apply(lambda x: (6.6 - x) * 200)
        df.drop("Voltage", axis=1, inplace=True)
        return self._process_df(df)
