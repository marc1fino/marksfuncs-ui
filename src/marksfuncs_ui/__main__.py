"""Launch marksfuncs-ui."""

import sys

from PyQt6.QtCore import QLocale
from PyQt6.QtWidgets import QApplication, QMessageBox

from .theme import STYLE, app_icon, load_fonts


def main():
    QLocale.setDefault(QLocale(QLocale.Language.English))
    app = QApplication(sys.argv)
    app.setApplicationName("marksfuncs-ui")
    app.setOrganizationName("marksfuncs")
    app.setWindowIcon(app_icon())
    try:
        load_fonts()
        app.setStyleSheet(STYLE)
        from .main_window import MainWindow
        window = MainWindow()
    except Exception as error:
        QMessageBox.critical(None, "marksfuncs-ui could not start", str(error))
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
