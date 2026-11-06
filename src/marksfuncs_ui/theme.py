"""Blue workspace styling with Space Grotesk titles and Manrope controls."""

from pathlib import Path

from PyQt6.QtGui import QFontDatabase, QIcon


def load_fonts():
    for path in (Path(__file__).parent / "assets" / "fonts").glob("*.ttf"):
        if QFontDatabase.addApplicationFont(str(path)) < 0:
            raise RuntimeError(f"Could not load font {path.name}")


def app_icon():
    return QIcon(str(Path(__file__).parent / "assets" / "icon.svg"))


STYLE = """
QWidget { font-family: 'Manrope'; font-size: 12px; color: #2a2c3c;
    selection-background-color: #e7e8ff; selection-color: #2028ff; }
QMainWindow, QDialog { background: #fafbff; }
QLabel { background: transparent; border: none; }
QFrame#Header { background: white; border-bottom: 1px solid #e8eaf3; }
QLabel#Brand { font-family: 'Space Grotesk'; font-size: 24px; font-weight: 700; color: #2028ff; }
QLabel#Title { font-family: 'Space Grotesk'; font-size: 32px; font-weight: 600; color: #232545; }
QLabel#Subtitle { font-size: 11px; color: #85879b; }
QLabel#Section { font-family: 'Space Grotesk'; font-size: 11px; font-weight: 600; color: #82859b; letter-spacing: 1px; }
QLabel#Formula { font-family: 'Space Grotesk'; font-size: 22px; color: #2028ff; }
QLabel#Badge { background: #f0f1ff; color: #656abc; padding: 5px 9px; border-radius: 4px; font-size: 10px; }
QLabel#Error { color: #a94239; background: #fff0ed; border: 1px solid #efd5cf; padding: 10px; border-radius: 5px; }
QFrame#Sidebar { background: white; border-right: 1px solid #e8eaf3; }
QFrame#Inspector { background: white; border-left: 1px solid #e8eaf3; }
QFrame#PlotCard, QFrame#DetailCard { background: white; border: 1px solid #e5e7f1; border-radius: 7px; }
QFrame#Divider { background: #e9ebf3; max-height: 1px; border: none; }
QPushButton { border: 1px solid #e0e3ef; background: white; border-radius: 5px; padding: 8px 12px; color: #666b89; }
QPushButton:hover { background: #f5f5ff; border-color: #b3b7ff; color: #2028ff; }
QPushButton:pressed { background: #e9eaff; }
QPushButton:focus { border: 1px solid #2028ff; }
QPushButton:disabled { color: #afb2c5; background: #fafaff; }
QPushButton#Primary { color: white; background: #2028ff; border-color: #2028ff; font-weight: 600; padding: 11px 16px; }
QPushButton#Primary:hover { background: #121be2; }
QPushButton#Ghost { background: transparent; border: none; color: #81859f; padding: 6px 9px; }
QPushButton#Ghost:hover { color: #2028ff; background: #f0f1ff; }
QPushButton#Tab { background: transparent; border: none; border-radius: 0; padding: 10px 14px; color: #878ba1; }
QPushButton#Tab:checked { color: #2028ff; border-bottom: 2px solid #2028ff; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #fefeff; border: 1px solid #e0e3ef; border-radius: 5px; padding: 7px 9px; min-height: 18px; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #777dff; background: white; }
QSpinBox::up-button, QDoubleSpinBox::up-button { width: 18px; border: none; }
QSpinBox::down-button, QDoubleSpinBox::down-button { width: 18px; border: none; }
QSlider::groove:horizontal { height: 3px; border-radius: 1px; background: #e9ebf5; }
QSlider::sub-page:horizontal { background: #5960ff; border-radius: 1px; }
QSlider::handle:horizontal { background: white; border: 2px solid #454dff; width: 12px; margin: -6px 0; border-radius: 7px; }
QSlider::handle:horizontal:hover { border-color: #2028ff; background: #f0f1ff; }
QLabel#ParamSymbol { font-family: 'Space Grotesk'; color: #2028ff; font-size: 17px; font-weight: 600; }
QLabel#ParamHelp, QLabel#ParamEndpoint { color: #979bb1; font-size: 10px; }
QLabel#ParamLabel { color: #686e8a; font-size: 11px; }
QListWidget { background: white; border: none; outline: none; }
QListWidget::item { padding: 9px 12px; margin: 1px 7px; border-radius: 5px; border-left: 2px solid transparent; }
QListWidget::item:hover { background: #f8f8ff; }
QListWidget::item:selected { background: #f0f1ff; color: #2028ff; border-left: 2px solid #2028ff; }
QListWidget::item:disabled { color: #979bb1; background: white; font-size: 10px; padding-top: 17px; padding-bottom: 4px; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QScrollBar:vertical { width: 5px; background: transparent; margin: 1px; }
QScrollBar::handle:vertical { background: #dce0ef; border-radius: 2px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QTextEdit, QPlainTextEdit { border: none; background: transparent; padding: 8px; }
QPlainTextEdit { font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 11px; color: #494fa6; }
QTableWidget { background: white; border: none; gridline-color: #eff0f7; alternate-background-color: #fafaff; }
QHeaderView::section { background: #f5f6ff; color: #7c80a3; border: none; padding: 5px; font-weight: 600; }
QCheckBox { spacing: 8px; color: #7c819c; font-size: 11px; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #d0d5e8; border-radius: 3px; background: white; }
QCheckBox::indicator:checked { background: #2028ff; border-color: #2028ff; image: url('@CHECK@'); }
QToolTip { background: white; color: #5f6586; border: 1px solid #dde1ef; padding: 7px; }
QStatusBar { background: #fafbff; color: #8b90aa; font-size: 10px; }
QStatusBar::item { border: none; }
QSplitter::handle { background: #f0f1f7; width: 1px; }
""".replace("@CHECK@", (Path(__file__).parent / "assets" / "check.svg").as_posix())
