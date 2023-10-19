from __future__ import annotations

import numpy as np
import pandas as pd
from PySide6.QtCharts import QChart, QValueAxis, QLineSeries
from PySide6.QtCore import QObject, QPointF, QPointFList, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QUndoStack, QImage, QPainter
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from app.utils import MarkerGenerator, MarkerShape, undoable
from app.widgets import InteractiveChart, ColorWidget

from .viewmodel import ViewModel


class ViewSeries(QObject):
    legend_clicked = Signal()

    def __init__(
        self,
        name: str,
        parent: ViewController,
    ) -> None:
        super().__init__()

        self._chart_series = QLineSeries()
        self._chart_series.colorChanged.connect(self._color_changed) # type: ignore

        self._color_widget = None

        self._tree_item = QTreeWidgetItem()
        self._tree_item.setFlags(self._tree_item.flags() | Qt.ItemFlag.ItemIsEditable)

        self._name = ""
        self._marker_shape = None

        self.setParent(parent)
        self.set_name(name, undo=False) # type: ignore
        self.marker_size = 15
        self._update_marker_image()

    def setParent(self, parent: ViewController) -> None:
        assert isinstance(parent, ViewController)
        self._parent = parent

        parent.tree_item.addChild(self._tree_item)
        self.undo_stack = parent.undo_stack
        self._parent_changed()
        super().setParent(parent)

    @property
    def controller(self) -> ViewController:
        return self._parent
    
    @property
    def model(self) -> ViewModel:
        return self.controller.model

    @property
    def name(self) -> str:
        return self._name

    @undoable("name", title="Renamed series from {old_value} to {new_value}")
    def set_name(self, name: str) -> None:
        if self._name != name:
            self.model.rename({self._name: name})

            self._name = name
            self._tree_item.setText(0, name)
            self._chart_series.setName(name)

    @property
    def chart_series(self) -> QLineSeries:
        return self._chart_series

    @property
    def tree_item(self) -> QTreeWidgetItem:
        return self._tree_item

    @property
    def points(self) -> list[QPointF] | QPointFList:
        return self._chart_series.points()

    @points.setter
    def points(self, points: list[QPointF] | QPointFList) -> None:
        self.chart_series.replace(points) #type: ignore

    @property
    def color(self) -> QColor:
        return self._chart_series.color()

    @color.setter
    def color(self, color: QColor | str) -> None:
        if isinstance(color, str):
            color = QColor.fromString(color)

        if color != self._chart_series.color():
            self._chart_series.setColor(color)

    @property
    def width(self) -> int:
        return self._chart_series.pen().width()

    @width.setter
    def width(self, width: int) -> None:
        pen = self._chart_series.pen()
        pen.setWidth(width)
        self._chart_series.setPen(pen)

    @property
    def marker_shape(self) -> MarkerShape | None:
        return self._marker_shape

    @marker_shape.setter
    def marker_shape(self, shape: MarkerShape | int) -> None:
        if isinstance(shape, int):
            shape = MarkerShape(shape)

        if shape != self._marker_shape:
            self._marker_shape = shape
            self._update_marker_image()

    @property
    def marker_size(self) -> float:
        return self._chart_series.markerSize()

    @marker_size.setter
    def marker_size(self, size: float) -> None:
        if size != self._chart_series.markerSize():
            self._chart_series.setMarkerSize(size)

    def _update_marker_image(self) -> None:
        if self._marker_shape is None:
            self._chart_series.setSelectedLightMarker(QImage())
        else:
            self._chart_series.setSelectedLightMarker(
                MarkerGenerator.get_marker(self._marker_shape, 50, self.color)
            )

    def _color_changed(self, color: QColor) -> None:
        if self._color_widget:
            self._color_widget.color = color
        self._update_marker_image()

    def _parent_changed(self) -> None:
        if self._tree_item.treeWidget():
            if self._color_widget is None:
                self._color_widget = ColorWidget(self._chart_series.color())
                self._color_widget.clicked.connect(self.legend_clicked)
            self._tree_item.treeWidget().setItemWidget(
                self._tree_item, 1, self._color_widget
            )
        elif self._color_widget is not None:
            self._color_widget.deleteLater()
            self._color_widget = None

    def deleteLater(self) -> None:
        self._chart_series.deleteLater()

        if self._color_widget is not None:
            self._color_widget.deleteLater()

        if self._tree_item.parent():
            self._tree_item.parent().removeChild(self._tree_item)
        return super().deleteLater()


class ViewController(QObject):
    legend_clicked = Signal(ViewSeries)

    def __init__(
        self,
        name: str,
        model: ViewModel,
        display_markers: bool = False,
        item_parent: QTreeWidget | QTreeWidgetItem | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._name: str | None = None
        self._tooltip_lines: list[str] = []
        self._view_series: dict[QTreeWidgetItem, ViewSeries] = {}

        self._series_width = 1
        self._marker_size = 10
        self._marker_count = 5
        self._display_markers = display_markers
        self._marker_generator = MarkerGenerator()

        self._tree_item = QTreeWidgetItem()
        self._tree_item.setFlags(self._tree_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self._undo_stack = QUndoStack(self)
        self._chart_view = InteractiveChart()
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self._chart_view.chart().legend().hide()

        self._x_axis = QValueAxis()
        self._y_axis = QValueAxis()

        self._x_axis.setTitleText(model.x_axis)
        self._y_axis.setTitleText(model.y_axis)

        self.chart.addAxis(self._x_axis, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(self._y_axis, Qt.AlignmentFlag.AlignLeft)

        self.set_item_parent(item_parent)
        self.set_model(model, undo=False) # type: ignore
        self.set_name(name, undo=False) # type: ignore

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

    def __len__(self):
        return len(self._view_series)

    @property
    def name(self) -> str | None:
        return self._name

    @undoable("name", title="Renamed from {old_value} to {new_value}")
    def set_name(self, name: str) -> None:
        if name != self._name:
            self._name = name
            self._tree_item.setText(0, name)
            self.chart.setTitle(name)

    @property
    def model(self) -> ViewModel:
        return self._model

    @undoable("model", title_arg="title", remove_title_arg=True)
    def set_model(self, model: ViewModel) -> None:

        added_series = []
        removed_series = []

        if hasattr(self, '_model'):
            self._model.disconnect(self)
            added_series = model.difference(self._model)
            removed_series = self._model.difference(model)
        else:
            added_series = model.difference(None)

        model.series_added.connect(self._add_series)
        model.series_removed.connect(self._remove_series)
        model.data_changed.connect(self._data_changed)
        self._model = model

        # Sync series to the new model keeping any existing series
        for name in sorted(removed_series):
            self._remove_series(name)

        for name in sorted(added_series):
            self._add_series(name)

        all_points = self._model.points
        for name, points in all_points.items():
            if name in self and name not in added_series:
                self[name].points = points

        self._update_tooltip()
        self._data_changed()
        self.fit_contents()

    def add_tooltips(self, tooltips: str | list[str]):
        if isinstance(tooltips, str):
            tooltips = [tooltips]

        self._tooltip_lines += tooltips
        self._update_tooltip()

    def set_item_parent(self, parent: QTreeWidget | QTreeWidgetItem | None) -> None:
        old_parent = self._tree_item.parent() or self._tree_item.treeWidget()
        if old_parent is not None:
            old_parent.removeChild(self._tree_item)

        if isinstance(parent, QTreeWidget):
            parent.addTopLevelItem(self._tree_item)
        elif isinstance(parent, QTreeWidgetItem):
            parent.addChild(self._tree_item)

        for series in self:
            series._parent_changed()

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
        return self._model.df

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @property
    def series_width(self) -> int:
        return self._series_width

    @series_width.setter
    def series_width(self, width: int) -> None:
        self._series_width = width
        for series in self:
            series.width = width

    @property
    def display_markers(self) -> bool:
        return self._display_markers

    @display_markers.setter
    def display_markers(self, display: bool):
        if self._display_markers != display:
            self._display_markers = display
            self._update_marker_points()

    @property
    def marker_size(self) -> int:
        return self._marker_size

    @marker_size.setter
    def marker_size(self, size: int) -> None:
        if self._marker_size != size:
            self._marker_size = size
            for series in self._view_series.values():
                series.marker_size = size

    @property
    def marker_count(self) -> int:
        return self._marker_count

    @marker_count.setter
    def marker_count(self, count: int) -> None:
        if self._marker_count != count:
            self._marker_count = count
            if self._display_markers:
                self._update_marker_points()

    def setAxisRanges(
        self,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        self._x_axis.setRange(x_min, x_max)
        self._y_axis.setRange(y_min, y_max)

    def crop(self) -> None:
        x_min = self._x_axis.min()
        x_max = self._x_axis.max()

        df = self._model.df
        if df.index.inferred_type == "timedelta64":
            x_min = pd.to_timedelta(x_min, unit="S")
            x_max = pd.to_timedelta(x_max, unit="S")

        new_df = df[(df.index >= x_min) & (df.index <= x_max)]

        # If the data is time data, reset the index so
        # the data starts at 0.00 seconds. Helps when
        # dragging and dropping new series.
        if new_df.index.inferred_type == "timedelta64":
            series = new_df.index.to_series()
            new_df.index = series - series.iloc[0]

        new_model = ViewModel(new_df)
        self.set_model(new_model, title="Crop") #type: ignore

    def fit_contents(self) -> None:
        # Get a list of visible series
        cols = [
            series.name
            for series in self._view_series.values()
            if series.chart_series.isVisible()
        ]

        if not cols:
            return

        # Create a dataframe with only the visible data
        df = self._model.df[cols]
        # Drop rows missing all data. This gives us accurate
        # min/max values for our visible series.
        df = df.dropna(how="all")

        x_min = df.index.min()
        x_max = df.index.max()
        if df.index.inferred_type == "timedelta64":
            x_min = x_min.total_seconds()
            x_max = x_max.total_seconds()
        elif df.index.inferred_type == "datetime64":
            x_min = (x_min - pd.Timestamp("1970-01-01")) // pd.Timedelta("1s")
            x_max = (x_max - pd.Timestamp("1970-01-01")) // pd.Timedelta("1s")

        y_min = df.min(axis=1).min()
        y_max = df.max(axis=1).max()
        # Add some margin to the y axis
        y_min -= abs(y_min * 0.1)
        y_max += abs(y_max * 0.1)

        self.setAxisRanges(x_min, x_max, y_min, y_max)

    def set_series_color(self, series: ViewSeries, color: QColor) -> None:
        if color != series.color:
            series.color = color

    def _point_hovered(self, pos: QPointF, state: bool) -> None:
        if state:
            sender = self.sender()
            if isinstance(sender, QLineSeries):
                series_name = sender.name() + "\n"
            else:
                series_name = ""
            x_title = self.chart.axisX().titleText() or 'X'
            y_title = self.chart.axisY().titleText() or 'Y'
            self.chart_view.show_tooltip(
                pos,
                f"{series_name}{x_title}: {pos.x():.2f}\n{y_title}: {pos.y():.2f}",
            )
        else:
            self.chart_view.tooltip.hide()

    def _add_series(self, name: str) -> ViewSeries:
        view_series = ViewSeries(name, parent=self)
        view_series.marker_shape = self._marker_generator.next_shape()
        view_series.marker_size = self._marker_size

        view_series.legend_clicked.connect(self._legend_clicked)

        chart_series = view_series.chart_series
        self.chart.addSeries(chart_series)
        chart_series.attachAxis(self._x_axis)
        chart_series.attachAxis(self._y_axis)
        chart_series.hovered.connect(self._point_hovered)
        chart_series.clicked.connect(self.chart_view.keep_tooltip)

        tree_item = view_series.tree_item
        tree_item.setCheckState(0, Qt.CheckState.Checked)

        view_series.width = self._series_width
        view_series.points = self._model.points[name]

        self._view_series[tree_item] = view_series

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
        view_series.deleteLater()

    def _update_tooltip(self) -> None:
        lines = self._tooltip_lines.copy()
        lines.append(f"Points: {self._model.shape[0]:n}")
        if self._model.sample_rate:
            lines.append(f"Sample Rate: {int(self._model.sample_rate):n}hz")

        self._tree_item.setToolTip(0, "\n".join(lines))

    def _data_changed(self) -> None:
        self._update_tooltip()
        # Use OpenGL with larger datasets
        use_opengl = self._model.size > 500000
        for series in self:
            cs = series.chart_series
            if cs.useOpenGL() != use_opengl:
                cs.setUseOpenGL(use_opengl)
                # Bug when disabling opengl causes the "old"
                # series data to still be drawn on top of
                # the new series data. Hide and show fixes this.
                if cs.isVisible():
                    QTimer.singleShot(10, series.chart_series.hide)
                    QTimer.singleShot(20, series.chart_series.show)

    def _update_marker_points(self) -> None:
        if not self._display_markers:
            for series in self:
                series.chart_series.deselectAllPoints()
            return

        start = self._x_axis.min()
        end = self._x_axis.max()

        # Create linearly spaced points even with the axis tick counts
        indices = np.linspace(start, end, self._marker_count)

        df = self._model.df
        if df.index.inferred_type == "timedelta64":
            start = pd.to_timedelta(start, "S")
            end = pd.to_timedelta(end, "S")
            indices = pd.to_timedelta(indices, "S")

        points = df.index.get_indexer(indices, method="nearest")
        for series in self._view_series.values():
            series.chart_series.deselectAllPoints()
            series.chart_series.selectPoints(points)

    def _axis_range_changed(self) -> None:
        if self._display_markers:
            self._update_marker_points()

    def _get_series_from_name(self, name: str) -> ViewSeries | None:
        for s in self._view_series.values():
            if s.name == name:
                return s

    def _legend_clicked(self) -> None:
        self.legend_clicked.emit(self.sender())
