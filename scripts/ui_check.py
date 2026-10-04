"""Render the real Qt widgets to an image without starting model inference."""
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from malayalam_voice_studio.core.config import Paths
from malayalam_voice_studio.gui.main_window import MainWindow
from malayalam_voice_studio.gui.theme import STYLE


def main():
    app = QApplication([])
    app.setStyle('Fusion')
    from malayalam_voice_studio.gui.fonts import configure_fonts
    configure_fonts(app)
    app.setStyleSheet(STYLE)
    window = MainWindow(Paths())
    window.editor.editor.setPlainText('നീ... [PAUSE:400] ഇവിടെ വന്നത് എന്തിനാ?\nനമുക്ക് പോകാം.')
    window.acting.fields['emotion'].setCurrentText('Suspicious')
    window.analyze()
    window.show()
    def capture():
        directory = Path('validation')
        directory.mkdir(exist_ok=True)
        window.grab().save(str(directory / 'studio.png'))
        window.tabs.setCurrentIndex(1)
        app.processEvents()
        window.grab().save(str(directory / 'studio-segments.png'))
        window.tabs.setCurrentIndex(0)
        window.character.details.toggle.setChecked(True)
        window.acting.details.toggle.setChecked(True)
        window.editor.details.toggle.setChecked(True)
        window.resize(900, 650)
        app.processEvents()
        window.grab().save(str(directory / 'studio-advanced.png'))
        window.dirty = False
        def finish():
            if any(task.isRunning() for task in window.tasks):
                QTimer.singleShot(250, finish)
            else:
                app.quit()
        finish()
    QTimer.singleShot(4000, capture)
    app.exec()


if __name__ == '__main__':
    main()
