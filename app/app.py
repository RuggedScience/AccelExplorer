from PySide6.QtWidgets import QApplication

from . import __version__
from .mainwindow import MainWindow

# import logging
# logging.basicConfig(level=logging.DEBUG)

QApplication.setOrganizationName("Rugged Science")
QApplication.setOrganizationDomain("ruggedscience.com")
QApplication.setApplicationName("AccelExplorer")
QApplication.setApplicationVersion(__version__)


def run():
    app = QApplication([])
    widget = MainWindow()
    widget.show()
    return app.exec()
