from __future__ import annotations

import dataclasses
import json
import logging
import os
from pathlib import Path
from collections.abc import Iterable
from io import TextIOWrapper

import pandas as pd
from PySide6.QtCore import QObject, QSettings, QTimer
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QFileDialog,
    QMainWindow,
    QDoubleSpinBox,
    QSpinBox,
)
from yapsy.PluginManager import PluginManager

from app.plugins.viewmodelplugin import (
    ViewModelPlugin,
    FilterPlugin,
    ViewPlugin,
)
from app.plugins.options import BoolOption, ListOption
from app.plugins.parserplugins import ParserPlugin, ParseError
from app.ui.ui_mainwindow import Ui_MainWindow
from app.utils import SignalBlocker, timing, get_plugin_path
from app.views import ViewModel, ViewController, ViewSeries
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

        self._connect_signals()
        self._load_plugins()
        self._load_settings()

        self.ui.menuView.addAction(self.ui.viewsDockWidget.toggleViewAction())
        self.ui.menuView.addAction(self.ui.chartSettingsDockWidget.toggleViewAction())
        self.ui.menuView.addAction(self.ui.undoDockWidget.toggleViewAction())

        self.ui.menuFilters.setEnabled(not self.ui.menuFilters.isEmpty())
        self.ui.menuViews.setEnabled(not self.ui.menuViews.isEmpty())

    @property
    def supported_extensions(self) -> list[str]:
        exts = []
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
        self.ui.actionNew_View.triggered.connect(self._new_view)
        self.ui.actionOpen.triggered.connect(self._open_files)
        self.ui.actionFit_Contents.triggered.connect(self._fit_to_contents)
        self.ui.actionClose.triggered.connect(self._close_current_selection)
        self.ui.actionExport.triggered.connect(self._export_current_view)
        self.ui.actionCrop.triggered.connect(self._crop_current_view)
        self.ui.actionUndo.triggered.connect(self._undo)
        self.ui.actionRedo.triggered.connect(self._redo)

        self.ui.saveDefaults_button.clicked.connect(self._save_chart_settings)

    def _load_settings(self) -> None:
        settings = QSettings()
        self.restoreGeometry(settings.value("geometry"))
        self.restoreState(settings.value("state"))

        self._marker_size = int(settings.value("marker_size", 10)) #type: ignore
        self._marker_count = int(settings.value("marker_count", 5)) #type: ignore

        self._x_minor_ticks = int(settings.value("x_minor_ticks", 0)) #type: ignore
        self._x_major_ticks = int(settings.value("x_major_ticks", 5)) #type: ignore

        self._y_minor_ticks = int(settings.value("y_minor_ticks", 0)) #type: ignore
        self._y_major_ticks = int(settings.value("y_major_ticks", 5)) #type: ignore
        self._series_width = int(settings.value("series_width", 2)) #type: ignore
        self._selected_series_width = int(settings.value("selected_series_width", 5))  # type: ignore

        self.ui.selectedSeriesWidth_spin.setValue(self._selected_series_width)

        self._last_directory = str(settings.value("last_directory", ""))

    def _save_settings(self) -> None:
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())
        settings.setValue("last_directory", self._last_directory)

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
        plugin_path = get_plugin_path()
        pm = PluginManager()
        pm.setPluginInfoExtension("plugin")
        pm.setPluginPlaces(
            [
                os.path.join(plugin_path, "parsers"),
                os.path.join(plugin_path, "filters"),
                os.path.join(plugin_path, "views"),
            ]
        )
        pm.setCategoriesFilter({"parsers": ParserPlugin, "dataframe": ViewModelPlugin})
        pm.collectPlugins()

        self._parsers: list[ParserPlugin] = [
            plugin.plugin_object for plugin in pm.getPluginsOfCategory("parsers")
        ]

        for plugin in pm.getPluginsOfCategory("dataframe"):
            action = DataframePluginAction(
                plugin.plugin_object, plugin.description, self
            )
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
        model: ViewModel,
        display_markers: bool = False,
    ) -> ViewController:
        controller = ViewController(
            name,
            model,
            display_markers=display_markers,
            item_parent=self.ui.treeWidget,
            parent=self,
        )

        tree_item = controller.tree_item

        if len(controller.chart.series()) > 1:
            tree_item.setExpanded(True)

        self.ui.stackedWidget.addWidget(controller.chart_view)
        self.ui.treeWidget.add_view(controller)

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

    def _add_file(self, file: Path, model: ViewModel) -> ViewController:
        controller = self._add_view(file.name, model)
        # Set the original filename in the tooltip
        # in case the user changes the name later.
        controller.add_tooltips(f"File: {file.name}")
        return controller

    def _add_files(self, files: Iterable[Path]) -> None:
        unparsed_files = []
        for file in files:
            model = None
            extension = get_ext(file)
            if not self._parse_exported_file(file):
                for parser in self._parsers:
                    if extension in parser.supported_extensions():
                        try:
                            model = parser.parse(file)
                            break
                        except ParseError:
                            pass
                        except Exception:
                            logging.exception(__name__)

                if model is not None:
                    self._add_file(file, model)
                elif extension == "csv":
                    unparsed_files.append(file)

        if unparsed_files:
            models = ParserDialog(unparsed_files, self).exec()
            if models:
                for file, model in models.items():
                    self._add_file(file, model)

    def _get_supported_files(self, event: QDropEvent) -> list[Path]:
        files = []
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            for url in mimeData.urls():
                if url.isLocalFile():
                    file = Path(url.toLocalFile())
                    if get_ext(file) in self.supported_extensions:
                        files.append(file)
        return files

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        files = self._get_supported_files(event)
        if files:
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        files = self._get_supported_files(event)
        if files:
            event.acceptProposedAction()
            QTimer.singleShot(1, lambda: self._add_files(files))
        else:
            super().dropEvent(event)

    def _close_view(self, controller: ViewController) -> None:
        self.ui.treeWidget.remove_view(controller)
        self.ui.stackedWidget.removeWidget(controller.chart_view)
        controller.deleteLater()

    def _close_current_selection(self) -> None:
        controllers = self.ui.treeWidget.get_selected_controllers()
        # If there is no selection, close the current view
        if not controllers:
            current_controller = self.ui.treeWidget.get_current_controller()
            if current_controller is not None:
                self._close_view(current_controller)
        else:
            for controller in controllers:
                # If the root tree item is selected just close the entire view
                if controller.tree_item.isSelected():
                    self._close_view(controller)
                # If not, close only the selected series
                else:
                    # Created a list of series that aren't selected.
                    # This is the list of columns to keep.
                    cols = [
                        series.name
                        for series in controller
                        if not series.tree_item.isSelected()
                    ]
                    # If we aren't keeping any columns, just close the view
                    if not cols:
                        self._close_view(controller)
                    # Else if we aren't keeping all of the columns
                    # create a new model with those columns.
                    elif len(cols) != len(controller):
                        new_model = controller.model[cols]
                        controller.set_model(new_model, title="Removed series") #type: ignore

    def _export_current_view(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            item = controller.tree_item
            suggested_name = item.text(0).split(".")[0]
            if self._last_directory:
                suggested_name = os.path.join(self._last_directory, suggested_name)
            filename, filter = QFileDialog.getSaveFileName(
                self, "Export File", suggested_name, "CSV (*.csv)"
            )
            if filename:
                self._last_directory = os.path.dirname(filename)
                with open(filename, "w") as f:
                    metadata = ViewMetaData.from_controller(controller)
                    metadata.to_file(f)
                    controller.df.to_csv(f)

    def _crop_current_view(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            controller.crop()

    def _fit_to_contents(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller:
            controller.fit_contents()

    def _undo(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller is not None and controller.undo_stack.canUndo():
            controller.undo_stack.undo()

    def _redo(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        if controller is not None and controller.undo_stack.canRedo():
            controller.undo_stack.redo()

    def _update_undo_actions(self) -> None:
        controller = self.ui.treeWidget.get_current_controller()
        self.ui.actionUndo.setEnabled(
            bool(controller is not None and controller.undo_stack.canUndo())
        )
        self.ui.actionRedo.setEnabled(
            bool(controller is not None and controller.undo_stack.canRedo())
        )

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
            controller.series_width = self.ui.seriesWidth_spin.value()

    def _handle_series_hovered(self, current: ViewSeries, previous: ViewSeries) -> None:
        if previous:
            previous.width = previous.controller.series_width

        if current:
            current.width = self.ui.selectedSeriesWidth_spin.value()

    def _set_value_silent(self, spin_box: QSpinBox | QDoubleSpinBox, value: float | int) -> None:
        if not spin_box.hasFocus():
            with SignalBlocker(spin_box):
                spin_box.setValue(value) #type: ignore

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
        previous: ViewController | None = None,
    ) -> None:
        if previous is not None:
            x_axis = previous.x_axis
            y_axis = previous.y_axis
            x_axis.disconnect(self)
            y_axis.disconnect(self)
            previous.undo_stack.disconnect(self)

        self.ui.chartSettingsWidget.setEnabled((current != None))

        if current is not None:
            self._update_chart_settings()
            x_axis = current.x_axis
            y_axis = current.y_axis

            x_axis.rangeChanged.connect(self._update_chart_settings)
            x_axis.tickCountChanged.connect(self._update_chart_settings)
            x_axis.minorTickCountChanged.connect(self._update_chart_settings)

            y_axis.rangeChanged.connect(self._update_chart_settings)
            y_axis.tickCountChanged.connect(self._update_chart_settings)
            y_axis.minorTickCountChanged.connect(self._update_chart_settings)

            current.undo_stack.canUndoChanged.connect(self._update_undo_actions)
            current.undo_stack.canRedoChanged.connect(self._update_undo_actions)

            self.ui.stackedWidget.setCurrentWidget(current.chart_view)
            self.ui.undoView.setStack(current.undo_stack)

        enable = current is not None
        self.ui.actionFit_Contents.setEnabled(enable)
        self.ui.actionClose.setEnabled(enable)
        self.ui.actionExport.setEnabled(enable)
        self.ui.actionCrop.setEnabled(enable)
        self.ui.menuData.setEnabled(enable)

        self._update_undo_actions()

    def _selection_changed(self, controllers: list[ViewController]) -> None:
        actions = self.ui.menuViews.actions() + self.ui.menuFilters.actions()
        for action in actions:
            if isinstance(action, DataframePluginAction):
                can_process = bool(controllers)
                for controller in controllers:
                    if not action.plugin.can_process(controller.model):
                        can_process = False
                        break
                action.setEnabled(can_process)

    def _series_legend_clicked(self, series: ViewSeries):
        sender = self.sender()
        if isinstance(sender, ViewController):
            color = QColorDialog.getColor(series.color, self)
            if color.isValid():
                series.color = color

    def _new_view(self) -> None:
        model = ViewModel()
        controller = self._add_view("New View", model)

    def _open_files(self) -> None:
        filters = "Data files ("
        for ext in self.supported_extensions:
            filters += f"*.{ext} "
        filters = filters.strip() + ")"

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            self._last_directory,
            filters,
        )
        if files:
            self._last_directory = os.path.dirname(files[0])
            self._add_files([Path(filename) for filename in files])

    def _view_plugin_triggered(self, plugin: ViewPlugin) -> None:
        controllers = self.ui.treeWidget.get_selected_controllers()

        options = plugin.options
        # View plugins support being combined if we have selected more than one controller
        if len(controllers) > 1:
            options["combine"] = BoolOption("Combine", True)

        if options:
            values = OptionsDialog(options, self).exec()
            if not values:
                return
        else:
            values = {}

        new_controllers: list[ViewController] = []
        combine = values.pop("combine", False)
        if combine:
            combined_model = ViewModel()
            for controller in controllers:
                model = plugin.process(controller.model, **values)
                model.add_suffix(f" - {controller.name}")
                combined_model.merge(model)

            controller = self._add_view(
                plugin.name,
                combined_model,
                plugin.display_markers,
            )

            new_controllers.append(controller)
        else:
            for controller in controllers:
                model = plugin.process(controller.model, **values)
                new_controller = self._add_view(
                    f"{plugin.name} - {controller.name}",
                    model,
                    plugin.display_markers,
                )

                for series in new_controller:
                    if series.name in controller:
                        series.color = controller[series.name].color

                new_controllers.append(new_controller)

        tooltips = []
        for key, option in options.items():
            if key in values:
                value = values[key]
                if isinstance(option, ListOption):
                    value = option.value_to_name(value)
                tooltips.append(f"{option.name}: {value}")

        for controller in new_controllers:
            controller.add_tooltips(tooltips)

    def _filter_plugin_triggered(self, plugin: FilterPlugin) -> None:
        controllers = self.ui.treeWidget.get_selected_controllers()
        if controllers:
            options = plugin.options
            if options:
                values = OptionsDialog(options, self).exec()
                if not values:
                    return
            else:
                values = {}

            for controller in controllers:
                model = plugin.process(controller.model, **values)
                title = f"{plugin.name} ("
                for key, option in options.items():
                    if key in values:
                        value = values[key]
                        if isinstance(option, ListOption):
                            value = option.value_to_name(value)
                        title += f" {option.name}: {value},"

                # Remove trailing comma
                title = title[:-1]
                title += ")"
                controller.set_model(model, title=title) #type: ignore

    def _plugin_action_triggered(self) -> None:
        sender = self.sender()

        if isinstance(sender, DataframePluginAction):
            if isinstance(sender.plugin, ViewPlugin):
                self._view_plugin_triggered(sender.plugin)
            elif isinstance(sender.plugin, FilterPlugin):
                self._filter_plugin_triggered(sender.plugin)

    def _parse_exported_file(self, file: Path) -> bool:
        if get_ext(file) != "csv":
            return False

        try:
            with file.open("r") as f:
                metadata = ViewMetaData.from_file(f)
                if metadata:
                    parse_dates = bool(metadata.index_type == "timedelta64")
                    df = pd.read_csv(f, index_col=metadata.index_name)

                    if parse_dates:
                        df.index = pd.to_timedelta(df.index, unit=None)

                    model = ViewModel(df, y_axis=metadata.y_title)
                    controller = self._add_file(file, model)
                    metadata.to_controller(controller)
                    return True
        # If we couldn't parse it just return False
        # so the parser dialog will handle it.
        except Exception:
            logging.exception(__name__)
        return False


class DataframePluginAction(QAction):
    def __init__(
        self, plugin: ViewModelPlugin, description: str = "", parent: QObject | None = None
    ):
        super().__init__(plugin.name, parent)
        self.setToolTip(description)
        self._plugin = plugin

    @property
    def plugin(self) -> ViewModelPlugin:
        return self._plugin


@dataclasses.dataclass
class ViewMetaData:
    start_string = "#AccelExplorer MetaData\n"
    end_string = "#End AccelExplorer Metadata\n"

    name: str
    index_name: str
    index_type: str

    x_title: str
    x_major_ticks: int
    x_minor_ticks: int

    y_title: str
    y_major_ticks: int
    y_minor_ticks: int

    series_width: int

    display_markers: bool
    marker_size: int
    marker_count: int

    series: dict[str, dict]

    def to_controller(self, controller: ViewController) -> None:
        controller.set_name(self.name, undo=False) #type: ignore
        controller.x_axis.setTitleText(self.x_title)
        controller.x_axis.setMinorTickCount(self.x_minor_ticks)
        controller.x_axis.setTickCount(self.x_major_ticks)
        controller.y_axis.setTitleText(self.y_title)
        controller.y_axis.setMinorTickCount(self.y_minor_ticks)
        controller.y_axis.setTickCount(self.y_major_ticks)
        controller.series_width = self.series_width
        controller.marker_count = self.marker_count
        controller.marker_size = self.marker_size
        controller.display_markers = self.display_markers
        for series, data in self.series.items():
            if series in controller:
                controller[series].color = data["color"]
                controller[series].marker_shape = data["shape"]

    def to_file(self, file: TextIOWrapper) -> None:
        file.write(self.start_string)
        json.dump(dataclasses.asdict(self), file)
        file.write("\n")
        file.write(self.end_string)

    @classmethod
    def from_controller(cls, controller: ViewController) -> "ViewMetaData":
        kwargs = {
            "name": controller.name,
            "index_name": controller.df.index.name,
            "index_type": controller.df.index.inferred_type,
            "x_title": controller.x_axis.titleText(),
            "x_minor_ticks": controller.x_axis.minorTickCount(),
            "x_major_ticks": controller.x_axis.tickCount(),
            "y_title": controller.y_axis.titleText(),
            "y_minor_ticks": controller.y_axis.minorTickCount(),
            "y_major_ticks": controller.y_axis.tickCount(),
            "series_width": controller.series_width,
            "display_markers": controller.display_markers,
            "marker_size": controller.marker_size,
            "marker_count": controller.marker_count,
            "series": {
                series.name: {
                    "color": series.color.name(),
                    "shape": series.marker_shape.value if series.marker_shape else None,
                }
                for series in controller
            },
        }
        return cls(**kwargs)

    @classmethod
    def from_file(cls, file: TextIOWrapper) -> ViewMetaData | None:
        data = ""
        for i, line in enumerate(file):
            if i == 0:
                if line == cls.start_string:
                    continue
                else:
                    return None
            elif line == cls.end_string:
                break

            data += line

        kwargs = json.loads(data)
        return cls(**kwargs)


def get_ext(file: Path) -> str:
    ext = file.suffix.lower()
    # Drop the "." off the extension name
    if ext:
        ext = ext[1:]
    return ext
