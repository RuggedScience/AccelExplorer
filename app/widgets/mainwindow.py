from collections.abc import Iterable
from typing import List

import endaq as ed
import pandas as pd
from PySide6.QtCore import QFileInfo, QSettings, Qt, QTimer, QObject
from PySide6.QtGui import (
    QCloseEvent,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QAction,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QSpinBox,
    QColorDialog,
)
from yapsy.PluginManager import PluginManager, PluginManagerSingleton

from app.plugins.dataframeplugins import (
    DataFramePlugin,
    ViewPlugin,
    FilterPlugin,
    SRSPlugin,
    FFTPlugin,
)
from app.plugins.options import BoolOption
from app.plugins.parserplugins import CSVParser
from app.ui.ui_mainwindow import Ui_MainWindow
from app.utils import timing, SignalBlocker
from app.viewcontroller import ViewController, ViewSeries
from app.widgets.optionsdialog import OptionsDialog
from app.widgets.parserdialog import ParserDialog


class DataframePluginAction(QAction):
    def __init__(
        self, plugin: DataFramePlugin, description: str = None, parent: QObject = None
    ):
        super().__init__(plugin.name, parent)
        self.setToolTip(description)
        self._plugin = plugin

    @property
    def plugin(self) -> DataFramePlugin:
        return self._plugin


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle(
            f"{QApplication.applicationName()} {QApplication.applicationVersion()}[*]"
        )

        self._connect_signals()
        self._load_plugins()
        self._load_settings()

        self.ui.menuView.addAction(self.ui.viewsDockWidget.toggleViewAction())
        self.ui.menuView.addAction(self.ui.chartSettingsDockWidget.toggleViewAction())
        self.ui.menuView.addAction(self.ui.undoDockWidget.toggleViewAction())

        self.ui.menuFilters.setEnabled(not self.ui.menuFilters.isEmpty())
        self.ui.menuViews.setEnabled(not self.ui.menuViews.isEmpty())

    @property
    def supported_extensions(self) -> List[str]:
        exts = ["ide"]
        for parser in self._parsers:
            exts += [ext.lower() for ext in parser.supported_extensions()]

        return list(set(exts))

    def _connect_signals(self) -> None:
        # Views tree widget
        self.ui.treeWidget.currentViewChanged.connect(self._current_view_changed)
        self.ui.treeWidget.viewSelectionChanged.connect(self._selection_changed)
        self.ui.treeWidget.seriesHovered.connect(self._handle_series_hovered)
        # Chart X-Axis Ranges
        self.ui.xMin_spin.valueChanged.connect(self._update_chart_ranges)
        self.ui.xMax_spin.valueChanged.connect(self._update_chart_ranges)
        # Chart X-Axis Tick Marks
        self.ui.xMinorTicks_spin.valueChanged.connect(self._update_tick_counts)
        self.ui.xMajorTicks_spin.valueChanged.connect(self._update_tick_counts)
        # Chart Y-Axis Ranges
        self.ui.yMin_spin.valueChanged.connect(self._update_chart_ranges)
        self.ui.yMax_spin.valueChanged.connect(self._update_chart_ranges)
        # Chart Y-Axis Tick Marks
        self.ui.yMinorTicks_spin.valueChanged.connect(self._update_tick_counts)
        self.ui.yMajorTicks_spin.valueChanged.connect(self._update_tick_counts)
        # Series Group
        self.ui.seriesWidth_spin.valueChanged.connect(self._update_series_width)
        self.ui.selectedSeriesWidth_spin.valueChanged.connect(self._update_series_width)
        # Markers
        self.ui.marker_group.clicked.connect(self._update_markers)
        self.ui.markerSize_spin.valueChanged.connect(self._update_markers)
        self.ui.markerCount_spin.valueChanged.connect(self._update_markers)
        # Actions
        self.ui.actionOpen.triggered.connect(self._open_files)
        self.ui.actionFit_Contents.triggered.connect(self._fit_to_contents)
        self.ui.actionClose.triggered.connect(self._close_current_selection)
        self.ui.actionExport.triggered.connect(self._export_current_view)
        self.ui.actionCrop.triggered.connect(self._crop_current_view)

        self.ui.saveDefaults_button.clicked.connect(self._save_chart_settings)

    def _load_settings(self) -> None:
        settings = QSettings()
        self.restoreGeometry(settings.value("geometry"))
        self.restoreState(settings.value("state"))

        self._marker_size = settings.value("marker_size", 10)
        self._marker_count = settings.value("marker_count", 5)

        self._x_minor_ticks = settings.value("x_minor_ticks", 0)
        self._x_major_ticks = settings.value("x_major_ticks", 5)

        self._y_minor_ticks = settings.value("y_minor_ticks", 0)
        self._y_major_ticks = settings.value("y_major_ticks", 5)
        self._series_width = settings.value("series_width", 2)
        self._selected_series_width = settings.value("selected_series_width", 5)

        self.ui.selectedSeriesWidth_spin.setValue(self._selected_series_width)

    def _save_settings(self) -> None:
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())

    def _save_chart_settings(self):
        settings = QSettings()
        settings.setValue("marker_size", self.ui.markerSize_spin.value())
        settings.setValue("marker_count", self.ui.markerCount_spin.value())
        settings.setValue("x_minor_ticks", self.ui.xMinorTicks_spin.value())
        settings.setValue("x_major_ticks", self.ui.xMajorTicks_spin.value())
        settings.setValue("y_minor_ticks", self.ui.yMinorTicks_spin.value())
        settings.setValue("y_major_ticks", self.ui.yMajorTicks_spin.value())
        settings.setValue("series_width", self.ui.seriesWidth_spin.value())
        settings.setValue(
            "selected_series_width", self.ui.selectedSeriesWidth_spin.value()
        )

    def _load_plugins(self) -> None:
        pm: PluginManager = PluginManagerSingleton.get()

        self._parsers: List[CSVParser] = [
            plugin.plugin_object for plugin in pm.getPluginsOfCategory("parsers")
        ]

        actions = [
            DataframePluginAction(SRSPlugin(), "Shock Response Spectrum", self),
            DataframePluginAction(FFTPlugin(), "Fast Fourier Transform", self),
        ]
        actions += [
            DataframePluginAction(plugin.plugin_object, plugin.description, self)
            for plugin in pm.getPluginsOfCategory("dataframe")
        ]

        for action in actions:
            action.setEnabled(False)
            if action.plugin.icon:
                action.setIcon(action.plugin.icon)
            action.triggered.connect(self._plugin_action_triggered)
            if isinstance(action.plugin, ViewPlugin):
                self.ui.menuViews.addAction(action)
            elif isinstance(action.plugin, FilterPlugin):
                self.ui.menuFilters.addAction(action)

            if action.plugin.add_to_toolbar:
                self.ui.toolBar.addAction(action)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_settings()
        return super().closeEvent(event)

    def _add_view(
        self,
        name: str,
        df: pd.DataFrame,
        x_title: str,
        y_title: str,
        display_markers: bool = False,
    ) -> ViewController:
        controller = ViewController(
            name,
            df,
            display_markers=display_markers,
            tree_widget=self.ui.treeWidget,
            parent=self,
        )
        controller.x_axis.setTitleText(x_title)
        controller.y_axis.setTitleText(y_title)

        tree_item = controller.tree_item
        tree_item.setFlags(tree_item.flags() | Qt.ItemIsAutoTristate)

        if len(controller.chart.series()) > 1:
            tree_item.setExpanded(True)

        self.ui.stackedWidget.addWidget(controller.chart_view)
        self.ui.treeWidget.add_view(controller)
        # self._open_views[tree_item] = controller

        self.ui.treeWidget.setCurrentItem(tree_item)

        self.ui.treeWidget.resizeColumnToContents(0)
        self.ui.treeWidget.resizeColumnToContents(1)

        controller.series_width = self._series_width
        controller.marker_count = self._marker_count
        controller.marker_size = self._marker_size

        controller.x_axis.setTickCount(self._x_major_ticks)
        controller.x_axis.setMinorTickCount(self._x_minor_ticks)
        controller.y_axis.setTickCount(self._y_major_ticks)
        controller.y_axis.setMinorTickCount(self._y_minor_ticks)

        controller.legend_clicked.connect(self._series_legend_clicked)

        return controller

    def _add_file(self, fileinfo: QFileInfo | str, df: pd.DataFrame) -> None:
        if isinstance(fileinfo, str):
            fileinfo = QFileInfo(fileinfo)

        controller = self._add_view(
            fileinfo.fileName(),
            df,
            df.index.name,
            "Acceleration (g's)",
        )
        # Set the original filename in the tooltip
        # in case the user changes the name later.
        tooltip_text = f"File: {fileinfo.fileName()}"
        if df.index.inferred_type == "timedelta64":
            freq = 1 / ed.calc.utils.sample_spacing(df)
            tooltip_text += f"\nFrequency: {freq:.2f}hz"
        controller.tree_item.setToolTip(0, tooltip_text)

    def _add_files(self, files: Iterable[QFileInfo]) -> None:
        unparsed_files = []
        for file in files:
            df = None
            filename = file.absoluteFilePath()
            if file.suffix().lower() == "ide":
                df: pd.DataFrame = ed.ide.get_primary_sensor_data(
                    name=filename, measurement_type=ed.ide.ACCELERATION
                )
                # Convert index from datetime to timedelta
                series = df.index.to_series()
                df.index = series - series[0]
            else:
                df = None
                for parser in self._parsers:
                    try:
                        df = parser.parse(filename)
                        break
                    except Exception as ex:
                        pass

            if df is not None:
                self._add_file(file, df)
            else:
                unparsed_files.append(filename)

        if unparsed_files:
            dfs = ParserDialog(unparsed_files, self).exec()
            if dfs:
                for file, df in dfs.items():
                    self._add_file(file, df)

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
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        # event.acceptProposedAction()
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        files = self._get_supported_files(event)
        if files:
            event.acceptProposedAction()
            QTimer.singleShot(1, lambda: self._add_files(files))
        else:
            super().dropEvent(event)

    def _close_current_selection(self) -> None:
        controllers = self.ui.treeWidget.get_selected_controllers()
        for controller in controllers:
            self.ui.treeWidget.remove_view(controller)
            self.ui.stackedWidget.removeWidget(controller.chart_view)
            controller.deleteLater()

    def _export_current_view(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            item = controller.tree_item
            suggested_name = item.text(0).split(".")[0]
            fileName, filter = QFileDialog.getSaveFileName(
                self, "Export File", suggested_name, "CSV (*.csv)"
            )
            if fileName:
                controller.df.to_csv(fileName)

    def _crop_current_view(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            controller.crop()

    def _fit_to_contents(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            controller.fit_contents()

    def _update_markers(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            controller.display_markers = self.ui.marker_group.isChecked()
            controller.marker_size = self.ui.markerSize_spin.value()
            controller.marker_count = self.ui.markerCount_spin.value()

    def _update_chart_ranges(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            controller.setAxisRanges(
                self.ui.xMin_spin.value(),
                self.ui.xMax_spin.value(),
                self.ui.yMin_spin.value(),
                self.ui.yMax_spin.value(),
            )

    def _update_tick_counts(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            controller.x_axis.setMinorTickCount(self.ui.xMinorTicks_spin.value())
            controller.x_axis.setTickCount(self.ui.xMajorTicks_spin.value())
            controller.y_axis.setMinorTickCount(self.ui.yMinorTicks_spin.value())
            controller.y_axis.setTickCount(self.ui.yMajorTicks_spin.value())

    def _update_series_width(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            for series in controller:
                series.width = self.ui.seriesWidth_spin.value()

    def _handle_series_hovered(
        self, controller: ViewController, current: ViewSeries, previous: ViewSeries
    ) -> None:
        if previous:
            previous.width = self.ui.seriesWidth_spin.value()

        if controller and controller is self.ui.treeWidget.get_current_controller():
            if current:
                current.width = self.ui.selectedSeriesWidth_spin.value()

    def _set_value_silent(self, spin_box: QSpinBox, value: float) -> None:
        if not spin_box.hasFocus():
            with SignalBlocker(spin_box):
                spin_box.setValue(value)

    def _update_chart_settings(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            # X-Axis group
            x_axis = controller.x_axis
            self._set_value_silent(self.ui.xMin_spin, x_axis.min())
            self._set_value_silent(self.ui.xMax_spin, x_axis.max())
            self._set_value_silent(self.ui.xMinorTicks_spin, x_axis.minorTickCount())
            self._set_value_silent(self.ui.xMajorTicks_spin, x_axis.tickCount())
            # Y-Axis group
            y_axis = controller.y_axis
            self._set_value_silent(self.ui.yMin_spin, y_axis.min())
            self._set_value_silent(self.ui.yMax_spin, y_axis.max())
            self._set_value_silent(self.ui.yMinorTicks_spin, y_axis.minorTickCount())
            self._set_value_silent(self.ui.yMajorTicks_spin, y_axis.tickCount())
            # Series group
            self._set_value_silent(self.ui.seriesWidth_spin, controller.series_width)
            # Marker group
            self._set_value_silent(self.ui.markerSize_spin, controller.marker_size)
            self._set_value_silent(self.ui.markerCount_spin, controller.marker_count)
            self.ui.marker_group.setChecked(controller.display_markers)

    def _current_view_changed(
        self,
        current: ViewController,
        previous: ViewController = None,
    ) -> None:

        if previous:
            x_axis = previous.x_axis
            y_axis = previous.y_axis
            x_axis.disconnect(self)
            y_axis.disconnect(self)

        self.ui.chartSettingsWidget.setEnabled((current != None))

        if current:
            self._update_chart_settings()
            x_axis = current.x_axis
            y_axis = current.y_axis

            x_axis.rangeChanged.connect(self._update_chart_settings)
            x_axis.tickCountChanged.connect(self._update_chart_settings)
            x_axis.minorTickCountChanged.connect(self._update_chart_settings)

            y_axis.rangeChanged.connect(self._update_chart_settings)
            y_axis.tickCountChanged.connect(self._update_chart_settings)
            y_axis.minorTickCountChanged.connect(self._update_chart_settings)

            self.ui.stackedWidget.setCurrentWidget(current.chart_view)
            self.ui.undoView.setStack(current.undo_stack)

            for action in self.ui.menuViews.actions():
                if isinstance(action, DataframePluginAction):
                    action.setEnabled(action.plugin.can_process(current.df))

            for action in self.ui.menuFilters.actions():
                if isinstance(action, DataframePluginAction):
                    action.setEnabled(action.plugin.can_process(current.df))

        enable = current is not None
        self.ui.actionFit_Contents.setEnabled(enable)
        self.ui.actionClose.setEnabled(enable)
        self.ui.actionExport.setEnabled(enable)
        self.ui.actionCrop.setEnabled(enable)
        self.ui.menuData.setEnabled(enable)

    def _selection_changed(self, controllers: List[ViewController]) -> None:
        enable = bool(controllers)
        for controller in controllers:
            if controller.df.index.inferred_type != "timedelta64":
                enable = False
                break

    def _series_legend_clicked(self, series: ViewSeries):
        sender = self.sender()
        if isinstance(sender, ViewController):
            color = QColorDialog.getColor(series.color, self)
            if color.isValid():
                sender.set_series_color(series, color)

    def _open_files(self) -> None:
        filters = "Data files ("
        for ext in self.supported_extensions:
            filters += f"*.{ext} "
        filters = filters.strip() + ")"

        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", filters)
        if files:
            self._add_files([QFileInfo(filename) for filename in files])

    def _view_plugin_triggered(self, plugin: ViewPlugin) -> None:
        controllers = self.ui.treeWidget.get_selected_controllers()

        options = plugin.options
        # View plugins support being combined if we have selected more than one controller
        if len(controllers) > 1:
            options["combine"] = BoolOption("Combine", True)

        values = OptionsDialog(options, self).exec()
        if values:
            combine = values.pop("combine", False)
            dfs = {}
            for controller in controllers:
                df = plugin.process(controller.df, **values)
                if combine:
                    df = df.add_suffix(f" - {controller.name}")
                    if not dfs:
                        dfs[plugin.name] = df
                    else:
                        dfs[plugin.name] = pd.concat(
                            [dfs[plugin.name], df], axis="columns"
                        )
                else:
                    dfs[f"{plugin.name} - {controller.name}"] = df

            for name, df in dfs.items():
                self._add_view(
                    name, df, plugin.x_title, plugin.y_title, plugin.display_markers
                )

    def _filter_plugin_triggered(self, plugin: FilterPlugin) -> None:
        controllers = self.ui.treeWidget.get_selected_controllers()
        if controllers:
            values = OptionsDialog(plugin.options, self).exec()
            if values:
                for controller in controllers:
                    filtered_df = plugin.process(controller.df, **values)
                    controller.set_df(filtered_df, plugin.name)

    def _plugin_action_triggered(self) -> None:
        sender = self.sender()

        if isinstance(sender, DataframePluginAction):
            if isinstance(sender.plugin, ViewPlugin):
                self._view_plugin_triggered(sender.plugin)
            elif isinstance(sender.plugin, FilterPlugin):
                self._filter_plugin_triggered(sender.plugin)
