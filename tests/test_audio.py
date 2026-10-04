import numpy as np
import pytest
import soundfile as sf

from malayalam_voice_studio.audio.exporter import export_audio
from malayalam_voice_studio.audio.mixer import mix, silence
from malayalam_voice_studio.audio.processor import master, process_segment, read_audio, resample
from malayalam_voice_studio.core.domain import Effects, Performance, Project, Segment


def test_exact_silence_and_duration(tmp_path):
    file = tmp_path / "tone.wav"
    sf.write(file, np.full(1000, .2), 22050, subtype="FLOAT")
    scene = Project(segments=[Segment("a", raw_path=str(file), pause_before_ms=450),
                              Segment("b", raw_path=str(file), pause_before_ms=250)], tail_pause_ms=100)
    audio = mix(scene, 22050, False)
    assert len(audio) == 2000 + round(.45 * 22050) + round(.25 * 22050) + round(.1 * 22050)
    assert not np.any(audio[:round(.45 * 22050)])


def test_limiter_preserves_relative_gain(tmp_path):
    audio = np.array([.2, .4, 1.5, -1.5], dtype=np.float32)
    output = master(audio, 48000, Effects(), tmp_path)
    assert np.max(np.abs(output)) <= .892
    assert output[1] / output[0] == pytest.approx(2)


@pytest.mark.parametrize("rate", [22050, 44100, 48000])
@pytest.mark.parametrize("depth", [16, 24])
@pytest.mark.parametrize("channels", [1, 2])
def test_export_metadata(tmp_path, rate, depth, channels):
    file = tmp_path / "export.wav"
    export_audio(np.zeros(rate), file, rate, depth, channels)
    info = sf.info(file)
    assert (info.samplerate, info.subtype, info.channels) == (rate, f"PCM_{depth}", channels)


def test_invalid_audio(tmp_path):
    path = tmp_path / "broken.wav"
    path.write_text("invalid")
    with pytest.raises(ValueError, match="Invalid audio"):
        read_audio(path)


@pytest.mark.parametrize("speed,pitch,expected_hz", [(1, 12, 880), (1.5, 0, 440), (.8, -12, 220)])
def test_tempo_pitch_independent(tmp_path, speed, pitch, expected_hz):
    rate = 48000
    t = np.arange(rate * 2) / rate
    source, target = tmp_path / "source.wav", tmp_path / "processed.wav"
    sf.write(source, .2 * np.sin(2 * np.pi * 440 * t), rate)
    duration = process_segment(source, target, Performance(speed=speed, pitch=pitch))
    audio, _ = read_audio(target)
    assert duration == pytest.approx(2 / speed, abs=.08)
    spectrum = np.abs(np.fft.rfft(audio))
    frequency = np.argmax(spectrum) * rate / len(audio)
    assert frequency == pytest.approx(expected_hz, abs=5)


def test_missing_ffmpeg_actionable(tmp_path):
    source = tmp_path / "a.wav"
    sf.write(source, np.zeros(22050), 22050)
    with pytest.raises(ValueError, match="FFmpeg"):
        process_segment(source, tmp_path / "b.wav", Performance(speed=1.1), str(tmp_path / "missing.exe"))


def test_missing_breath_asset(tmp_path):
    source = tmp_path / "a.wav"
    sf.write(source, np.zeros(22050), 22050)
    scene = Project(segments=[Segment("a", processed_path=str(source), performance=Performance(breath="Short"))])
    with pytest.raises(ValueError, match="breath asset"):
        mix(scene)
