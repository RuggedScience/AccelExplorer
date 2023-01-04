import os
import sys
from yapsy.PluginManager import PluginManager


def we_are_frozen():
    """Returns whether we are frozen via py2exe.
    This will affect how we find out where we are located."""

    return hasattr(sys, "frozen")


def module_path():
    """This will get us the program's directory,
    even if we are frozen using py2exe"""

    if we_are_frozen():
        return os.path.dirname(sys.executable)

    return os.path.dirname(__file__)


def get_plugin_manager() -> PluginManager:
    plugin_path = os.path.join(module_path(), "plugins")

    pm = PluginManager()
    pm.setPluginPlaces([plugin_path])

    return pm
