import csv
import re

import pandas as pd

from app.categories import CSVParser, ParseError

class AllenCSVParser(CSVParser):
    name = 'Allen'
    header_row = 29
    sample_rate = 0

    def parse(self, filename: str, **kwargs) -> pd.DataFrame:
        with open(filename, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                name = row[0]
                value = row[1]
                if re.search('sampling period', name, re.IGNORECASE):
                    self.sample_rate = int(1 / float(value))
                    break

        if self.sample_rate == 0:
            raise ParseError('Could not find sample rate')

        df = super().parse(filename, **kwargs)
        df.columns.values[0] = "Time"
        df.columns.values[1] = "Voltage"
        df = df[['Time', 'Voltage']]
        df["g_s"] = df['Voltage'].apply(lambda x: (6.6 - x) * 200)
        df.drop('Voltage', axis=1, inplace=True)
        return df