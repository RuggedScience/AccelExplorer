from collections import namedtuple
from typing import Dict, List

import numpy as np
import pandas as pd
from PySide6.QtCharts import QChart, QLineSeries, QValueAxis
from PySide6.QtCore import QObject, QPointF, Qt, QTimer
from PySide6.QtGui import QKeySequence, QUndoStack, QImage
from PySide6.QtWidgets import QTreeWidgetItem

from app.commands.viewcommands import CropCommand, DataCommand, AddDataCommand
from app.utils import df_to_points
from app.utils.markergenerator import MarkerGenerator
from app.widgets.interactivechart import InteractiveChart

AxisRanges = namedtuple("AxisRanges", ["x_min", "x_max", "y_min", "y_max"])


class ViewSeries:
    def __init__(self, name: str, parent: QTreeWidgetItem = None) -> None:
        self._chart_series = QLineSeries()
        self._tree_item = QTreeWidgetItem(parent)
        self.name = name

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        self._chart_series.setName(name)
        self._tree_item.setText(0, name)
        self._name = name

    @property
    def chart_series(self) -> QLineSeries:
        return self._chart_series

    @property
    def tree_item(self) -> QTreeWidgetItem:
        return self._tree_item


class ViewController(QObject):
    def __init__(
        self,
        name: str,
        df: pd.DataFrame,
        display_markers: bool = False,
        parent: QObject = None,
    ):
        super().__init__(parent)

        self._view_series: Dict[QTreeWidgetItem, ViewSeries] = {}

        self._marker_size = 10
        self._marker_count = 5
        self._display_markers = display_markers
        self._marker_generator = MarkerGenerator(50)

        self._tree_item = QTreeWidgetItem()
        self._undo_stack = QUndoStack(self)
        self._chart_view = InteractiveChart()

        self._x_axis = QValueAxis()
        self._y_axis = QValueAxis()

        self.chart.addAxis(self._x_axis, Qt.AlignBottom)
        self.chart.addAxis(self._y_axis, Qt.AlignLeft)

        undo_action = self._undo_stack.createUndoAction(self._chart_view)
        undo_action.setShortcut(QKeySequence.Undo)

        redo_action = self._undo_stack.createRedoAction(self._chart_view)
        redo_action.setShortcut(QKeySequence.Redo)

        self._chart_view.addActions([undo_action, redo_action])

        self.name = name
        self._replace_data(df)

        self.fit_contents()
        # Wait until after we adjust the ranges to start monitoring them
        self._x_axis.rangeChanged.connect(self._axis_range_changed)
        self._y_axis.rangeChanged.connect(self._axis_range_changed)

        self._axis_range_changed()

    def __getitem__(self, key: QTreeWidgetItem | str) -> ViewSeries:
        series = None
        name = ""
        if isinstance(key, QTreeWidgetItem):
            name = key.text(0)
            series = self._view_series.get(key)
        elif isinstance(key, str):
            name = key
            series = self._get_series_from_name(key)

        if series is None:
            raise KeyError(f"{name} not in {self.name}")

        return series

    def __contains__(self, key: QTreeWidgetItem | str) -> bool:
        if isinstance(key, QTreeWidgetItem):
            return key in self._view_series
        elif isinstance(key, str):
            return self._get_series_from_name(key) is not None

    def __iter__(self):
        yield from self._view_series.values()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._tree_item.setText(0, name)
        self.chart.setTitle(name)
        self._name = name

    @property
    def tree_item(self) -> QTreeWidgetItem:
        return self._tree_item

    @property
    def chart_view(self) -> InteractiveChart:
        return self._chart_view

    @property
    def chart(self) -> QChart:
        return self._chart_view.chart()

    @property
    def x_axis(self) -> QValueAxis:
        return self._x_axis

    @property
    def y_axis(self) -> QValueAxis:
        return self._y_axis

    @property
    def df(self) -> pd.DataFrame:
        return self._df.copy()

    @property
    def undo_stack(self) -> None:
        return self._undo_stack

    @property
    def axis_ranges(self) -> AxisRanges:
        return AxisRanges(
            self._x_axis.min(),
            self._x_axis.max(),
            self._y_axis.min(),
            self._y_axis.max(),
        )

    @property
    def display_markers(self) -> bool:
        return self._display_markers

    @display_markers.setter
    def display_markers(self, display: bool):
        if self._display_markers != display:
            self._display_markers = display
            self._marker_generator.reset()
            for series in self._data_series.values():
                self._update_series_markers(series)

            if display:
                self._update_marker_points()

    @property
    def marker_size(self) -> int:
        return self._marker_size

    @marker_size.setter
    def marker_size(self, size: int) -> None:
        if self._marker_size != size:
            for series in self._data_series.values():
                series.setMarkerSize(size)
            self._marker_size = size

    @property
    def marker_count(self) -> int:
        return self._marker_count

    @marker_count.setter
    def marker_count(self, count: int) -> None:
        if self._marker_count != count:
            self._marker_count = count
            self._update_marker_points()

    def set_df(self, df: pd.DataFrame, title: str) -> None:
        cmd = DataCommand(title, self, self._df, df)
        self._undo_stack.push(cmd)

    def can_add_data(self, df: pd.DataFrame) -> bool:
        return df.index.inferred_type == self._df.index.inferred_type

    def add_data(
        self,
        name: str,
        df: pd.DataFrame,
        points: Dict[str, List[QPointF]] = None,
    ) -> None:
        for col in df:
            i = 1
            old_name = col
            while col in self._df:
                col = f"{col} ({i})"
                i += 1

            if old_name != col:
                df.rename(columns={old_name: col}, inplace=True)

        if points is None:
            points = df_to_points(df)

        cmd = AddDataCommand(name, self, df, points)
        self._undo_stack.push(cmd)

    def _add_data(self, df: pd.DataFrame, points: Dict[str, List[QPointF]]):
        self._df = pd.concat([self._df, df], axis="columns")
        for name, data in points.items():
            series = self._add_series(name)
            series.chart_series.replace(data)

    def _remove_data(self, df: pd.DataFrame) -> None:
        self._df.drop(df.columns, axis="columns", inplace=True)
        for col in df:
            self._remove_series(col)

    def crop(self) -> None:
        x_min = self._x_axis.min()
        x_max = self._x_axis.max()
        if self._df.index.inferred_type == "timedelta64":
            x_min = pd.to_timedelta(x_min, unit="S")
            x_max = pd.to_timedelta(x_max, unit="S")

        new_df = self._df[(self._df.index >= x_min) & (self._df.index <= x_max)]

        old_points = {series.name(): series.points() for series in self.chart.series()}
        new_points = df_to_points(new_df)

        cmd = CropCommand(self, self._df, new_df, old_points, new_points)
        self._undo_stack.push(cmd)

    def fit_contents(self) -> None:
        cols = [
            series.name
            for series in self._view_series.values()
            if series.chart_series.isVisible()
        ]

        if not cols:
            return

        df = self._df[cols]
        df = df.dropna(how="all")

        x_min = df.index.min()
        x_max = df.index.max()
        if df.index.inferred_type == "timedelta64":
            x_min = x_min.total_seconds()
            x_max = x_max.total_seconds()

        # Add some margin to the y axis
        y_min = df.min(axis=1).min()
        y_max = df.max(axis=1).max()
        y_min -= abs(y_min * 0.1)
        y_max += abs(y_max * 0.1)

        self.setAxisRanges(x_min, x_max, y_min, y_max)

    def rename_series(self, series: QTreeWidgetItem | str, name: str):
        view_series = None
        if isinstance(series, QTreeWidgetItem):
            view_series = self._view_series.get(series)
        elif isinstance(series, str):
            view_series = self._get_series_from_name(series)

        if view_series is None or view_series.name not in self._df:
            raise ValueError(f"Series not in {self.name}")

        self._df.rename(columns={view_series.name: name}, inplace=True)
        view_series.name = name

    def _point_hovered(self, pos: QPointF, state: bool):
        if state:
            x_title = self.chart.axisX().titleText()
            y_title = self.chart.axisY().titleText()
            self.chart_view.show_tooltip(
                pos,
                f"{x_title}: {pos.x():.2f}\n{y_title}: {pos.y():.2f}",
            )
        else:
            self.chart_view.tooltip.hide()

    def _add_series(self, name: str) -> ViewSeries:
        view_series = ViewSeries(name, self._tree_item)

        chart_series = view_series.chart_series
        self.chart.addSeries(chart_series)
        chart_series.attachAxis(self._x_axis)
        chart_series.attachAxis(self._y_axis)
        chart_series.hovered.connect(self._point_hovered)
        chart_series.clicked.connect(self.chart_view.keep_tooltip)

        tree_item = view_series.tree_item
        tree_item.setCheckState(0, Qt.Checked)

        self._view_series[tree_item] = view_series

        self._update_series_markers(chart_series)

        return view_series

    def _remove_series(self, series: str | QTreeWidgetItem | ViewSeries) -> None:
        view_series = None
        if isinstance(series, str):
            view_series = self._get_series_from_name(series)
        elif isinstance(series, QTreeWidgetItem):
            view_series = self._view_series.get(series)
        elif isinstance(series, ViewSeries):
            view_series = series

        if view_series is None:
            raise ValueError(f"Could not find {series} in {self.name}")

        self._view_series.pop(view_series.tree_item)
        self._tree_item.removeChild(view_series.tree_item)
        self.chart.removeSeries(view_series.chart_series)
        view_series.chart_series.deleteLater()

    def _update_series(self) -> None:
        new_names = {str(col) for col in self._df}
        old_names = {s.name for s in self._view_series.values()}

        added_cols = new_names.difference(old_names)
        removed_cols = old_names.difference(new_names)

        for name in removed_cols:
            self._remove_series(name)

        for name in added_cols:
            self._add_series(name)

    def _update_series_points(
        self,
        series: QLineSeries | ViewSeries,
        points: List[QPointF],
    ) -> None:
        if isinstance(series, ViewSeries):
            series = series.chart_series

        series.replace(points)
        # Only use OpenGL with large datasets
        use_opengl = len(points) > 100000
        # Bug when disabling opengl causes the "old"
        # series data to still be drawn on top of
        # the new series data. Hide and show fixes this.
        if not use_opengl and series.useOpenGL():
            series.hide()
            QTimer.singleShot(10, series.show)

        series.setUseOpenGL(use_opengl)

    def _replace_data(self, df: pd.DataFrame) -> None:
        self._df = df
        self._update_series()
        all_points = df_to_points(df)

        for view_series in self._view_series.values():
            points = all_points.get(view_series.name)
            if points is not None:
                self._update_series_points(view_series.chart_series, points)

    def _update_series_markers(self, series: QLineSeries) -> None:
        if not self._display_markers:
            series.setMarkerSize(0)
            series.setSelectedLightMarker(QImage())
            series.deselectAllPoints()
        else:
            series.setMarkerSize(self._marker_size)
            series.setSelectedLightMarker(self._marker_generator.next(series.color()))

    def _update_marker_points(self, start: float = None, end: float = None) -> None:
        if start is None:
            start = self._x_axis.min()

        if end is None:
            end = self._x_axis.max()

        # Create linearly spaced points even with the axis tick counts
        indices = np.linspace(start, end, self._marker_count)

        if self._df.index.inferred_type == "timedelta64":
            start = pd.to_timedelta(start, "S")
            end = pd.to_timedelta(end, "S")
            indices = pd.to_timedelta(indices, "S")

        points = self._df.index.get_indexer(indices, method="nearest")
        for series in self._view_series.values():
            series.chart_series.deselectAllPoints()
            series.chart_series.selectPoints(points)

    def setAxisRanges(
        self,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        self._x_axis.setRange(x_min, x_max)
        self._y_axis.setRange(y_min, y_max)

    def _axis_range_changed(self) -> None:
        ranges = self.axis_ranges

        if self._display_markers:
            self._update_marker_points(ranges.x_min, ranges.x_max)

    def _get_series_from_name(self, name: str) -> ViewSeries:
        for s in self._view_series.values():
            if s.name == name:
                return s
