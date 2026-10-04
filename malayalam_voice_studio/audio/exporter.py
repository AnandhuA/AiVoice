from pathlib import Path
from uuid import uuid4

import numpy as np
import soundfile as sf

from .processor import run_ffmpeg


def export_audio(audio: np.ndarray, path: Path, sample_rate: int = 48000, bit_depth: int = 24,
                 channels: int = 1, bitrate: int = 192, ffmpeg: str = "") -> None:
    if sample_rate not in (22050, 44100, 48000) or bit_depth not in (16, 24) or channels not in (1, 2):
        raise ValueError("Unsupported export settings.")
    if not len(audio) or not np.isfinite(audio).all():
        raise ValueError("Cannot export empty or invalid audio.")
    path.parent.mkdir(parents=True, exist_ok=True)
    audio = np.clip(audio, -1, 1)
    if channels == 2:
        audio = np.column_stack([audio, audio])
    temporary = path.parent / f".{uuid4().hex}.wav"
    try:
        sf.write(temporary, audio, sample_rate, subtype=f"PCM_{bit_depth}")
        if path.suffix.lower() == ".mp3":
            encoded = temporary.with_suffix(".mp3")
            try:
                run_ffmpeg(["-i", str(temporary), "-c:a", "libmp3lame", "-b:a", f"{bitrate}k", str(encoded)], ffmpeg)
                encoded.replace(path)
            finally:
                encoded.unlink(missing_ok=True)
        else:
            temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
