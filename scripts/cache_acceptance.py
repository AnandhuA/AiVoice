"""Verify that changing only timing reuses actual cached speech."""
import json
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from malayalam_voice_studio.core.config import Paths
from malayalam_voice_studio.core.project_manager import load_project
from malayalam_voice_studio.gui.tasks import GenerationController


def main():
    app = QCoreApplication([])
    paths = Paths()
    scene, warnings = load_project(paths.root / 'validation' / 'desktop-acceptance' / 'project')
    assert not warnings
    segment = scene.segments[1]
    original = segment.raw_path
    segment.pause_before_ms = 725
    controller = GenerationController()
    events = []
    controller.event.connect(lambda kind, value: events.append((kind, value)))
    controller.finished.connect(app.quit)
    controller.start(scene, paths, paths.load_settings(), [segment.id])
    app.exec()
    failures = [value for kind, value in events if kind in ('error', 'failed')]
    assert not failures, failures
    takes = [value for kind, value in events if kind == 'segment']
    assert len(takes) == 1 and takes[0]['raw_path'] == original
    report = {'pause_only_change_reuses_raw_take': True, 'pause_ms': segment.pause_before_ms}
    destination = paths.root / 'validation' / 'desktop-acceptance' / 'cache-report.json'
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
