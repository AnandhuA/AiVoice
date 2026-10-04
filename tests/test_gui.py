from malayalam_voice_studio.core.config import Paths
from malayalam_voice_studio.gui.main_window import MainWindow


def test_editor_and_manual_boundary(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(MainWindow, "hardware", lambda self: None)
    window = MainWindow(Paths(tmp_path))
    qtbot.addWidget(window)
    window.editor.editor.setPlainText("നീ... [PAUSE:400] ഇവിടെ വന്നത് എന്തിനാ?")
    window.analyze()
    assert window.table.rowCount() == 2
    window.table.selectRow(0)
    window.after.setValue(650)
    window.apply_pauses()
    assert window.project.segments[1].pause_before_ms == 650
    window.table.selectRow(1)
    assert window.before.value() == 650
    window.acting.fields["speed"].setValue(.9)
    window.apply_performance()
    assert window.project.segments[1].performance.speed == .9
    window.dirty = False


def test_stale_generation_rejected(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(MainWindow, "hardware", lambda self: None)
    window = MainWindow(Paths(tmp_path))
    qtbot.addWidget(window)
    window.editor.editor.setPlainText("നീ വരൂ")
    window.analyze()
    segment = window.project.segments[0]
    window.snapshot = {segment.id: window.fingerprint(segment)}
    segment.text = "നമുക്ക് പോകാം"
    window.generation_event("segment", {"id": segment.id})
    assert not segment.raw_path
    window.dirty = False


def test_backend_capability_controls(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(MainWindow, "hardware", lambda self: None)
    window = MainWindow(Paths(tmp_path))
    qtbot.addWidget(window)
    assert window.project.backend == 'praha'
    assert not window.character.fields['speaker'].isEnabled()
    assert window.acting.fields['cfg_weight'].isEnabled()
    window.backend.setCurrentText('parler')
    assert window.character.fields['speaker'].isEnabled()
    assert not window.acting.fields['cfg_weight'].isEnabled()
    window.dirty = False
