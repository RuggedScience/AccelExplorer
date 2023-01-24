from copy import deepcopy

import pandas as pd
from endaq.calc.utils import sample_spacing

from PySide6.QtCore import QObject, QPointF, Signal, QPointFList


class ViewModel(QObject):
    data_changed = Signal()
    series_added = Signal(str)
    series_removed = Signal(str)
    name_changed = Signal(str, str)

    def __init__(
        self,
        df: pd.DataFrame = pd.DataFrame(),
        y_axis: str = "",
        points: dict[str, QPointFList] = None,
        parent: QObject = None,
        lazy: bool = True
    ):
        super().__init__(parent)

        self._df = df.copy()
        self._y_axis = y_axis
        self._points = None

        if points is None:
            if not lazy:
                self._points = self.generate_points(df)
        else:
            self._points = points.copy()

    def __getitem__(self, key) -> "ViewModel":
        key = list(key)

        points = {}
        for name in key:
            if not isinstance(name, str):
                raise TypeError(f"Invalid key type. Expected string, got {type(name)}.")

            points[name] = self._points[name]

        return ViewModel(self._df[key], points)

    @property
    def df(self) -> pd.DataFrame:
        return self._df.copy()
    
    @property
    def x_axis(self) -> str:
        return self._df.index.name
    
    @property
    def y_axis(self) -> str:
        return self._y_axis
    
    @property
    def size(self) -> int:
        return self._df.size
    
    @property
    def index_type(self) -> str:
        return self._df.index.inferred_type

    @property
    def points(self) -> dict[str, QPointFList]:
        # Lazyily generate the points
        if self._points is None:
            self._points = self.generate_points(self._df)

        return self._points.copy()

    @property
    def empty(self) -> bool:
        return self._df.empty

    @property
    def sample_rate(self) -> float:
        if self._df.index.inferred_type == "timedelta64":
            return 1 / sample_spacing(self._df)

    def copy(self) -> "ViewModel":
        return ViewModel(df=self._df, y_axis=self._y_axis, points=self._points)

    def remove_series(self, name: str) -> None:
        assert name in self._df
        assert name in self._points

        self._df.drop(name, axis="columns", inplace=True)
        del self._points[name]

        self.series_removed.emit(name)
        self.data_changed.emit()

    def merge(self, other: "ViewModel") -> None:
        if not self.can_merge(other):
            raise ValueError("Cannot merge non matching models")
        
        new_cols = set(other._df.columns).difference(self._df)
        
        if self.empty:
            self._df = other._df
            self._points = other._points
            self._y_axis = other._y_axis
        else:
            for col in new_cols:
                self._df[col] = other._df[col].copy()
                self._points[col] = other._points[col]

            # df = pd.concat([self._df, other], axis="columns")
            self._df.sort_index(inplace=True)

        # Wait until we're done to emit the signals
        for col in new_cols:
            self.series_added.emit(col)
        self.data_changed.emit()

    def can_merge(self, other: "ViewModel") -> bool:
        if self.empty:
            return True

        if self._df.index.inferred_type != other._df.index.inferred_type:
            return False

        if other._df.index.inferred_type == "timedelta64":
            if sample_spacing(other._df) != sample_spacing(self._df):
                return False
        return True

    def add_suffix(self, suffix: str) -> None:
        columns = {col: col + suffix for col in self._df}
        self.rename(columns)

    def rename(self, columns: dict[str, str]) -> None:
        self._df.rename(columns=columns, inplace=True)
        for old, new in columns.items():
            self._points[new] = self._points.pop(old)
            self.name_changed.emit(old, new)

    @staticmethod
    def generate_points(df: pd.DataFrame) -> dict[str, QPointFList]:
        d = {}
        df = df.astype(float)
        for col, series in df.items():
            if series.index.inferred_type == "timedelta64":
                series.index = series.index.total_seconds()

            points = QPointFList()
            points.reserve(series.size)
            for i, v in series.items():
                points.append(QPointF(i, v))
            d[col] = points
        return d
