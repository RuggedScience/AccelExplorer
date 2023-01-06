from typing import List

import pandas as pd

from PySide6.QtCharts import QChart, QLineSeries
from PySide6.QtCore import QTimer, QPointF, QObject
from PySide6.QtWidgets import QTreeWidgetItem

from app.widgets.zoomchart import ZoomChart


class ViewController(QObject):
    def __init__(self, name: str, chart_view: ZoomChart, df: pd.DataFrame):
        self._tree_item = QTreeWidgetItem()
        self._chart_view = chart_view
        self.name = name
        self.df = df

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
    def chart_view(self) -> ZoomChart:
        return self._chart_view

    @property
    def chart(self) -> QChart:
        return self._chart_view.chart()

    @property
    def df(self) -> pd.DataFrame:
        return self._df.copy()

    @df.setter
    def df(self, df: pd.DataFrame) -> None:
        self._replace_data(df)

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

    def _add_series(self, name: str) -> QLineSeries:
        series = QLineSeries()
        series.setName(name)
        self.chart.addSeries(series)
        series.attachAxis(self.chart.axisX())
        series.attachAxis(self.chart.axisY())
        series.hovered.connect(self._point_hovered)
        series.clicked.connect(self.chart_view.keep_tooltip)
        return series

    def _generate_series_data(self, series: pd.Series) -> List[QPointF]:
        if series.index.inferred_type == "timedelta64":
            series.index = series.index.total_seconds()

        return [QPointF(float(i), float(v)) for i, v in series.items()]

    def _replace_data(self, df: pd.DataFrame) -> None:
        for col, data in df.items():
            found = False
            for series in self.chart.series():
                if series.name() == col:
                    found = True
                    break

            if not found:
                series = self._add_series(col)

            points = self._generate_series_data(data)
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

            pen = series.pen()
            pen.setWidth(4)
            series.setPen(pen)

        self._df = df
