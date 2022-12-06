import re
from typing import Tuple, Union
from collections.abc import Iterable
import numpy as np
import pandas as pd
from scipy import fft

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QMdiSubWindow,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox
)
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QIcon, QPixmap
from PySide6.QtCore import QFileInfo, Qt, QPointF, QTimer
from PySide6.QtCharts import QValueAxis, QLineSeries

from .ui import resources_rc
from .ui.ui_mainwindow import Ui_MainWindow
from .snapmdiarea import SnapMdiArea
from .zoomchart import ZoomChart
from .parserdialog import ParserDialog


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
    ) -> QMdiSubWindow:

        widget = QWidget(self)
        vlayout = QVBoxLayout()
        widget.setLayout(vlayout)
        hlayout = QHBoxLayout()
        vlayout.addLayout(hlayout)

        chart_view = ZoomChart(self)
        chart = chart_view.chart()
        # chart.legend().hide()
        vlayout.addWidget(chart_view)

        def point_hovered(pos: QPointF, state: bool):
            if state:
                chart_view.show_tooltip(
                    pos, f"Frequency: {pos.x():.2f}\nMagnitude: {pos.y():.2f}"
                )
            else:
                chart_view.tooltip.hide()

        x = df.iloc(axis=1)[0]
        x_axis = QValueAxis()

        if x_title:
            x_axis.setTitleText(x_title)

        if x_range:
            x_axis.setRange(*x_range)
        else:
            x_axis.setRange(x.min(), x.max())

        y_axis = QValueAxis()

        if y_title:
            y_axis.setTitleText(y_title)

        y_dfs = df.iloc[:, 1:]
        if y_range:
            y_axis.setRange(*y_range)
        else:
            # Add some margin to the y axis
            y_min = y_dfs.min(axis=1).min()
            y_max = y_dfs.max(axis=1).max()
            y_axis.setRange(y_min - abs(y_min * 0.1), y_max + abs(y_max * 0.1))

        chart.addAxis(x_axis, Qt.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignLeft)

        points = {column: [] for column in y_dfs}

        for row in df.itertuples(index=False):
            for column in y_dfs:
                x = float(row[0])
                y = float(getattr(row, column))
                points[column].append(QPointF(x, y))

        for column in y_dfs:
            data = points[column]
            series = QLineSeries()
            series.setName(column)
            # series.setUseOpenGL(True)

            chart.addSeries(series)
            series.attachAxis(x_axis)
            series.attachAxis(y_axis)
            series.replace(data)

            pen = series.pen()
            pen.setWidth(4)
            series.setPen(pen)

            series.hovered.connect(point_hovered)
            series.clicked.connect(chart_view.keep_tooltip)

            check_box = QCheckBox(column)
            check_box.setChecked(True)
            check_box.stateChanged.connect(series.setVisible)
            hlayout.addWidget(check_box)

        sub_window = self._add_subwindow(widget)

        if not callouts is None:
            for _, row in callouts.iterrows():
                pos = QPointF(row["freq"], row["mag"])
                chart_view.add_callout(
                    pos, f"Frequency: {pos.x():.2f}\nMagnitude: {pos.y():.2f}"
                )

        return sub_window

    def addCsvs(self, filenames: Union[str, Iterable[str]]) -> None:
        if not isinstance(filenames, Iterable):
            filenames = [filenames]

        for filename in filenames:
            dlg = ParserDialog(filename, self)
            if not dlg.exec():
                continue
            accel_df = dlg.df

            fft_df = None
            for (name, data) in accel_df.iloc[:, 1:].iteritems():

                yf = fft.fft(data.values)

                if fft_df is None:
                    # Generate the frequency bin for x axis
                    x = fft.fftfreq(yf.size, 1 / dlg.sampleRate)
                    # We only want the first half since the data is mirrored
                    x = x[: int(len(x) / 2)]
                    fft_df = pd.DataFrame({"freq": x})

                # Calclulate the magnitude
                y: np.ndarray = (np.abs(yf) * 1.0 / yf.size) * 2.0
                # Keep the length the same as x
                y = y[: fft_df["freq"].size]
                fft_df[name] = y

            # Drop the "0hz" frequency since that's not real
            fft_df = fft_df.iloc[1:, :]
            fft_sw = self._add_chart(
                fft_df, x_title="Frequency (Hz)", y_title="Magnitude"
            )
            accel_sw = self._add_chart(
                accel_df, x_title="Time (ms)", y_title="Acceleration (g)"
            )

            fft_icon = QIcon(QPixmap(":/icons/freq_icon.png"))
            accel_icon = QIcon(QPixmap(":/icons/accel_icon.png"))

            info = QFileInfo(filename)
            fft_sw.setWindowTitle(f"FFT - {info.fileName()}")
            fft_sw.setWindowFilePath(filename)
            fft_sw.setWindowIcon(fft_icon)
            accel_sw.setWindowTitle(f"Accel - {info.fileName()}")
            accel_sw.setWindowFilePath(filename)
            accel_sw.setWindowIcon(accel_icon)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = []
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            for url in mimeData.urls():
                if url.isLocalFile():
                    info = QFileInfo(url.toLocalFile())
                    if re.search("csv", info.suffix(), re.IGNORECASE):
                        urls.append(url.toLocalFile())

        if urls:
            event.acceptProposedAction()
            QTimer.singleShot(1, lambda: self.addCsvs(urls))
