from copy import deepcopy
import json

import pytest

from malayalam_voice_studio.core.domain import Project, Segment
from malayalam_voice_studio.core.jobs import synthesis_key
from malayalam_voice_studio.core.presets import characters
from malayalam_voice_studio.tts.registry import create_backend
from malayalam_voice_studio.tts.model_manager import inspect_install


def test_praha_declares_reference_without_prompt_emotions():
    backend = create_backend('praha')
    assert backend.capabilities.reference
    assert not backend.capabilities.emotion_prompt
    assert not backend.capabilities.ssml


def test_praha_requires_base_and_adapter(tmp_path):
    (tmp_path / 'adapter_config.json').write_text('{}')
    with pytest.raises(ValueError, match='base/t3_cfg'):
        create_backend('praha').validate(tmp_path)


def test_praha_cache_native_controls_and_reference(tmp_path):
    project = Project(backend='praha', characters=characters(), segments=[Segment('നീ വരൂ', 'Arthur')])
    segment = project.segments[0]
    original = synthesis_key(project, segment, 'revision')
    segment.performance.emotion = 'Angry'
    assert synthesis_key(project, segment, 'revision') == original
    segment.performance.intensity = .9
    assert synthesis_key(project, segment, 'revision') != original
    original = synthesis_key(project, segment, 'revision')
    segment.performance.cfg_weight = .1
    assert synthesis_key(project, segment, 'revision') != original
    reference = tmp_path / 'reference.wav'
    reference.write_bytes(b'reference-one')
    project.characters['Arthur'].reference = str(reference)
    original = synthesis_key(project, segment, 'revision')
    reference.write_bytes(b'reference-two')
    assert synthesis_key(project, segment, 'revision') != original


def test_installed_manifest_requires_files(tmp_path):
    directory = tmp_path / 'praha'
    directory.mkdir()
    (directory / 'studio-model.json').write_text(json.dumps({'files': [{'target': '', 'file': 'missing.safetensors'}]}))
    assert not inspect_install(tmp_path, 'praha')['installed']
