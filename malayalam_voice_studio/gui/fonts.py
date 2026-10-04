import os
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase


def configure_fonts(app):
    """Register Windows fonts explicitly, including for offscreen validation."""
    root = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    for name in ('segoeui.ttf', 'segoeuib.ttf', 'Nirmala.ttc', 'Nirmala.ttf', 'NirmalaB.ttf'):
        path = root / name
        if path.is_file():
            QFontDatabase.addApplicationFont(str(path))
    font = QFont('Segoe UI', 10)
    font.setFamilies(['Segoe UI', 'Nirmala UI', 'sans-serif'])
    app.setFont(font)
