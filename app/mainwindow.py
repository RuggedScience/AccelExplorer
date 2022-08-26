from typing import Tuple
import numpy as np
import pandas as pd
from scipy import fft, signal

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QMdiSubWindow
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QIcon, QPixmap
from PySide6.QtCore import QFileInfo, Qt, QPointF
from PySide6.QtCharts import QValueAxis, QSplineSeries

from .ui import resources_rc
from .ui.ui_mainwindow import Ui_MainWindow
from .snapmdiarea import SnapMdiArea
from .zoomchart import ZoomChart
from .csvparser import NULabsCSVParser, ParseError


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle(
            f'{QApplication.applicationName()} {QApplication.applicationVersion()}[*]')

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

    def _add_chart(self, df: pd.DataFrame, callouts: pd.DataFrame = None, x_range: Tuple[float, float] = None, y_range: Tuple[float, float] = None, x_title: str = None, y_title: str = None) -> QMdiSubWindow:
        chart_view = ZoomChart(self)
        chart = chart_view.chart()
        chart.legend().hide()

        x = df.iloc(axis=1)[0]
        y = df.iloc(axis=1)[1]

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
        
        if y_range:
            y_axis.setRange(*y_range)
        else:
            # Add some margin to the y axis
            y_axis.setRange(y.min() + (y.min() * 0.1), y.max() + (y.max() * 0.1))

        chart.addAxis(x_axis, Qt.AlignBottom)
        chart.addAxis(y_axis, Qt.AlignLeft)

        points = [QPointF(row.iloc[0], row.iloc[1]) for _, row in df.iterrows()]
        series = QSplineSeries()

        chart.addSeries(series)
        series.attachAxis(x_axis)
        series.attachAxis(y_axis)
        series.replace(points)

        pen = series.pen()
        pen.setWidth(4)
        series.setPen(pen)
        sub_window = self._add_subwindow(chart_view)

        if not callouts is None:
            for _, row in callouts.iterrows():
                pos = QPointF(row['freq'], row['mag'])
                chart_view.add_callout(pos, f'Frequency: {pos.x():.2f}\nMagnitude: {pos.y():.2f}')

        def point_hovered(pos: QPointF, state: bool):
            if state:
                chart_view.show_tooltip(pos, f'Frequency: {pos.x():.2f}\nMagnitude: {pos.y():.2f}')
            else:
                chart_view.tooltip.hide()

        series.hovered.connect(point_hovered)
        series.clicked.connect(chart_view.keep_tooltip)

        return sub_window

    def addCsv(self, filename):
        parser = NULabsCSVParser(filename)
        try:
            accel_df = parser.parse()
        except ParseError:
            # TODO: Add error window
            return

        x_col = accel_df.iloc(axis=1)[0]
        y_col = accel_df.iloc(axis=1)[1]
        yf = fft.fft(y_col.values)
        # Generate the frequency bin for x axis
        x = fft.fftfreq(yf.size, 1 / parser.sample_rate)
        # We only want the first half since the data is mirrored
        x = x[:int(len(x) / 2)]
        # Calclulate the magnitude
        y: np.ndarray = (np.abs(yf) * 1.0 / yf.size) * 2.0
        # Keep the length the same as x
        y = y[:x.size]

        fft_df = pd.DataFrame({'freq': x, 'mag': y})
        peaks = signal.argrelextrema(y, np.greater_equal, order=10)[0]
        peaks = fft_df.iloc[peaks]
        peaks = peaks.nlargest(3, 'mag')
        
        fft_sw = self._add_chart(fft_df, callouts=peaks, x_title='Frequency (Hz)', y_title='Magnitude')
        accel_sw = self._add_chart(accel_df, x_title='Time (ms)', y_title='Acceleration (g)')

        fft_icon = QIcon(QPixmap(':/icons/freq_icon.png'))
        accel_icon = QIcon(QPixmap(':/icons/accel_icon.png'))

        info = QFileInfo(filename)
        fft_sw.setWindowTitle(f'FFT - {info.fileName()}')
        fft_sw.setWindowFilePath(filename)
        fft_sw.setWindowIcon(fft_icon)
        accel_sw.setWindowTitle(f'Accel - {info.fileName()}')
        accel_sw.setWindowFilePath(filename)
        accel_sw.setWindowIcon(accel_icon)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            for url in mimeData.urls():
                if url.isLocalFile():
                    info = QFileInfo(url.toLocalFile())
                    if info.suffix() == 'csv':
                        self.addCsv(url.toLocalFile())