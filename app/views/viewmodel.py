import pandas as pd
from endaq.calc.utils import sample_spacing

from PySide6.QtCore import QObject, QPointF, Signal


class ViewModel(QObject):
    data_changed = Signal()

    def __init__(
        self,
        df: pd.DataFrame = pd.DataFrame(),
        points: dict[str, list[QPointF]] = None,
        parent: QObject = None,
    ):
        super().__init__(parent)

        self._df = df.copy()

        if points is None:
            self._points = self.generate_points(df)
        else:
            self._points = points.copy()

    @property
    def df(self) -> pd.DataFrame:
        return self._df.copy()

    @df.setter
    def df(self, df: pd.DataFrame) -> None:
        self._df = df.copy()
        self._points = self.generate_points(df)
        self.data_changed.emit()

    @property
    def points(self) -> dict[str, list[QPointF]]:
        return self._points.copy()

    @property
    def empty(self) -> bool:
        return self._df.empty

    @property
    def sample_rate(self) -> float:
        if self._df.index.inferred_type == "timedelta64":
            return 1 / sample_spacing(self._df)

    def copy(self) -> "ViewModel":
        return ViewModel(self._df, self._points)

    def merge(self, other: pd.DataFrame) -> None:
        if isinstance(other, ViewModel):
            other = other.df

        df = pd.concat([self._df, other], axis="columns")
        df.sort_index(inplace=True)
        self.df = df

    def can_merge(self, df: pd.DataFrame) -> bool:
        if self._df.index.inferred_type != df.index.inferred_type:
            return False

        if df.index.inferred_type == "timedelta64":
            if sample_spacing(df) != sample_spacing(self._df):
                return False
        return True

    def rename(self, old: str, new: str) -> None:
        assert old in self._df
        assert old in self._points

        self._df.rename(columns={old: new}, inplace=True)
        self._points[new] = self._points.pop(old)

    @staticmethod
    def generate_points(df: pd.DataFrame) -> dict[str, list[QPointF]]:
        d = {}
        for col, series in df.items():
            if series.index.inferred_type == "timedelta64":
                series = series.copy()
                series.index = series.index.total_seconds()

            d[col] = [QPointF(float(i), float(v)) for i, v in series.items()]
        return d
