import os

from yapsy.PluginManager import PluginManager, PluginManagerSingleton
from PySide6.QtWidgets import QApplication

from . import __version__
from .utils import module_path
from .categories import FileParser, DataFilter, DataView
from .mainwindow import MainWindow

QApplication.setOrganizationName("Rugged Science")
QApplication.setOrganizationDomain("ruggedscience.com")
QApplication.setApplicationName("AccelExplorer")
QApplication.setApplicationVersion(__version__)


def run():
    plugin_path = os.path.join(module_path(), "plugins")
    pm: PluginManager = PluginManagerSingleton.get()
    pm.setPluginPlaces([plugin_path])
    pm.setCategoriesFilter(
        {"Parsers": FileParser, "Filters": DataFilter, "Views": DataView}
    )
    pm.collectPlugins()

    app = QApplication([])
    widget = MainWindow()
    widget.show()
    return app.exec()
