import pandas as pd
from endaq.calc.utils import sample_spacing

from PySide6.QtCore import QObject, QPointF, Signal, QPointFList


class ViewModel(QObject):
    data_changed = Signal()
    series_added = Signal(str)
    series_removed = Signal(str)
    name_changed = Signal(str, str)
    sample_rate_changed = Signal(float)

    def __init__(
        self,
        df: pd.DataFrame = pd.DataFrame(),
        y_axis: str = "",
        x_axis: str = None,
        points: dict[str, QPointFList] = None,
        parent: QObject = None,
        lazy: bool = True,
    ):
        super().__init__(parent)

        self._df = df.copy()
        self._y_axis = y_axis
        self._x_axis = x_axis
        self._points: dict[str, QPointFList] = {}

        self._sample_rate = None
        if not df.empty and df.index.inferred_type == "timedelta64":
            self._sample_rate = 1 / sample_spacing(df)

        if points is None:
            if not lazy:
                self._points = self._df_to_points(df)
        else:
            self._points = points.copy()

    def __getitem__(self, key) -> "ViewModel":
        key = list(key)

        points = {}
        for name in key:
            if not isinstance(name, str):
                raise TypeError(f"Invalid key type. Expected string, got {type(name)}.")

            if name in self._points:
                points[name] = self._points[name]

        return ViewModel(self._df[key], points)

    @property
    def df(self) -> pd.DataFrame:
        return self._df.copy()

    @property
    def x_axis(self) -> str:
        if self._x_axis is not None:
            return self._x_axis
        return self._df.index.name

    @property
    def y_axis(self) -> str:
        return self._y_axis

    @property
    def size(self) -> int:
        return self._df.size

    @property
    def shape(self) -> tuple[int, int]:
        return self._df.shape

    @property
    def index_type(self) -> str:
        return self._df.index.inferred_type

    @property
    def points(self) -> dict[str, QPointFList]:
        # Lazyily generate the points
        for col, series in self._df.items():
            if col not in self._points:
                self._points[col] = self._series_to_points(series)

        return self._points.copy()

    @property
    def empty(self) -> bool:
        return self._df.empty

    @property
    def sample_rate(self) -> float:
        return self._sample_rate

    def copy(self) -> "ViewModel":
        return ViewModel(df=self._df, y_axis=self._y_axis, points=self._points)

    def remove_series(self, name: str) -> None:
        assert name in self._df
        assert name in self._points

        self._df.drop(name, axis="columns", inplace=True)
        if name in self._points:
            del self._points[name]

        self.series_removed.emit(name)
        self.data_changed.emit()

    def merge(self, other: "ViewModel") -> None:
        if not self.can_merge(other):
            raise ValueError("Cannot merge non matching models")

        new_cols = set(other._df.columns).difference(self._df.columns)

        # If this is an empty model just copy other into this one.
        if self.empty:
            self._df = other._df
            self._points = other._points
            self._y_axis = other._y_axis
        else:
            # We only want to add new columns.
            # merge does not support adding data to already existing columns.
            new_df = other._df[list(new_cols)]
            self._df = pd.concat([self._df, new_df], axis="columns")
            self._df.sort_index(inplace=True)
            # Use linear interpolation to fill in missing data.
            # Happens if files don't have the same sample rate.
            self._df.interpolate(inplace=True)

            for col in new_cols:
                # Use points from other if they have been generated
                if col in other._points:
                    self._points[col] = other._points[col]

        # Wait until we're done to emit the signals
        for col in new_cols:
            self.series_added.emit(col)

        sample_rate = 1 / sample_spacing(self._df)
        if sample_rate != self._sample_rate:
            self._sample_rate = sample_rate
            self.sample_rate_changed.emit(sample_rate)

        self.data_changed.emit()

    def can_merge(self, other: "ViewModel") -> bool:
        if self.empty:
            return True

        return self._df.index.inferred_type == other._df.index.inferred_type

    def add_suffix(self, suffix: str) -> None:
        columns = {col: col + suffix for col in self._df}
        self.rename(columns)

    def rename(self, columns: dict[str, str]) -> None:
        self._df.rename(columns=columns, inplace=True)
        for old, new in columns.items():
            if old in self._points:
                self._points[new] = self._points.pop(old)

            self.name_changed.emit(old, new)

    def _series_to_points(self, series: pd.Series) -> QPointFList:
        if series.index.inferred_type == "timedelta64":
            series.index = series.index.total_seconds()

        points = QPointFList()
        points.reserve(series.size)
        for i, v in series.items():
            points.append(QPointF(i, v))
        return points

    def _df_to_points(self, df: pd.DataFrame) -> dict[str, QPointFList]:
        d = {}
        df = df.astype(float)
        for col, series in df.items():
            d[col] = self._series_to_points(series)
        return d
