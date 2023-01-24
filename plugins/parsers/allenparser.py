__all__ = ["AllenCSVParser"]

import linecache

from app.plugins import parserplugins
from app.views import ViewModel


class AllenCSVParser(parserplugins.CSVParser):
    def can_parse(self, filename: str) -> bool:
        try:
            self._get_sample_rate(filename)
        except:
            return False
        return True

    def parse(self, filename: str) -> ViewModel:
        sample_rate = self._get_sample_rate(filename)
        df = self._parse_to_df(filename=filename, sample_rate=sample_rate, header_row=29)
        # We only care about the second column which contains voltage
        df = df.iloc(axis="columns")[1].to_frame()

        col_name = df.columns[0]
        df[col_name] = df[col_name].apply(lambda x: (6.6 - x) * 200)
        df.rename(columns={col_name: "Acceleration"}, inplace=True)
        return ViewModel(df, "Acceleration (g)")

    def _get_sample_rate(self, filename: str) -> int:
        sample_rate_row = linecache.getline(filename=filename, lineno=22).lower()
        if sample_rate_row.startswith("sampling period"):
            value = sample_rate_row.split(",")[1]
            try:
                return int(1 / float(value))
            except:
                pass

        raise parserplugins.ParseError("Could not find sample rate")
