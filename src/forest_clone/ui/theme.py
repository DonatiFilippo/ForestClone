"""Application-wide light/dark stylesheet."""

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication, theme: str) -> None:
    system_dark = app.palette().color(QPalette.ColorRole.Window).lightness() < 128
    dark = theme == "Dark" or (theme == "System" and system_dark)
    colors = (
        {
            "bg": "#141b18", "surface": "#1d2722", "surface2": "#24312a",
            "border": "#34463c", "text": "#eef5f0", "muted": "#98a99e",
            "input": "#26342d", "sidebar": "#15251d",
        }
        if dark else
        {
            "bg": "#f3f6f2", "surface": "#ffffff", "surface2": "#f7faf7",
            "border": "#dce6dd", "text": "#203027", "muted": "#718077",
            "input": "#f8faf8", "sidebar": "#183f2b",
        }
    )
    app.setStyleSheet(
        f"""
        * {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}
        QWidget#root, QWidget#page, QStackedWidget#pages {{ background: {colors['bg']}; color: {colors['text']}; }}
        QFrame#sidebar {{ background: {colors['sidebar']}; border: none; }}
        QLabel#brand {{ color: #f1f8f3; font-size: 17px; font-weight: 800; letter-spacing: 1px; }}
        QLabel#tagline, QLabel#localLabel {{ color: #9fc2ac; font-size: 11px; }}
        QListWidget#navigation {{ background: transparent; color: #b9d0c1; border: none; outline: none; font-size: 14px; }}
        QListWidget#navigation::item {{ height: 44px; padding-left: 8px; margin: 3px 0; border-radius: 8px; }}
        QListWidget#navigation::item:selected {{ background: #2d6548; color: white; font-weight: 600; }}
        QListWidget#navigation::item:hover:!selected {{ background: #204c35; color: white; }}
        QLabel#pageTitle {{ color: {colors['text']}; font-size: 27px; font-weight: 750; }}
        QLabel#pageSubtitle {{ color: {colors['muted']}; font-size: 13px; }}
        QLabel#eyebrow, QLabel#sessionStatus {{ color: #4c9663; font-size: 10px; font-weight: 800; letter-spacing: 1px; }}
        QFrame#focusCard, QFrame#settingsCard, QFrame#statCard, QFrame#periodBar {{ background: {colors['surface']}; border: 1px solid {colors['border']}; border-radius: 14px; }}
        QLabel#timerLabel {{ color: {colors['text']}; font-size: 52px; font-weight: 650; letter-spacing: 2px; }}
        QLabel#fieldLabel {{ color: {colors['muted']}; font-size: 12px; }}
        QLabel#statValue {{ color: {colors['text']}; font-size: 20px; font-weight: 700; }}
        QLabel#statLabel {{ color: {colors['muted']}; font-size: 9px; font-weight: 700; letter-spacing: 1px; }}
        QPushButton {{ min-height: 34px; padding: 0 16px; border-radius: 8px; font-weight: 600; }}
        QPushButton#primaryButton {{ color: white; background: #438f59; border: 1px solid #438f59; }}
        QPushButton#primaryButton:hover {{ background: #367e4c; border-color: #367e4c; }}
        QPushButton#primaryButton:pressed {{ background: #2e6e42; }}
        QPushButton#secondaryButton {{ color: {colors['text']}; background: transparent; border: 1px solid {colors['border']}; }}
        QPushButton#secondaryButton:hover {{ background: {colors['surface2']}; }}
        QPushButton#periodButton {{ min-width: 34px; max-width: 34px; padding: 0; color: {colors['text']}; background: {colors['surface2']}; border: 1px solid {colors['border']}; font-size: 21px; }}
        QPushButton#periodButton:hover {{ border-color: #63a574; background: {colors['input']}; }}
        QLabel#periodLabel {{ color: {colors['text']}; font-size: 13px; font-weight: 650; }}
        QPushButton:disabled {{ background: {colors['border']}; color: {colors['muted']}; border-color: {colors['border']}; }}
        QComboBox, QSpinBox {{ min-height: 34px; padding: 0 10px; color: {colors['text']}; background: {colors['input']}; border: 1px solid {colors['border']}; border-radius: 7px; }}
        QComboBox:hover, QSpinBox:hover {{ border-color: #63a574; }}
        QComboBox::drop-down {{ border: none; width: 24px; }}
        QComboBox QAbstractItemView {{ color: {colors['text']}; background: {colors['surface']}; selection-background-color: #438f59; border: 1px solid {colors['border']}; }}
        QProgressBar#sessionProgress {{ min-height: 7px; max-height: 7px; background: {colors['border']}; border: none; border-radius: 3px; }}
        QProgressBar#sessionProgress::chunk {{ background: #55a76b; border-radius: 3px; }}
        QScrollArea#forestScroll {{ background: transparent; border: none; }}
        QScrollArea#forestScroll > QWidget > QWidget {{ background: {colors['surface']}; border-radius: 14px; }}
        QTableWidget#historyTable {{ color: {colors['text']}; background: {colors['surface']}; alternate-background-color: {colors['surface2']}; border: 1px solid {colors['border']}; border-radius: 12px; selection-background-color: #dcefe1; selection-color: #203027; outline: none; }}
        QTableWidget#historyTable::item {{ padding-left: 12px; border-bottom: 1px solid {colors['border']}; }}
        QHeaderView::section {{ color: {colors['muted']}; background: {colors['surface2']}; border: none; border-bottom: 1px solid {colors['border']}; padding: 12px; font-size: 10px; font-weight: 700; }}
        QCheckBox {{ color: {colors['text']}; spacing: 9px; }}
        QCheckBox::indicator {{ width: 17px; height: 17px; border: 1px solid {colors['border']}; border-radius: 4px; background: {colors['input']}; }}
        QCheckBox::indicator:checked {{ background: #438f59; border-color: #438f59; }}
        QFormLayout QLabel {{ color: {colors['text']}; }}
        QToolTip {{ color: {colors['text']}; background: {colors['surface']}; border: 1px solid {colors['border']}; }}
        """
    )
