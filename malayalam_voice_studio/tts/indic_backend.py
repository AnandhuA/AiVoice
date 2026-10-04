from pathlib import Path
from typing import Callable

import numpy as np

from .base import AudioResult, Capabilities, GenerationRequest, LocalTTSBackend


class IndicF5Backend(LocalTTSBackend):
    capabilities = Capabilities(reference=True)

    def load(self, model_dir: Path, device: str) -> None:
        self.validate(model_dir)
        try:
            from transformers import AutoModel
            import f5_tts  # noqa: F401
        except ImportError as exc:
            raise ValueError("IndicF5 optional dependencies are missing. See README for its isolated setup.") from exc
        # Only an explicitly installed, pinned local repository can execute custom model code.
        self.model = AutoModel.from_pretrained(str(model_dir), trust_remote_code=True,
                                             local_files_only=True).to(device).eval()

    def synthesize(self, request: GenerationRequest, cancelled: Callable[[], bool]) -> AudioResult:
        import torch
        c = request.character
        if not c.reference or not Path(c.reference).is_file() or not c.reference_text.strip():
            raise ValueError("IndicF5 requires a valid reference WAV and its exact transcript.")
        if cancelled():
            raise InterruptedError("Generation cancelled.")
        torch.manual_seed(request.segment.seed)
        with torch.inference_mode():
            output = self.model(request.segment.text, ref_audio_path=c.reference, ref_text=c.reference_text)
        if cancelled():
            raise InterruptedError("Generation cancelled.")
        audio = np.asarray(output)
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768
        return AudioResult(audio.astype(np.float32).squeeze(), 24000)
