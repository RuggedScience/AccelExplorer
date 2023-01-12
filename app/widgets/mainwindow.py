from collections.abc import Iterable
from typing import Dict, List

import endaq as ed
import pandas as pd
from PySide6.QtCore import QFileInfo, QPoint, QSettings, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QCursor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenu,
    QTreeWidgetItem,
    QSpinBox,
)
from yapsy.PluginManager import PluginManager, PluginManagerSingleton

from app.plugins.dataframeplugins import FilterPlugin, ViewPlugin
from app.plugins.parserplugins import AccelCSVParser, CSVParser
from app.ui.ui_mainwindow import Ui_MainWindow
from app.utils import timing
from app.viewcontroller import ViewController
from app.widgets.optionsdialog import OptionsDialog
from app.widgets.parserdialog import ParserDialog


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle(
            f"{QApplication.applicationName()} {QApplication.applicationVersion()}[*]"
        )

        self.ui.treeWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.treeWidget.customContextMenuRequested.connect(
            self._context_menu_requested
        )
        self.ui.treeWidget.currentItemChanged.connect(self._current_tree_item_changed)
        self.ui.treeWidget.itemChanged.connect(self._tree_item_changed)

        self.ui.xMin_spin.valueChanged.connect(self._update_chart_ranges)
        self.ui.xMax_spin.valueChanged.connect(self._update_chart_ranges)
        self.ui.yMin_spin.valueChanged.connect(self._update_chart_ranges)
        self.ui.yMax_spin.valueChanged.connect(self._update_chart_ranges)
        self.ui.xMinorTicks_spin.valueChanged.connect(self._update_tick_counts)
        self.ui.xMajorTicks_spin.valueChanged.connect(self._update_tick_counts)
        self.ui.yMinorTicks_spin.valueChanged.connect(self._update_tick_counts)
        self.ui.yMajorTicks_spin.valueChanged.connect(self._update_tick_counts)
        self.ui.fitToContents_button.clicked.connect(self._fit_to_contents)
        self.ui.markerSize_spin.valueChanged.connect(self._update_markers)
        self.ui.marker_group.clicked.connect(self._update_markers)

        self._open_views: Dict[QTreeWidgetItem, ViewController] = {}

        self._load_plugins()
        self._load_settings()

    @property
    def supported_extensions(self) -> List[str]:
        exts = ["ide"]
        for parser in self._parsers:
            exts += [ext.lower() for ext in parser.supported_extensions()]

        return exts

    def _load_settings(self):
        settings = QSettings()
        self.restoreGeometry(settings.value("geometry"))
        self.restoreState(settings.value("state"))

    def _save_settings(self):
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())

    def _load_plugins(self):
        pm: PluginManager = PluginManagerSingleton.get()

        self._parsers: List[CSVParser] = [CSVParser(), AccelCSVParser()] + [
            plugin.plugin_object for plugin in pm.getPluginsOfCategory("parsers")
        ]

        self._filter_menu = QMenu("Filters")
        self._view_menu = QMenu("Views")

        for plugin in pm.getPluginsOfCategory("dataframe"):
            action = QAction(plugin.name, self)
            action.setWhatsThis(plugin.description)
            action.plugin = plugin
            if isinstance(plugin.plugin_object, FilterPlugin):
                self._filter_menu.addAction(action)
            elif isinstance(plugin.plugin_object, ViewPlugin):
                self._view_menu.addAction(action)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_settings()
        return super().closeEvent(event)

    def _remove_view(self, controller: ViewController):
        self.ui.treeWidget.invisibleRootItem().removeChild(controller.tree_item)
        self._open_views.pop(controller.tree_item)

    def _add_view(
        self,
        name: str,
        df: pd.DataFrame,
        x_title: str,
        y_title: str,
        display_markers: bool = False,
        parent: QTreeWidgetItem = None,
    ) -> ViewController:

        controller = ViewController(
            name,
            df,
            display_markers=display_markers,
            parent=self,
        )
        controller.x_axis.setTitleText(x_title)
        controller.y_axis.setTitleText(y_title)

        tree_item = controller.tree_item
        tree_item.setFlags(tree_item.flags() | Qt.ItemIsAutoTristate)

        if parent:
            parent.addChild(tree_item)
        else:
            self.ui.treeWidget.addTopLevelItem(tree_item)

        for series in controller.chart.series():
            series_item = QTreeWidgetItem(tree_item)
            series_item.setText(0, series.name())
            series_item.setCheckState(0, Qt.Checked)
            series_item.series = series

        if len(controller.chart.series()) > 1:
            tree_item.setExpanded(True)
        else:
            controller.chart.legend().setVisible(False)

        self.ui.stackedWidget.addWidget(controller.chart_view)
        self._open_views[tree_item] = controller

        self.ui.treeWidget.setCurrentItem(tree_item)

        return controller

    def _add_files(self, files: Iterable[QFileInfo]) -> None:
        # TODO: Make parser dialog accept multiple files at once

        for file in files:
            filename = file.absoluteFilePath()
            if file.suffix().lower() == "ide":
                df: pd.DataFrame = ed.ide.get_primary_sensor_data(
                    name=filename, measurement_type=ed.ide.ACCELERATION
                )
                # Convert index from datetime to timedelta
                series = df.index.to_series()
                df.index = series - series[0]
            else:

                parsers = []
                auto_parsers = []
                for parser in self._parsers:
                    if parser.can_parse(filename):
                        parsers.append(parser)
                        # If the parser doesn't offer any options and has no header row
                        # that means it can parse the file without human input.
                        if not parser.options and parser.header_row is not None:
                            auto_parsers.append(parser)

                df = None
                # Try all of the auto parsers and remove any that fail
                for parser in auto_parsers:
                    try:
                        df = auto_parsers[0].parse(filename)
                    except:
                        parsers.remove(parser)

                # If the auto parser didn't work let's resort to the dialog
                if df is None:
                    dlg = ParserDialog(filename, parsers, parent=self)
                    df = dlg.exec()

                if df is None:
                    continue

            self._add_view(file.fileName(), df, df.index.name, "Acceleration (g's)")

    def _get_supported_files(self, event: QDropEvent) -> List[QFileInfo]:
        files = []
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            for url in mimeData.urls():
                if url.isLocalFile():
                    info = QFileInfo(url.toLocalFile())
                    if info.suffix().lower() in self.supported_extensions:
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

        controller = self._get_controller_from_tree_item(item)
        if controller is None:
            return

        df = controller.df

        menu = QMenu(self)

        crop_action = QAction("Crop")
        menu.addAction(crop_action)
        export_action = QAction("Export")
        menu.addAction(export_action)

        actions = self._filter_menu.actions() + self._view_menu.actions()
        # Plugins can specify supported index types.
        # Disable plugins that can't process the current dataframe
        for action in actions:
            plugin = action.plugin.plugin_object
            action.setEnabled(plugin.can_process(df))

        if self._filter_menu.actions():
            menu.addMenu(self._filter_menu)

        if self._view_menu.actions():
            menu.addMenu(self._view_menu)

        action = menu.exec(QCursor.pos())
        if not action:
            return

        if action is crop_action:
            controller.crop()
        elif action is export_action:
            suggested_name = item.text(0).split(".")[0]
            fileName, filter = QFileDialog.getSaveFileName(
                self, "Export File", suggested_name, "CSV (*.csv)"
            )
            if fileName:
                if "csv" in filter:
                    df.to_csv(fileName)
        else:
            params = {}
            plugin = action.plugin.plugin_object
            options = plugin.options
            if options:
                dlg = OptionsDialog(options, self)
                if dlg.exec() == OptionsDialog.Rejected:
                    return
                params = dlg.values

            new_df = plugin.process(df, **params)

            if isinstance(plugin, FilterPlugin):
                controller.set_df(new_df, action.plugin.name)
            elif isinstance(plugin, ViewPlugin):
                name = action.plugin.name
                self._add_view(
                    f"{name} - {item.text(0)}",
                    new_df,
                    plugin.x_title,
                    plugin.y_title,
                    parent=item,
                )

    def _fit_to_contents(self) -> None:
        item = self.ui.treeWidget.currentItem()
        controller = self._get_controller_from_tree_item(item)
        if controller:
            controller.fit_contents()

    def _update_markers(self) -> None:
        item = self.ui.treeWidget.currentItem()
        controller = self._get_controller_from_tree_item(item)
        if controller:
            controller.display_markers = self.ui.marker_group.isChecked()
            controller.marker_size = self.ui.markerSize_spin.value()

    def _update_chart_ranges(self) -> None:
        item = self.ui.treeWidget.currentItem()
        controller = self._get_controller_from_tree_item(item)
        if controller:
            controller.setAxisRanges(
                self.ui.xMin_spin.value(),
                self.ui.xMax_spin.value(),
                self.ui.yMin_spin.value(),
                self.ui.yMax_spin.value(),
            )

    def _update_tick_counts(self) -> None:
        item = self.ui.treeWidget.currentItem()
        controller = self._get_controller_from_tree_item(item)
        if controller:
            controller.x_axis.setMinorTickCount(self.ui.xMinorTicks_spin.value())
            controller.x_axis.setTickCount(self.ui.xMajorTicks_spin.value())
            controller.y_axis.setMinorTickCount(self.ui.yMinorTicks_spin.value())
            controller.y_axis.setTickCount(self.ui.yMajorTicks_spin.value())

    def _set_value_silent(self, spin_box: QSpinBox, value: float) -> None:
        if not spin_box.hasFocus():
            blocked = spin_box.blockSignals(True)
            spin_box.setValue(value)
            spin_box.blockSignals(blocked)

    def _update_chart_settings(self) -> None:
        item = self.ui.treeWidget.currentItem()
        controller = self._get_controller_from_tree_item(item)
        if controller:
            x_axis = controller.x_axis
            y_axis = controller.y_axis

            self._set_value_silent(self.ui.xMin_spin, x_axis.min())
            self._set_value_silent(self.ui.xMax_spin, x_axis.max())
            self._set_value_silent(self.ui.xMinorTicks_spin, x_axis.minorTickCount())
            self._set_value_silent(self.ui.xMajorTicks_spin, x_axis.tickCount())

            self._set_value_silent(self.ui.yMin_spin, y_axis.min())
            self._set_value_silent(self.ui.yMax_spin, y_axis.max())
            self._set_value_silent(self.ui.yMinorTicks_spin, y_axis.minorTickCount())
            self._set_value_silent(self.ui.yMajorTicks_spin, y_axis.tickCount())

            self._set_value_silent(self.ui.markerSize_spin, controller.marker_size)
            self.ui.marker_group.setChecked(controller.display_markers)

    def _current_tree_item_changed(
        self, current: QTreeWidgetItem, previous: QTreeWidgetItem = None
    ) -> None:

        if previous:
            pass
            controller = self._get_controller_from_tree_item(previous)
            x_axis = controller.x_axis
            y_axis = controller.y_axis
            x_axis.disconnect(self)
            y_axis.disconnect(self)

        self.ui.chartSettingsDockWidget.setEnabled((current != None))
        controller = self._get_controller_from_tree_item(current)
        if controller:
            self._update_chart_settings()
            x_axis = controller.x_axis
            y_axis = controller.y_axis

            x_axis.rangeChanged.connect(self._update_chart_settings)
            x_axis.tickCountChanged.connect(self._update_chart_settings)
            x_axis.minorTickCountChanged.connect(self._update_chart_settings)

            y_axis.rangeChanged.connect(self._update_chart_settings)
            y_axis.tickCountChanged.connect(self._update_chart_settings)
            y_axis.minorTickCountChanged.connect(self._update_chart_settings)

            self.ui.stackedWidget.setCurrentWidget(controller.chart_view)
            self.ui.undoView.setStack(controller.undo_stack)

    def _tree_item_changed(self, item: QTreeWidgetItem, column: int):
        if column == 0 and hasattr(item, "series"):
            item.series.setVisible(item.checkState(0) == Qt.Checked)

    def _get_root_parent(self, item):
        while item and item.parent() is not None:
            item = item.parent()
        return item

    def _get_controller_from_tree_item(self, item: QTreeWidgetItem) -> ViewController:
        if item not in self._open_views:
            item = self._get_root_parent(item)

        if item:
            return self._open_views.get(item)
        return None
