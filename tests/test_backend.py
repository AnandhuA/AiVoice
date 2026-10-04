import pytest

from malayalam_voice_studio.core.domain import Project, Segment
from malayalam_voice_studio.core.jobs import synthesis_key
from malayalam_voice_studio.core.presets import characters
from malayalam_voice_studio.tts.device import resolve
from malayalam_voice_studio.tts.registry import create_backend


def test_cache_excludes_postprocessing():
    scene = Project(characters=characters(), segments=[Segment("നീ", "Arthur")])
    segment = scene.segments[0]
    key = synthesis_key(scene, segment, "revision")
    segment.pause_before_ms = 800
    segment.performance.speed = .8
    segment.performance.pitch = -2
    segment.performance.volume_db = -3
    assert synthesis_key(scene, segment, "revision") == key
    segment.performance.emotion = "Angry"
    assert synthesis_key(scene, segment, "revision") != key


def test_missing_model(tmp_path):
    with pytest.raises(ValueError, match="Model missing"):
        create_backend("parler").validate(tmp_path)


def test_xtts_language_guard():
    with pytest.raises(ValueError, match="does not support Malayalam"):
        create_backend("xtts")


def test_device_fallback():
    assert resolve("Auto", False)[0] == "cpu"
    assert resolve("Auto", True)[0] == "cuda:0"
    assert resolve("CPU", True)[0] == "cpu"
    with pytest.raises(ValueError, match="CUDA unavailable"):
        resolve("CUDA", False)
