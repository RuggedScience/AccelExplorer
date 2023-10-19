from __future__ import annotations

import pandas as pd
from endaq.calc.utils import sample_spacing
from PySide6.QtCore import QObject, QPointF, QPointFList, Signal

from app.utils import generate_time_index


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
        x_axis: str | None = None,
        points: dict[str, QPointFList] | None = None,
        parent: QObject | None = None,
        lazy: bool = True,
    ):
        super().__init__(parent)

        self.data_changed.connect(self._update_sample_rate)

        self._df = df.copy()
        self._y_axis = y_axis
        self._x_axis = x_axis
        self._points: dict[str, QPointFList] = {}
        self._sample_rate: int = 0

        self._update_sample_rate()

        if points is None:
            if not lazy:
                self._points = self._df_to_points(df)
        else:
            self._points = points.copy()

    def __getitem__(self, key: str | list[str]) -> "ViewModel":
        key = list(key)

        points = {}
        for name in key:
            if not isinstance(name, str):
                raise TypeError(f"Invalid key type. Expected string, got {type(name)}.")

            if name in self._points:
                points[name] = self._points[name]

        return ViewModel(self._df[key], points=points)

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
                self._points[str(col)] = self._series_to_points(series)

        return self._points.copy()

    @property
    def empty(self) -> bool:
        return self._df.empty

    @property
    def sample_rate(self) -> int:
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

    def difference(self, other: ViewModel | None) -> list[str]:
        if other is None:
            return list(self._df.columns)
        return list(set(self._df.columns).difference(other._df.columns))

    def merge(self, other: ViewModel) -> None:
        if not self.can_merge(other):
            raise ValueError("Cannot merge non matching models")

        new_cols = other.difference(self)

        # If this is an empty model just copy other into this one.
        if self.empty:
            self._df = other._df
            self._points = other._points
            self._y_axis = other._y_axis
        else:
            # We only want to add new columns.
            # merge does not support adding data to already existing columns.
            new_df = other._df[new_cols]

            # TODO: What happens if the sample rate is empty on either model?
            if other.sample_rate != self.sample_rate:
                end = new_df.index[-1].total_seconds()
                spacing = 1 / self.sample_rate
                size = int(end / spacing)

                new_index = generate_time_index(self.sample_rate, size)
                new_df = new_df.reindex(new_index, method="nearest")

                # If the sample rates didn't match and we had to
                # resample the dataframe we should redraw the new data
                # so the user can see exactly how the data was modified.
                other_points = {}
            else:
                other_points = other._points

            self._df = pd.concat([self._df, new_df], axis="columns")
            self._df.sort_index(inplace=True)

            for col in new_cols:
                # Use points from other if they have been generated
                if col in other_points:
                    self._points[col] = other_points[col]

        # Wait until we're done to emit the signals
        for col in new_cols:
            self.series_added.emit(col)

        self.data_changed.emit()

    def can_merge(self, other: ViewModel | None) -> bool:
        if self.empty:
            return True

        return (
            other is not None
            and self._df.index.inferred_type == other._df.index.inferred_type
            # We can't merge two models with the same series names
            and not bool(set(self._df.columns).intersection(other._df))
        )

    def add_suffix(self, suffix: str) -> None:
        columns = {str(col): str(col) + suffix for col in self._df}
        self.rename(columns)

    def rename(self, columns: dict[str, str]) -> None:
        self._df.rename(columns=columns, inplace=True)
        for old, new in columns.items():
            if old in self._points:
                self._points[new] = self._points.pop(old)

            self.name_changed.emit(old, new)

    def _update_sample_rate(self) -> None:
        spacing = sample_spacing(self._df)
        if self.index_type == "timedelta64" and spacing:
            sample_rate = int(1 / spacing)
        else:
            sample_rate = 0

        if sample_rate != self._sample_rate:
            self._sample_rate = sample_rate
            self.sample_rate_changed.emit(sample_rate)

    def _series_to_points(self, series: pd.Series) -> QPointFList:
        if series.index.inferred_type == "timedelta64":
            series.index = series.index.total_seconds() #type: ignore

        series = series.astype(float).dropna()
        points = QPointFList()
        points.reserve(series.size) #type: ignore
        for i, v in series.items():
            points.append(QPointF(i, v)) #type: ignore
        return points

    def _df_to_points(self, df: pd.DataFrame) -> dict[str, QPointFList]:
        d = {}
        for col, series in df.items():
            d[col] = self._series_to_points(series)
        return d
