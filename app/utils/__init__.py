import os
import sys

from collections.abc import Iterable

from functools import wraps
from time import time

import numpy as np
import pandas as pd

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


def timing(prefix: str = ""):
    def inner(f):
        @wraps(f)
        def wrap(*args, **kw):
            ts = time()
            result = f(*args, **kw)
            te = time()
            print(f"{prefix}{f.__name__} took {te-ts:.2f} sec")
            return result

        return wrap

    return inner


def generate_time_index(sample_rate: int, size: int) -> pd.TimedeltaIndex:
    """Create a Pandas TimeDeltaIndex with the given sample rate and size."""

    # Do all calculations in nanoseconds to keep values
    # as integers and prevent floating point errors.
    spacing = 1_000_000_000 / sample_rate
    end = spacing * size

    values = np.arange(stop=int(end), step=int(spacing))
    # Clamp index to size of the dataframe
    # to prevent length mismatch errors.
    return pd.to_timedelta(values[:size], unit="ns")


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


from .markergenerator import MarkerGenerator, MarkerShape
from .optionsuimanager import OptionsUiManager
from .undoable import undoable
