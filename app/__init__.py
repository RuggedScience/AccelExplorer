import sys
import locale

from PySide6.QtWidgets import QApplication

try:
    from app._version import version
except ImportError:
    version = "DEV"

from app.widgets.mainwindow import MainWindow

locale.setlocale(locale.LC_ALL, "")

QApplication.setOrganizationName("Rugged Science")
QApplication.setOrganizationDomain("ruggedscience.com")
QApplication.setApplicationName("AccelExplorer")
QApplication.setApplicationVersion(version)


def run():
    app = QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
