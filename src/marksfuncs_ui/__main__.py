"""Launch the native marksfuncs function laboratory."""

import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from .theme import STYLE, app_icon, load_fonts


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("marksfuncs Studio")
    app.setOrganizationName("marksfuncs")
    app.setWindowIcon(app_icon())
    try:
        load_fonts()
        app.setStyleSheet(STYLE)
        from .main_window import MainWindow
        window = MainWindow()
    except Exception as error:
        QMessageBox.critical(None, "No se pudo iniciar marksfuncs", str(error))
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
