import os
import sys

from collections.abc import Iterable

from functools import wraps
from time import time

import pandas as pd

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QWidget


def _we_are_frozen():
    """Returns whether we are frozen via py2exe.
    This will affect how we find out where we are located."""

    return hasattr(sys, "frozen")


def get_plugin_path():
    """This will get us the program's directory,
    even if we are frozen using py2exe"""

    if _we_are_frozen():
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.getcwd()

    return os.path.join(base_path, "plugins")


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print(f"{f.__name__} took {te-ts:.2f} sec")
        return result

    return wrap


def series_to_points(series: pd.Series) -> list[QPointF]:
    if series.index.inferred_type == "timedelta64":
        series.index = series.index.total_seconds()

    return [QPointF(float(i), float(v)) for i, v in series.items()]


def df_to_points(df: pd.DataFrame) -> list[str, list[QPointF]]:
    d = {}
    for col, series in df.items():
        points = series_to_points(series)
        d[col] = points
    return d


class SignalBlocker:
    def __init__(self, widgets: Iterable[QWidget] | QWidget) -> None:
        if not isinstance(widgets, Iterable):
            widgets = (widgets,)

        self._widgets = widgets
        self._blocking: dict[QWidget, bool] = {}

    def __enter__(self) -> None:
        for widget in self._widgets:
            if widget:
                self._blocking[widget] = widget.blockSignals(True)

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        for widget in self._widgets:
            if widget:
                widget.blockSignals(self._blocking[widget])
