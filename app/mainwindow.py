from typing import Tuple, List, NamedTuple
from collections.abc import Iterable

import pandas as pd
import endaq as ed

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QMdiSubWindow,
    QTreeWidgetItem,
    QMenu,
    QFileDialog,
)
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QAction, QCursor
from PySide6.QtCore import QEvent, QFileInfo, Qt, QPointF, QPoint, QTimer, QObject
from PySide6.QtCharts import QValueAxis, QLineSeries

from .utils import get_plugin_manager
from .categories import DataFilter, DataView
from .ui import resources_rc
from .ui.ui_mainwindow import Ui_MainWindow
from .zoomchart import ZoomChart
from .parserdialog import ParserDialog
from .snapmdiarea import SnapMdiArea


class ViewData(NamedTuple):
    tree_item: QTreeWidgetItem
    widget: ZoomChart
    df: pd.DataFrame
    window: QMdiSubWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle(
            f"{QApplication.applicationName()} {QApplication.applicationVersion()}[*]"
        )

        self._mdi_area = SnapMdiArea(self)
        self.setCentralWidget(self._mdi_area)

        self.ui.treeWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.treeWidget.customContextMenuRequested.connect(
            self._context_menu_requested
        )
        self.ui.treeWidget.currentItemChanged.connect(self._current_tree_item_changed)
        self.ui.treeWidget.itemChanged.connect(self._tree_item_changed)

        pm = get_plugin_manager()
        pm.setCategoriesFilter({"Filters": DataFilter, "Views": DataView})
        pm.collectPlugins()

        self._filter_menu = QMenu("Filters")
        for plugin in pm.getPluginsOfCategory("Filters"):
            action = QAction(plugin.name, self)
            action.setWhatsThis(plugin.description)
            action.filter = plugin.plugin_object
            self._filter_menu.addAction(action)

        self._view_menu = QMenu("Views")
        for plugin in pm.getPluginsOfCategory("Views"):
            action = QAction(plugin.name, self)
            action.setWhatsThis(plugin.description)
            action.view = plugin.plugin_object
            self._view_menu.addAction(action)

        self._open_views: List[ViewData] = []

    def _add_subwindow(self, widget: QWidget) -> QMdiSubWindow:
        sub_window = self._mdi_area.addSubWindow(widget)
        widget.show()
        if len(self._mdi_area.subWindowList()) == 1:
            sub_window.showMaximized()
        else:
            self._mdi_area.tileSubWindows()
        return sub_window

    def _add_chart(
        self,
        df: pd.DataFrame,
        callouts: pd.DataFrame = None,
        x_range: Tuple[float, float] = None,
        y_range: Tuple[float, float] = None,
        x_title: str = None,
        y_title: str = None,
    ) -> ZoomChart:
        chart_view = ZoomChart(self)
        chart = chart_view.chart()
        # chart.legend().hide()

        def point_hovered(pos: QPointF, state: bool):
            if state:
                chart_view.show_tooltip(
                    pos, f"{x_title}: {pos.x():.2f}\n{y_title}: {pos.y():.2f}"
                )
            else:
                chart_view.tooltip.hide()

        x = df.index
        x_axis = QValueAxis()

        if x_title:
            x_axis.setTitleText(x_title)
        else:
            x_axis.setTitleText(x.name)

        if x_range:
            x_axis.setRange(*x_range)
        else:
            if isinstance(x, pd.TimedeltaIndex):
                x_axis.setRange(x.min().total_seconds(), x.max().total_seconds())
            else:
                x_axis.setRange(x[0], x[-1])

        y_axis = QValueAxis()

        if y_title:
            y_axis.setTitleText(y_title)

        if y_range:
            y_axis.setRange(*y_range)
        else:
            # Add some margin to the y axis
            y_min = df.min(axis=1).min()
            y_max = df.max(axis=1).max()
            y_axis.setRange(y_min - abs(y_min * 0.1), y_max + abs(y_max * 0.1))

        chart.addAxis(x_axis, Qt.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignLeft)

        for col, data in df.items():
            points = []
            for index, value in data.items():
                if isinstance(index, pd.Timedelta):
                    x = float(index.total_seconds())
                else:
                    x = float(index)

                y = float(value)
                points.append(QPointF(x, y))

            series = QLineSeries()
            series.setName(col)

            # Only use OpenGL with large datasets
            if len(points) > 100000:
                series.setUseOpenGL(True)

            chart.addSeries(series)
            series.attachAxis(x_axis)
            series.attachAxis(y_axis)
            series.replace(points)

            pen = series.pen()
            pen.setWidth(4)
            series.setPen(pen)

            series.hovered.connect(point_hovered)
            series.clicked.connect(chart_view.keep_tooltip)

        if not callouts is None:
            for _, row in callouts.iterrows():
                pos = QPointF(row["freq"], row["mag"])
                chart_view.add_callout(
                    pos, f"Frequency: {pos.x():.2f}\nMagnitude: {pos.y():.2f}"
                )

        return chart_view

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(watched, QMdiSubWindow) and event.type() == QEvent.Close:
            for view in self._open_views:
                if view.window == watched:
                    self._remove_view(view)

        return super().eventFilter(watched, event)

    def _remove_view(self, view: ViewData):
        self.ui.treeWidget.invisibleRootItem().removeChild(view.tree_item)
        self._open_views.remove(view)

    def _add_view(
        self,
        name: str,
        df: pd.DataFrame,
        x_title: str,
        y_title: str,
        x_range: Tuple[float, float] = None,
        y_range: Tuple[float, float] = None,
    ) -> ViewData:
        chart = self._add_chart(
            df, x_title=x_title, y_title=y_title, x_range=x_range, y_range=y_range
        )
        chart.chart().setTitle(name)
        tree_item = QTreeWidgetItem()
        tree_item.setText(0, name)
        tree_item.setFlags(tree_item.flags() | Qt.ItemIsAutoTristate)
        tree_item.setExpanded(True)
        self.ui.treeWidget.addTopLevelItem(tree_item)
        sw = self._add_subwindow(chart)
        sw.setWindowTitle(name)
        sw.installEventFilter(self)

        for series in chart.chart().series():
            series_item = QTreeWidgetItem(tree_item)
            series_item.setText(0, series.name())
            series_item.setCheckState(0, Qt.Checked)
            series_item.series = series

        data = ViewData(tree_item=tree_item, widget=chart, df=df, window=sw)
        self._open_views.append(data)
        return data

    def _add_files(self, files: Iterable[QFileInfo]) -> None:
        for file in files:
            if file.suffix().lower() == "ide":
                df = ed.ide.get_primary_sensor_data(
                    name=file.absoluteFilePath(), measurement_type=ed.ide.ACCELERATION
                )
                s = df.index.to_series()
                st = s[0]
                s = s.apply(lambda x: x - st)
                df.index = s
            elif file.suffix().lower() == "h5":
                df = pd.read_hdf(file.absoluteFilePath())
            else:
                dlg = ParserDialog(file.absoluteFilePath(), self)
                if not dlg.exec():
                    continue
                df = dlg.df

            self._add_view(file.fileName(), df, df.index.name, "Acceleration (g's)")

    def _get_supported_files(self, event: QDropEvent) -> List[QFileInfo]:
        files = []
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            for url in mimeData.urls():
                if url.isLocalFile():
                    info = QFileInfo(url.toLocalFile())
                    if info.suffix().lower() in ("csv", "ide", "h5"):
                        files.append(info)
        return files

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        files = self._get_supported_files(event)
        if files:
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        files = self._get_supported_files(event)
        if files:
            event.acceptProposedAction()
            QTimer.singleShot(1, lambda: self._add_files(files))

    def _context_menu_requested(self, pos: QPoint) -> None:
        item = self.ui.treeWidget.itemAt(pos)

        menu = QMenu(self)

        export_action = QAction("Export")
        menu.addAction(export_action)

        if self._filter_menu.actions():
            menu.addMenu(self._filter_menu)

        if self._view_menu.actions():
            menu.addMenu(self._view_menu)

        action = menu.exec(QCursor.pos())
        if not action:
            return

        df = self._get_df_from_tree_item(item)
        if df is None:
            return

        if action is export_action:
            fileName, filter = QFileDialog.getSaveFileName(
                self, "Export File", None, "HDFS (*.h5);;CSV (*.csv)"
            )
            if fileName:
                if "csv" in filter:
                    df.to_csv(fileName)
                else:
                    df.to_hdf(fileName, key=item.text(0), mode="w")
            pass
        elif hasattr(item, "series"):
            name = item.series.name()
            input_df = df[name].to_frame()
        else:
            input_df = df

        if hasattr(action, "view"):
            new_df = action.view.generate(input_df)
            name = action.view.name
            self._add_view(
                f"{name} - {item.text(0)}",
                new_df,
                action.view.x_title,
                action.view.y_title,
                action.view.x_range,
                action.view.y_range,
            )
        elif hasattr(action, "filter"):
            new_df = action.filter.filter(input_df)
            name = action.filter.name
            self._add_view(
                f"{name} - {item.text(0)}", new_df, new_df.index.name, "Test"
            )

    def _current_tree_item_changed(self, current: QTreeWidgetItem, _) -> None:
        data = self._get_view_from_tree_item(current)
        if data is None:
            return

        self._view_menu.setEnabled((data.df is not None))

    def _tree_item_changed(self, item: QTreeWidgetItem, column: int):
        if column == 0 and hasattr(item, "series"):
            item.series.setVisible(item.checkState(0) == Qt.Checked)

    def _get_root_parent(self, item):
        while item and item.parent() is not None:
            item = item.parent()
        return item

    def _get_view_from_tree_item(self, item: QTreeWidgetItem) -> ViewData:
        item = self._get_root_parent(item)
        if item:
            for view in self._open_views:
                if view.tree_item is item:
                    return view
        return None

    def _get_df_from_tree_item(self, item: QTreeWidgetItem) -> pd.DataFrame:
        view = self._get_view_from_tree_item(item)
        if view:
            if view.tree_item is item:
                return view.df

            for col in view.df:
                if col == item.text(0):
                    return view.df[col].to_frame()

        return None
