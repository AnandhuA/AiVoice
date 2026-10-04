from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import multiprocessing
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from .core.config import Paths
from .gui.main_window import MainWindow
from .gui.theme import STYLE


def main() -> None:
    multiprocessing.freeze_support()
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    app = QApplication(sys.argv)
    app.setApplicationName("Malayalam Voice Studio")
    app.setOrganizationName("MalayalamVoiceStudio")
    app.setStyle("Fusion")
    from .gui.fonts import configure_fonts
    configure_fonts(app)
    app.setStyleSheet(STYLE)
    paths = Paths()
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(paths.logs / "studio.log",
        maxBytes=2_000_000, backupCount=3, encoding="utf-8")], format="%(asctime)s %(levelname)s %(message)s")
    def exception_hook(kind, value, tb):
        logging.error("Unhandled exception", exc_info=(kind, value, tb))
        QMessageBox.critical(None, "Studio error", f"{value}\nDetails were written to logs/studio.log.")
    sys.excepthook = exception_hook
    try:
        window = MainWindow(paths)
        window.show()
        sys.exit(app.exec())
    except Exception as exc:
        logging.exception("Startup failed")
        QMessageBox.critical(None, "Startup failed", f"{exc}\nCheck settings.json and logs/studio.log.")


if __name__ == "__main__":
    main()
