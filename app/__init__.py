import logging
import locale


from PySide6.QtWidgets import QApplication

from app.version import __version__
from app.widgets.mainwindow import MainWindow

logging.basicConfig(level=logging.WARN)
locale.setlocale(locale.LC_ALL, "")

QApplication.setOrganizationName("Rugged Science")
QApplication.setOrganizationDomain("ruggedscience.com")
QApplication.setApplicationName("AccelExplorer")
QApplication.setApplicationVersion(__version__)


def run():
    app = QApplication([])
    widget = MainWindow()
    widget.show()
    return app.exec()


if __name__ == "__main__":
    import sys

    sys.exit(run())
