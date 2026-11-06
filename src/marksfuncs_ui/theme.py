"""Typography and the quiet teal visual identity of the desktop workspace."""

from pathlib import Path

from PyQt6.QtGui import QFontDatabase, QIcon


def load_fonts():
    for path in (Path(__file__).parent / "assets" / "fonts").glob("*.ttf"):
        if QFontDatabase.addApplicationFont(str(path)) < 0:
            raise RuntimeError(f"No se pudo cargar la fuente {path.name}")


def app_icon():
    return QIcon(str(Path(__file__).parent / "assets" / "icon.svg"))


STYLE = """
QWidget { font-family: 'Manrope'; font-size: 12px; color: #25353b;
    selection-background-color: #d4eeeb; selection-color: #086f73; }
QMainWindow, QDialog { background: #f7f9f9; }
QLabel { background: transparent; border: none; }
QFrame#Header { background: white; border-bottom: 1px solid #e1e8e7; }
QLabel#Brand { font-family: 'Space Grotesk'; font-size: 24px; font-weight: 700; color: #163f43; }
QLabel#Eyebrow { font-size: 10px; font-weight: 700; color: #658580; letter-spacing: 2px; }
QLabel#Title { font-family: 'Space Grotesk'; font-size: 32px; font-weight: 600; color: #193d40; }
QLabel#Subtitle { font-size: 12px; color: #71817f; }
QLabel#Section { font-size: 10px; font-weight: 700; color: #71817f; letter-spacing: 1px; }
QLabel#Formula { font-family: 'Space Grotesk'; font-size: 22px; color: #087f83; }
QLabel#Badge { background: #eaf5f1; color: #36816a; padding: 5px 9px; border-radius: 4px; font-size: 10px; }
QLabel#Description { color: #667c78; font-size: 12px; }
QLabel#Error { color: #a94239; background: #fff0ed; border: 1px solid #efd5cf; padding: 10px; border-radius: 5px; }
QFrame#Sidebar { background: white; border-right: 1px solid #e1e8e7; }
QFrame#Inspector { background: white; border-left: 1px solid #e1e8e7; }
QFrame#PlotCard, QFrame#DetailCard { background: white; border: 1px solid #e0e9e6; border-radius: 8px; }
QFrame#Divider { background: #e7ecea; max-height: 1px; border: none; }
QPushButton { border: 1px solid #dce5e2; background: white; border-radius: 5px; padding: 8px 12px; color: #526b66; }
QPushButton:hover { background: #f1f8f5; border-color: #9dc9bd; color: #146f68; }
QPushButton:pressed { background: #dff0e9; }
QPushButton:focus { border: 1px solid #087f83; }
QPushButton:disabled { color: #a5b3ae; background: #f7f9f8; }
QPushButton#Primary { color: white; background: #087f83; border-color: #087f83; font-weight: 600; padding: 11px 16px; }
QPushButton#Primary:hover { background: #096d71; }
QPushButton#Ghost { background: transparent; border: none; color: #70847d; padding: 6px 9px; }
QPushButton#Ghost:hover { color: #087f83; background: #edf6f1; }
QPushButton#Tab { background: transparent; border: none; border-radius: 0; padding: 10px 14px; color: #7e8a85; }
QPushButton#Tab:checked { color: #087f83; border-bottom: 2px solid #087f83; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #fcfdfc; border: 1px solid #dce6e1; border-radius: 5px; padding: 7px 9px; min-height: 18px; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #4caa9a; background: white; }
QSpinBox::up-button, QDoubleSpinBox::up-button { width: 18px; border: none; }
QSpinBox::down-button, QDoubleSpinBox::down-button { width: 18px; border: none; }
QSlider::groove:horizontal { height: 4px; border-radius: 2px; background: #e9efeb; }
QSlider::sub-page:horizontal { background: #319a8f; border-radius: 2px; }
QSlider::handle:horizontal { background: white; border: 2px solid #229083; width: 12px; margin: -5px 0; border-radius: 7px; }
QSlider::handle:horizontal:hover { border-color: #096c69; }
QLabel#ParamSymbol { font-family: 'Space Grotesk'; color: #087f83; font-size: 17px; font-weight: 600; }
QLabel#ParamHelp, QLabel#ParamEndpoint { color: #8b9992; font-size: 10px; }
QLabel#ParamLabel { color: #51685f; font-size: 11px; }
QListWidget { background: white; border: none; outline: none; }
QListWidget::item { padding: 9px 12px; margin: 1px 7px; border-radius: 5px; border-left: 2px solid transparent; }
QListWidget::item:hover { background: #f4f8f5; }
QListWidget::item:selected { background: #eaf4ef; color: #087f83; border-left: 2px solid #087f83; }
QListWidget::item:disabled { color: #8b9a92; background: white; font-size: 10px; padding-top: 17px; padding-bottom: 4px; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QScrollBar:vertical { width: 5px; background: transparent; margin: 1px; }
QScrollBar::handle:vertical { background: #d4dfd8; border-radius: 2px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QTextEdit, QPlainTextEdit { border: none; background: transparent; padding: 8px; }
QPlainTextEdit { font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 11px; color: #26746d; }
QTableWidget { background: white; border: none; gridline-color: #edf1ee; alternate-background-color: #f8fbf9; }
QHeaderView::section { background: #f2f7f4; color: #688176; border: none; padding: 5px; font-weight: 600; }
QCheckBox { spacing: 8px; color: #6d8176; font-size: 11px; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #c2d3c8; border-radius: 3px; background: white; }
QCheckBox::indicator:checked { background: #087f83; border-color: #087f83; image: url('@CHECK@'); }
QToolTip { background: white; color: #476458; border: 1px solid #d5e4da; padding: 7px; }
QStatusBar { background: #f7f9f9; color: #82958b; font-size: 10px; }
QStatusBar::item { border: none; }
QSplitter::handle { background: #e6ece8; width: 1px; }
""".replace("@CHECK@", (Path(__file__).parent / "assets" / "check.svg").as_posix())
