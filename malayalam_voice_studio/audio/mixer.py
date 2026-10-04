from pathlib import Path

import numpy as np

from ..core.domain import Project
from .processor import read_audio, resample


def silence(milliseconds: int, rate: int) -> np.ndarray:
    if not 0 <= milliseconds <= 60000:
        raise ValueError("Pause must be 0–60000 ms.")
    return np.zeros(round(milliseconds * rate / 1000), dtype=np.float32)


def mix(project: Project, rate: int = 48000, processed: bool = True) -> np.ndarray:
    chunks = []
    for segment in project.segments:
        path = segment.processed_path if processed else segment.raw_path
        if not path or not Path(path).is_file():
            raise ValueError(f"Generate segment first: {segment.text[:40]}")
        chunks.append(silence(segment.pause_before_ms, rate))
        if processed and segment.performance.breath != "None":
            breath_path = project.breath_assets.get(segment.performance.breath)
            if not breath_path:
                raise ValueError(f"Import a {segment.performance.breath.lower()} breath asset in the Effects panel.")
            breath, br = read_audio(Path(breath_path))
            chunks.append(resample(breath, br, rate) * .35)
        audio, ar = read_audio(Path(path))
        chunks.append(resample(audio, ar, rate))
    if not chunks:
        raise ValueError("Add dialogue before previewing or exporting.")
    chunks.append(silence(project.tail_pause_ms, rate))
    return np.concatenate(chunks)
