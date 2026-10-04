from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from ..core.domain import Character, Segment


@dataclass(frozen=True)
class Capabilities:
    languages: tuple[str, ...] = ("ml",)
    reference: bool = False
    emotion_prompt: bool = False
    ssml: bool = False
    word_timestamps: bool = False


@dataclass
class GenerationRequest:
    segment: Segment
    character: Character


@dataclass
class AudioResult:
    samples: np.ndarray
    sample_rate: int


class TTSBackend(ABC):
    capabilities = Capabilities()

    def validate(self, model_dir: Path) -> None:
        if not (model_dir / "config.json").is_file():
            raise ValueError("Model missing. Install it from Models, or choose an installed model.")

    @abstractmethod
    def load(self, model_dir: Path, device: str) -> None: ...

    @abstractmethod
    def synthesize(self, request: GenerationRequest, cancelled: Callable[[], bool]) -> AudioResult: ...

    def unload(self) -> None:
        if hasattr(self, "model"):
            del self.model
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


class MalayalamTTSBackend(TTSBackend):
    """Backends accepting Malayalam input with declared capabilities."""


class LocalTTSBackend(MalayalamTTSBackend):
    """On-device inference; model loading must not make network requests."""


class ExternalTTSBackend(TTSBackend):
    """Extension boundary for a future explicitly configured external provider."""
