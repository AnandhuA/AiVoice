from queue import Queue
from threading import Event

import numpy as np
import pytest

from malayalam_voice_studio.core.domain import Project, Segment
from malayalam_voice_studio.core.jobs import generation_worker, friendly_error
from malayalam_voice_studio.core.presets import characters
from malayalam_voice_studio.tts.base import AudioResult, LocalTTSBackend


class InstrumentedBackend(LocalTTSBackend):
    """Test-only DSP input; never registered with the production backend registry."""
    def load(self, model_dir, device):
        self.device = device

    def synthesize(self, request, cancelled):
        if request.segment.text == 'FAIL':
            raise ValueError('Intentional test failure')
        return AudioResult(np.full(1000, .1, dtype=np.float32), 22050)


def test_cancel_before_model_loading(tmp_path, monkeypatch):
    from malayalam_voice_studio.tts import device
    monkeypatch.setattr(device, 'detect', lambda: {'available': False})
    events, cancel = Queue(), Event()
    cancel.set()
    scene = Project(characters=characters(), segments=[Segment('നീ', 'Arthur')])
    generation_worker(scene.to_dict(), str(tmp_path), str(tmp_path), 'Auto', '',
                      [scene.segments[0].id], False, events, cancel)
    messages = list(events.queue)
    assert any(kind == 'cancelled' for kind, _ in messages)
    assert not any(kind == 'segment' for kind, _ in messages)


def test_memory_error_has_recovery():
    assert 'CPU' in friendly_error(RuntimeError('CUDA out of memory'))
    assert 'RAM' in friendly_error(MemoryError())
