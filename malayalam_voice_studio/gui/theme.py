STYLE = """
QWidget { background: #10141d; color: #dbe3ee; font-family: 'Segoe UI', 'Nirmala UI'; font-size: 12px; }
QMainWindow, QDialog { background: #10141d; }
QFrame#card { background: #181e2b; border: 1px solid #2a3447; border-radius: 10px; }
QLabel { background: transparent; }
QLabel#title { font-size: 24px; font-weight: 700; color: #f4f7fc; }
QLabel#section { color: #8f9cb5; font-size: 11px; font-weight: 700; padding: 4px 0; }
QLabel#muted { color: #8794ad; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
 background: #0e131e; border: 1px solid #303c51; border-radius: 5px; padding: 6px; selection-background-color: #296f69;
}
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #62d4b0; }
QPushButton { background: #242e40; border: 1px solid #34425a; border-radius: 5px; padding: 7px 12px; }
QPushButton:hover { background: #34435c; }
QPushButton:disabled { color: #5b6578; background: #1a2230; }
QPushButton#primary { background: #5cd6b0; border: none; color: #09251e; font-weight: 700; }
QPushButton#primary:hover { background: #8ae7c9; }
QTableWidget, QListWidget { background: #141b27; border: 1px solid #29364a; alternate-background-color: #192231; }
QTableWidget::item:selected, QListWidget::item:selected { background: #254c50; }
QHeaderView::section { background: #202b3c; color: #9fadc3; padding: 7px; border: none; }
QSlider::groove:horizontal { background: #2e3a50; height: 5px; border-radius: 2px; }
QSlider::handle:horizontal { background: #65d9b5; width: 13px; margin: -4px 0; border-radius: 6px; }
QProgressBar { border: 1px solid #303c51; border-radius: 4px; text-align: center; background: #111927; }
QProgressBar::chunk { background: #318575; }
QTabWidget::pane { border: 1px solid #29364a; }
QTabBar::tab { background: #192230; padding: 9px 15px; }
QTabBar::tab:selected { color: #6cdfbc; border-bottom: 2px solid #6cdfbc; }
QScrollBar:vertical { background: #121823; width: 10px; }
QScrollBar::handle:vertical { background: #34425a; min-height: 20px; }
QStatusBar { background: #151d2a; color: #99a8bf; }
QToolTip { background: #273246; color: #e4ebf6; border: 1px solid #4c607a; }
QToolButton { background: transparent; color: #9fadc3; border: none; padding: 6px 0; }
QToolButton:hover { color: #6cdfbc; }
QMenuBar { background: #151d2a; padding: 4px; }
QMenuBar::item:selected, QMenu::item:selected { background: #254c50; }
QMenu { background: #181e2b; border: 1px solid #34425a; padding: 5px; }
QMenu::item { padding: 8px 24px; }
"""
