from copy import deepcopy
import json

import pytest

from malayalam_voice_studio.core.domain import Project, Segment
from malayalam_voice_studio.core.presets import characters
from malayalam_voice_studio.core.project_manager import load_project, save_project
from malayalam_voice_studio.core.segment_manager import merge, reorder, split
from malayalam_voice_studio.core.batch import import_batch


def project():
    return Project(characters=characters(), segments=[Segment("നീ വരൂ", "Arthur"), Segment("നമുക്ക് പോകാം", "Arthur", pause_before_ms=450)])


def test_project_roundtrip(tmp_path):
    scene = project()
    scene.segments[0].manual = True
    scene.segments[0].performance.emotion = "Suspicious"
    scene.tail_pause_ms = 321
    save_project(scene, tmp_path / "മലയാളം")
    restored, warnings = load_project(tmp_path / "മലയാളം")
    assert not warnings
    assert restored.to_dict() == scene.to_dict()


def test_asset_portability(tmp_path):
    scene = project()
    audio = tmp_path / "take.wav"
    audio.write_bytes(b"asset-data")
    scene.segments[0].raw_path = str(audio)
    destination = tmp_path / "scene"
    save_project(scene, destination)
    audio.unlink()
    restored, warnings = load_project(destination)
    assert not warnings
    assert restored.segments[0].raw_path.startswith(str(destination))


def test_missing_asset_warning(tmp_path):
    scene = project()
    save_project(scene, tmp_path)
    data = json.loads((tmp_path / "project.json").read_text(encoding="utf-8"))
    data["segments"][0]["raw_path"] = "audio/missing.wav"
    (tmp_path / "project.json").write_text(json.dumps(data), encoding="utf-8")
    restored, warnings = load_project(tmp_path)
    assert warnings
    assert restored.segments[0].status == "Missing audio"


def test_path_escape_rejected(tmp_path):
    scene = project()
    save_project(scene, tmp_path)
    data = json.loads((tmp_path / "project.json").read_text(encoding="utf-8"))
    data["characters"]["Arthur"]["reference"] = "../private.wav"
    (tmp_path / "project.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="escapes"):
        load_project(tmp_path)


def test_split_merge_reorder():
    scene = project()
    first = scene.segments[0].id
    split(scene, 0, 2)
    assert len(scene.segments) == 3
    assert scene.segments[1].id != first
    merge(scene, 0)
    assert scene.segments[0].text == "നീ വരൂ"
    reorder(scene, 0, 1)
    assert scene.segments[1].id == first


def test_batch_is_atomic(tmp_path):
    scene = project()
    before = deepcopy(scene.to_dict())
    file = tmp_path / "bad.csv"
    file.write_text('character,emotion,intensity,dialogue\nArthur,angry,80,നീ\nUnknown,calm,40,വരൂ', encoding="utf-8")
    with pytest.raises(ValueError, match="row 2"):
        import_batch(file, scene)
    assert scene.to_dict() == before


def test_batch_unicode_bom(tmp_path):
    file = tmp_path / "good.csv"
    file.write_text('character,emotion,intensity,dialogue\nArthur,angry,80,"നീ എന്താ ചെയ്യുന്നത്?"', encoding="utf-8-sig")
    scene = project()
    assert import_batch(file, scene) == 1
    assert scene.segments[-1].performance.intensity == .8
