from __future__ import annotations

import math
from pathlib import Path
import subprocess
from uuid import uuid4

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from ..core.config import find_ffmpeg
from ..core.domain import Effects, Performance


def read_audio(path: Path) -> tuple[np.ndarray, int]:
    try:
        audio, rate = sf.read(path, dtype="float32", always_2d=True)
    except Exception as exc:
        raise ValueError(f"Invalid audio: {path.name}. Import WAV, FLAC or convert with FFmpeg.") from exc
    if not len(audio) or not np.isfinite(audio).all() or rate < 8000:
        raise ValueError("Audio is empty, non-finite, or has an invalid sample rate.")
    return audio.mean(axis=1), rate


def resample(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate:
        return audio.copy()
    divisor = math.gcd(source_rate, target_rate)
    return resample_poly(audio, target_rate // divisor, source_rate // divisor).astype(np.float32)


def run_ffmpeg(args: list[str], executable: str = "", timeout: int = 120) -> None:
    try:
        result = subprocess.run([find_ffmpeg(executable), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("FFmpeg missing or unavailable. Set a working executable in Settings or run setup.ps1.") from exc
    if result.returncode:
        raise ValueError(f"FFmpeg failed: {result.stderr[-2000:]}")


def tempo_filters(speed: float) -> list[str]:
    filters = []
    while speed < .5:
        filters.append("atempo=0.5")
        speed /= .5
    while speed > 2:
        filters.append("atempo=2")
        speed /= 2
    filters.append(f"atempo={speed:.8f}")
    return filters


def process_segment(source: Path, destination: Path, performance: Performance, ffmpeg: str = "") -> float:
    performance.validate()
    audio, rate = read_audio(source)
    filters = []
    factor = 2 ** (performance.pitch / 12)
    if performance.pitch:
        filters.extend([f"asetrate={rate * factor:.6f}", f"aresample={rate}"])
    if performance.speed != 1 or performance.pitch:
        filters.extend(tempo_filters(performance.speed / factor))
    temporary = destination.with_name(destination.stem + ".processing.wav")
    try:
        if filters:
            run_ffmpeg(["-i", str(source), "-af", ",".join(filters), "-c:a", "pcm_f32le", str(temporary)], ffmpeg)
            audio, rate = read_audio(temporary)
        # Energy is an approximate amplitude control, not a claim of native acting support.
        gain_db = performance.volume_db + (performance.energy - .7) * 8
        # Markup produces a dedicated emphasized phrase. This is phrase gain,
        # not forced word alignment or a claim of native emotional control.
        if performance.emphasis:
            gain_db += 1.5 * performance.intensity
        audio *= 10 ** (gain_db / 20)
        fade = min(round(rate * .005), len(audio) // 2)
        if fade:
            ramp = np.linspace(0, 1, fade, dtype=np.float32)
            audio[:fade] *= ramp
            audio[-fade:] *= ramp[::-1]
        destination.parent.mkdir(parents=True, exist_ok=True)
        sf.write(destination, audio, rate, subtype="FLOAT")
    finally:
        temporary.unlink(missing_ok=True)
    return len(audio) / rate


def master(audio: np.ndarray, rate: int, effects: Effects, cache: Path, ffmpeg: str = "") -> np.ndarray:
    filters = []
    if effects.highpass:
        filters.append("highpass=f=70")
    if effects.lowpass:
        filters.append("lowpass=f=14000")
    if effects.eq:
        filters.append("equalizer=f=2500:t=q:w=1:g=1.5")
    if effects.compression:
        filters.append("acompressor=threshold=0.18:ratio=2:attack=15:release=150:makeup=1")
    if effects.noise_reduction:
        filters.append("afftdn=nr=6:nf=-45")
    if effects.reverb:
        filters.append("aecho=0.9:0.9:35|65:0.06|0.03")
    if effects.saturation:
        audio = np.tanh(audio * 1.15) / 1.15
    if filters:
        cache.mkdir(parents=True, exist_ok=True)
        name = uuid4().hex
        source, target = cache / f"{name}-in.wav", cache / f"{name}-out.wav"
        try:
            sf.write(source, audio, rate, subtype="FLOAT")
            run_ffmpeg(["-i", str(source), "-af", ",".join(filters), "-c:a", "pcm_f32le", str(target)], ffmpeg)
            audio, rate = read_audio(target)
        finally:
            source.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
    if effects.ambience:
        ambience, ar = read_audio(Path(effects.ambience))
        ambience = resample(ambience, ar, rate)
        ambience = np.resize(ambience, len(audio))
        audio = audio + ambience * 10 ** (effects.ambience_db / 20)
    peak = float(np.max(np.abs(audio))) if len(audio) else 0
    target_peak = 10 ** (-1 / 20)
    if effects.normalize and peak > 0:
        audio = audio * min(target_peak / peak, 4)
    # Final peak ceiling. Global scaling preserves relative delivery levels.
    peak = float(np.max(np.abs(audio))) if len(audio) else 0
    if peak > target_peak:
        audio = audio * target_peak / peak
    return audio.astype(np.float32)
