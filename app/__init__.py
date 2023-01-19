import logging
import os

from PySide6.QtWidgets import QApplication
from yapsy.PluginManager import PluginManager, PluginManagerSingleton, PluginFileLocator

from app.plugins.dataframeplugins import DataFramePlugin
from app.plugins.parserplugins import ParserPlugin
from app.utils import get_plugin_path
from app.version import __version__
from app.widgets.mainwindow import MainWindow

logging.basicConfig(level=logging.WARN)

QApplication.setOrganizationName("Rugged Science")
QApplication.setOrganizationDomain("ruggedscience.com")
QApplication.setApplicationName("AccelExplorer")
QApplication.setApplicationVersion(__version__)


def run():
    plugin_path = get_plugin_path()
    pm: PluginManager = PluginManagerSingleton.get()
    pm.setPluginPlaces(
        [
            os.path.join(plugin_path, "parsers"),
            os.path.join(plugin_path, "filters"),
            os.path.join(plugin_path, "views"),
        ]
    )
    pm.setCategoriesFilter({"parsers": ParserPlugin, "dataframe": DataFramePlugin})
    pm.collectPlugins()

    app = QApplication([])
    widget = MainWindow()
    widget.show()
    return app.exec()


if __name__ == "__main__":
    import sys

    sys.exit(run())
