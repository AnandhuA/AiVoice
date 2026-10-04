"""Exercise the desktop controller against the installed real Praha model."""
from pathlib import Path
import json

from PySide6.QtCore import QTimer
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from malayalam_voice_studio.audio.exporter import export_audio
from malayalam_voice_studio.core.config import Paths
from malayalam_voice_studio.core.project_manager import load_project, save_project
from malayalam_voice_studio.gui.fonts import configure_fonts
from malayalam_voice_studio.gui.main_window import MainWindow
from malayalam_voice_studio.gui.theme import STYLE


def main():
    app = QApplication([])
    app.setStyle('Fusion')
    configure_fonts(app)
    app.setStyleSheet(STYLE)
    paths = Paths()
    window = MainWindow(paths)
    errors = []
    window.error = lambda text: (errors.append(text), print('ERROR:', text, flush=True), app.exit(1))
    project, warnings = load_project(paths.root / 'validation' / 'real-audio' / 'project')
    assert not warnings
    window.project = project
    window.editor.editor.setPlainText(project.original)
    window.refresh_characters()
    window.refresh(1)
    window.update_capabilities()
    window.show()
    preserved = project.segments[0].raw_path
    previous = project.segments[1].raw_path
    destination = paths.root / 'validation' / 'desktop-acceptance'
    destination.mkdir(parents=True, exist_ok=True)
    report = {}

    def rendered(result):
        try:
            audio, settings = result
            path = destination / 'dialogue.wav'
            export_audio(audio, path, settings.sample_rate, settings.bit_depth, settings.channels)
            export_audio(audio, destination / 'dialogue.mp3', settings.sample_rate, settings.bit_depth, settings.channels)
            save_project(window.project, destination / 'project')
            restored, messages = load_project(destination / 'project')
            assert not messages and len(restored.segments) == 2
            window.output.setVolume(.15)
            window.play(str(path))
            report.update(export=True, project_reopened=True, untouched_segment_preserved=True,
                          selected_segment_regenerated=True, inference_transport='isolated QProcess')
            QTimer.singleShot(1000, check_playback)
        except Exception as exc:
            window.error(str(exc))

    def check_playback():
        try:
            assert window.player.error() == QMediaPlayer.Error.NoError
            assert window.player.duration() > 0
            report['qt_playback_state'] = window.player.playbackState().name
            window.grab().save(str(destination / 'studio.png'))
            (destination / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(report, indent=2), flush=True)
            window.player.stop()
            window.dirty = False
            app.quit()
        except Exception as exc:
            window.error(str(exc))

    def generated():
        if errors or window.failures:
            return
        try:
            assert project.segments[0].raw_path == preserved
            assert project.segments[1].raw_path and project.segments[1].raw_path != previous
            assert project.segments[1].status == 'Ready'
            window.render(True, rendered)
        except Exception as exc:
            window.error(str(exc))

    window.generation.finished.connect(generated)
    QTimer.singleShot(100, lambda: window.generate(selected=True, force=True))
    QTimer.singleShot(300000, lambda: window.error('Desktop acceptance timed out.'))
    code = app.exec()
    window.generation.shutdown()
    raise SystemExit(code)


if __name__ == '__main__':
    main()
