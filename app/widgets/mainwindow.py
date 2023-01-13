from collections.abc import Iterable
from typing import Dict, List

import endaq as ed
import pandas as pd
from PySide6.QtCore import QFileInfo, QSettings, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
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
from app.plugins.parserplugins import CSVParser
from app.plugins.options import NumericOption
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

        self._open_views: Dict[QTreeWidgetItem, ViewController] = {}

        self._connect_signals()
        self._load_plugins()
        self._load_settings()

    @property
    def supported_extensions(self) -> List[str]:
        exts = ["ide"]
        for parser in self._parsers:
            exts += [ext.lower() for ext in parser.supported_extensions()]

        return exts

    def _connect_signals(self) -> None:
        # Views tree widget
        self.ui.treeWidget.currentItemChanged.connect(self._current_tree_item_changed)
        self.ui.treeWidget.itemChanged.connect(self._tree_item_changed)
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
        # Markers
        self.ui.marker_group.clicked.connect(self._update_markers)
        self.ui.markerSize_spin.valueChanged.connect(self._update_markers)
        self.ui.markerCount_spin.valueChanged.connect(self._update_markers)
        # Chart Fit to contents
        self.ui.fitToContents_button.clicked.connect(self._fit_to_contents)
        # Actions
        self.ui.actionClose.triggered.connect(self._close_current_view)
        self.ui.actionExport.triggered.connect(self._export_current_view)
        self.ui.actionCrop.triggered.connect(self._crop_current_view)
        self.ui.actionFFT.triggered.connect(self._fft_current_view)
        self.ui.actionSRS.triggered.connect(self._srs_current_view)

    def _load_settings(self) -> None:
        settings = QSettings()
        self.restoreGeometry(settings.value("geometry"))
        self.restoreState(settings.value("state"))

    def _save_settings(self) -> None:
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())

    def _load_plugins(self) -> None:
        pm: PluginManager = PluginManagerSingleton.get()

        self._parsers: List[CSVParser] = [
            plugin.plugin_object for plugin in pm.getPluginsOfCategory("parsers")
        ]

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
                df = None
                for parser in self._parsers:
                    try:
                        df = parser.parse(filename)
                        break
                    except Exception as ex:
                        pass

                # If we couldn't auto parse, resort to the dialog
                if df is None:
                    dlg = ParserDialog(filename, parent=self)
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

    def _close_current_view(self) -> None:
        controller = self._get_current_controller()
        if controller:
            item = controller.tree_item
            next_item = self.ui.treeWidget.itemAbove(item)
            next_item = self._get_root_parent(next_item)
            self.ui.treeWidget.invisibleRootItem().removeChild(item)

            if self.ui.treeWidget.currentItem() is None:
                self.ui.treeWidget.setCurrentItem(next_item)

            self._open_views.pop(item)
            self.ui.stackedWidget.removeWidget(controller.chart_view)

    def _export_current_view(self) -> None:
        item = self.ui.treeWidget.currentItem()
        controller = self._get_controller_from_tree_item(item)
        if controller:
            suggested_name = item.text(0).split(".")[0]
            fileName, _ = QFileDialog.getSaveFileName(
                self, "Export File", suggested_name, "CSV (*.csv)"
            )
            if fileName:
                controller.df.to_csv(fileName)

    def _crop_current_view(self) -> None:
        controller = self._get_current_controller()
        if controller:
            controller.crop()

    def _fit_to_contents(self) -> None:
        controller = self._get_current_controller()
        if controller:
            controller.fit_contents()

    def _fft_current_view(self) -> None:
        controller = self._get_current_controller()
        if controller:
            options = {
                "min_freq": NumericOption("Min Freq", 10, 1, None),
                "max_freq": NumericOption("Max Freq", 1000, 1, None),
            }
            dlg = OptionsDialog(options)
            if dlg.exec():
                values = dlg.values
                min_x = values.get("min_freq", 10)
                max_x = values.get("max_freq", 1000)

                fft: pd.DataFrame = ed.calc.fft.fft(controller.df)
                fft = fft[(fft.index >= min_x) & (fft.index <= max_x)]
                self._add_view(
                    f"FFT - {controller.name}",
                    fft,
                    "Frequency (Hz)",
                    "Magnitude",
                )

    def _srs_current_view(self) -> None:
        controller = self._get_current_controller()
        if controller:
            options = {
                "min_freq": NumericOption("Min Freq", 10, 1, None),
                "max_freq": NumericOption("Max Freq", 1000, 1, None),
                "dampening": NumericOption("Dampening", 5, 0, 100),
            }
            dlg = OptionsDialog(options)
            if dlg.exec():
                values = dlg.values
                min_x = values.get("min_freq", 10)
                max_x = values.get("max_freq", 1000)
                dampening = values.get("dampening", 5) / 100
                srs: pd.DataFrame = ed.calc.shock.shock_spectrum(
                    controller.df,
                    damp=dampening,
                    init_freq=min_x,
                    mode="srs",
                )

                srs = srs[srs.index <= max_x]
                self._add_view(
                    f"FFT - {controller.name}",
                    srs,
                    "Frequency (Hz)",
                    "Magnitude",
                )

    def _update_markers(self) -> None:
        controller = self._get_current_controller()
        if controller:
            controller.display_markers = self.ui.marker_group.isChecked()
            controller.marker_size = self.ui.markerSize_spin.value()
            controller.marker_count = self.ui.markerCount_spin.value()

    def _update_chart_ranges(self) -> None:
        controller = self._get_current_controller()
        if controller:
            controller.setAxisRanges(
                self.ui.xMin_spin.value(),
                self.ui.xMax_spin.value(),
                self.ui.yMin_spin.value(),
                self.ui.yMax_spin.value(),
            )

    def _update_tick_counts(self) -> None:
        controller = self._get_current_controller()
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
        controller = self._get_current_controller()
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
            self._set_value_silent(self.ui.markerCount_spin, controller.marker_count)
            self.ui.marker_group.setChecked(controller.display_markers)

    def _current_tree_item_changed(
        self, current: QTreeWidgetItem, previous: QTreeWidgetItem = None
    ) -> None:

        if previous:
            controller = self._get_controller_from_tree_item(previous)
            x_axis = controller.x_axis
            y_axis = controller.y_axis
            x_axis.disconnect(self)
            y_axis.disconnect(self)

        self.ui.chartSettingsDockWidget.setEnabled((current != None))

        index_type = None
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

            index_type = controller.df.index.inferred_type

        self.ui.actionClose.setEnabled(controller is not None)
        self.ui.actionExport.setEnabled(controller is not None)
        self.ui.actionCrop.setEnabled(controller is not None)
        self.ui.actionFFT.setEnabled(index_type == "timedelta64")
        self.ui.actionSRS.setEnabled(index_type == "timedelta64")

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

    def _get_current_controller(self) -> ViewController:
        return self._get_controller_from_tree_item(self.ui.treeWidget.currentItem())
