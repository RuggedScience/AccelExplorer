import os
from typing import Tuple, List
from collections.abc import Iterable

import pandas as pd
import endaq as ed

from yapsy.PluginManager import PluginManager

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QMdiSubWindow,
    QTreeWidgetItem,
    QMenu,
    QFileDialog,
    QUndoView,
)
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QAction,
    QCursor,
    QUndoStack,
    QKeySequence,
)
from PySide6.QtCore import QEvent, QFileInfo, Qt, QPoint, QTimer, QObject
from PySide6.QtCharts import QValueAxis

from app.utils import get_plugin_path, timing
from app.plugins.dataview import DataView
from app.plugins.datafilter import DataFilter
from app.ui import resources_rc
from app.ui.ui_mainwindow import Ui_MainWindow
from app.viewcontroller import ViewController
from app.commands.modifydatacommand import ModifyDataCommand

from .zoomchart import ZoomChart
from .parserdialog import ParserDialog
from .snapmdiarea import SnapMdiArea
from .optionsdialog import OptionsDialog


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

        plugin_dir = get_plugin_path()
        pm = PluginManager()
        pm.setPluginPlaces(
            [
                os.path.join(plugin_dir, "filters"),
                os.path.join(plugin_dir, "views"),
            ]
        )
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

        self._open_views: List[ViewController] = []

        self._undo_stack = QUndoStack(self)

        undoAction = self._undo_stack.createUndoAction(self, "Undo")
        undoAction.setShortcuts(QKeySequence.Undo)

        redoAction = self._undo_stack.createRedoAction(self, "Redo")
        redoAction.setShortcuts(QKeySequence.Redo)

        self.addActions([undoAction, redoAction])

        self.ui.undoView.setStack(self._undo_stack)

    def _add_subwindow(self, widget: QWidget) -> QMdiSubWindow:
        sub_window = self._mdi_area.addSubWindow(widget)
        widget.show()
        if len(self._mdi_area.subWindowList()) == 1:
            sub_window.showMaximized()
        else:
            self._mdi_area.tileSubWindows()
        return sub_window

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(watched, QMdiSubWindow) and event.type() == QEvent.Close:
            for view in self._open_views:
                if view.chart_view is watched.widget():
                    self._remove_view(view)

        return super().eventFilter(watched, event)

    def _remove_view(self, view: ViewController):
        self.ui.treeWidget.invisibleRootItem().removeChild(view.tree_item)
        self._open_views.remove(view)

    def _create_chart(
        self,
        x_title: str,
        y_title: str,
        x_range: Tuple[float, float],
        y_range: Tuple[float, float],
    ):
        chart_view = ZoomChart(self)
        chart = chart_view.chart()

        x_axis = QValueAxis()
        x_axis.setTitleText(x_title)
        x_axis.setRange(*x_range)

        y_axis = QValueAxis()
        y_axis.setTitleText(y_title)
        y_axis.setRange(*y_range)

        chart.addAxis(x_axis, Qt.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignLeft)

        return chart_view

    def _add_view(
        self,
        name: str,
        df: pd.DataFrame,
        x_title: str,
        y_title: str,
        x_range: Tuple[float, float] = None,
        y_range: Tuple[float, float] = None,
    ) -> ViewController:

        if x_range is None:
            x = df.index
            if isinstance(x, pd.TimedeltaIndex):
                x_range = (x.min().total_seconds(), x.max().total_seconds())
            else:
                x_range = (x[0], x[-1])

        if y_range is None:
            # Add some margin to the y axis
            y_min = df.min(axis=1).min()
            y_max = df.max(axis=1).max()
            y_range = (y_min - abs(y_min * 0.1), y_max + abs(y_max * 0.1))

        chart_view = self._create_chart(x_title, y_title, x_range, y_range)
        controller = ViewController(name, chart_view, df)

        tree_item = controller.tree_item
        tree_item.setFlags(tree_item.flags() | Qt.ItemIsAutoTristate)
        self.ui.treeWidget.addTopLevelItem(tree_item)
        tree_item.setExpanded(True)
        sw = self._add_subwindow(chart_view)
        sw.setWindowTitle(name)
        sw.installEventFilter(self)

        for series in controller.chart.series():
            series_item = QTreeWidgetItem(tree_item)
            series_item.setText(0, series.name())
            series_item.setCheckState(0, Qt.Checked)
            series_item.series = series

        self._open_views.append(controller)
        return controller

    def _add_files(self, files: Iterable[QFileInfo]) -> None:
        for file in files:
            if file.suffix().lower() == "ide":
                df: pd.DataFrame = ed.ide.get_primary_sensor_data(
                    name=file.absoluteFilePath(), measurement_type=ed.ide.ACCELERATION
                )
                # Convert index from datetime to timedelta
                series = df.index.to_series()
                df.index = series - series[0]

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

        crop_action = QAction("Crop")
        menu.addAction(crop_action)
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

        controller = self._get_view_from_tree_item(item)
        if controller is None:
            return

        if action is crop_action:
            chart = controller.chart
            x_axis = chart.axisX()
            y_axis = chart.axisY()

            x_min = x_axis.min()
            x_max = x_axis.max()
            if df.index.inferred_type == "timedelta64":
                x_min = pd.to_timedelta(x_min, unit="S")
                x_max = pd.to_timedelta(x_max, unit="S")

            new_df = df[(df.index >= x_min) & (df.index <= x_max)]
            self._undo_stack.push(ModifyDataCommand("Crop - ", controller, df, new_df))
        elif action is export_action:
            suggested_name = item.text(0).split(".")[0]
            fileName, filter = QFileDialog.getSaveFileName(
                self, "Export File", suggested_name, "HDFS (*.h5);;CSV (*.csv)"
            )
            if fileName:
                if "csv" in filter:
                    df.to_csv(fileName)
                else:
                    # Clean up the key so it doesn't yell about natural naming...
                    suggested_name = suggested_name.replace(" - ", "_")
                    suggested_name = suggested_name.replace("-", "_")
                    suggested_name = suggested_name.replace(" ", "_")
                    df.to_hdf(fileName, key=suggested_name, mode="w")
            pass
        elif hasattr(item, "series"):
            name = item.series.name()
            input_df = df[name].to_frame()
            item_text = f"{controller.tree_item.text(0)} ({item.text(0)} only)"
        else:
            input_df = df
            item_text = item.text(0)

        if hasattr(action, "view"):
            params = {}
            options = action.view.options
            if options:
                dlg = OptionsDialog(options, self)
                if dlg.exec():
                    params = dlg.values

            new_df = action.view.generate(input_df, **params)
            name = action.view.name
            self._add_view(
                f"{name} - {item_text}",
                new_df,
                action.view.x_title,
                action.view.y_title,
            )
        elif hasattr(action, "filter"):
            params = {}
            options = action.filter.options
            if options:
                dlg = OptionsDialog(options, self)
                if dlg.exec():
                    params = dlg.values
            new_df = action.filter.filter(input_df, **params)
            self._undo_stack.push(
                ModifyDataCommand(
                    f"{action.filter.name} filter - ", controller, df, new_df
                )
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

    def _get_view_from_tree_item(self, item: QTreeWidgetItem) -> ViewController:
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
