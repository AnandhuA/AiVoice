from __future__ import annotations

from dataclasses import asdict
import json
import logging
import os
from pathlib import Path
import traceback

import numpy as np
import soundfile as sf

from .domain import Project, digest
from ..tts.parler_backend import description
from ..tts.base import GenerationRequest


def synthesis_key(project: Project, segment, model_revision: str) -> str:
    character = project.characters[segment.character]
    request = GenerationRequest(segment, character)
    reference_hash = ""
    if project.backend in ("indicf5", "praha") and character.reference:
        from hashlib import sha256
        reference_hash = sha256(Path(character.reference).read_bytes()).hexdigest()
    return digest({"text": segment.text, "backend": project.backend, "revision": model_revision,
        "seed": segment.seed, "description": description(request) if project.backend == "parler" else "",
        "reference": reference_hash, "reference_text": character.reference_text if project.backend == "indicf5" else "",
        "exaggeration": segment.performance.intensity if project.backend == "praha" else None,
        "cfg_weight": segment.performance.cfg_weight if project.backend == "praha" else None})


def generation_worker(payload: dict, model_root: str, cache: str, device_choice: str, ffmpeg: str,
                      selected: list[str], force: bool, events, cancel) -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HOME"] = str(Path(model_root) / "hf-cache")
    backend = None
    try:
        from ..audio.processor import process_segment
        from ..tts.device import detect, resolve
        from ..tts.registry import create_backend
        project = Project.from_dict(payload)
        folder = Path(model_root) / project.backend
        manifest = folder / "studio-model.json"
        revision = digest(json.loads(manifest.read_text(encoding="utf-8"))) if manifest.exists() else "local-unversioned"
        device, message = resolve(device_choice, detect()["available"])
        events.put(("message", message))
        backend = create_backend(project.backend)
        destination = Path(cache) / "takes"
        destination.mkdir(parents=True, exist_ok=True)
        targets = [s for s in project.segments if s.id in selected]
        loaded = False
        for index, segment in enumerate(targets):
            if cancel.is_set():
                raise InterruptedError("Generation cancelled. Completed segments are retained.")
            try:
                key = synthesis_key(project, segment, revision)
                raw = Path(segment.raw_path) if segment.raw_path and segment.audio_key == key else destination / f"{key}.wav"
                if force:
                    from uuid import uuid4
                    raw = destination / f"{key}-{uuid4().hex[:8]}.wav"
                events.put(("message", f"Generating {index + 1}/{len(targets)}: {segment.text[:36]}"))
                if not raw.exists() or force:
                    if not loaded:
                        try:
                            backend.load(folder, device)
                        except RuntimeError as exc:
                            if device_choice != "Auto" or "out of memory" not in str(exc).lower():
                                raise
                            backend.unload()
                            import torch
                            torch.cuda.empty_cache()
                            device = "cpu"
                            events.put(("message", "GPU memory exhausted; retrying on CPU."))
                            backend.load(folder, device)
                        loaded = True
                    request = GenerationRequest(segment, project.characters[segment.character])
                    try:
                        result = backend.synthesize(request, cancel.is_set)
                    except RuntimeError as exc:
                        if device_choice != "Auto" or device == "cpu" or "out of memory" not in str(exc).lower():
                            raise
                        backend.unload()
                        import gc
                        import torch
                        gc.collect()
                        torch.cuda.empty_cache()
                        device = "cpu"
                        events.put(("message", "GPU memory exhausted during synthesis; retrying this phrase on CPU."))
                        backend.load(folder, device)
                        result = backend.synthesize(request, cancel.is_set)
                    if result.samples.ndim != 1 or not len(result.samples) or not np.isfinite(result.samples).all():
                        raise ValueError("Model returned invalid or empty audio. Shorten the phrase and retry.")
                    temporary = raw.with_suffix(".tmp.wav")
                    sf.write(temporary, result.samples, result.sample_rate, subtype="FLOAT")
                    temporary.replace(raw)
                processed = destination / f"{raw.stem}-{digest(asdict(segment.performance))[:16]}.wav"
                duration = process_segment(raw, processed, segment.performance, ffmpeg)
                events.put(("segment", {"id": segment.id, "raw_path": str(raw), "processed_path": str(processed),
                    "audio_key": key, "duration": duration, "status": "Ready", "revision": revision}))
                if loaded:
                    from .config import atomic_json
                    from datetime import datetime, timezone
                    import torch
                    atomic_json(folder / "validation.json", {"validated_at": datetime.now(timezone.utc).isoformat(),
                        "device": device, "torch": torch.__version__, "status": "Real synthesis succeeded",
                        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 3) if device.startswith("cuda") else 0,
                        "listening_review": "Not established by automated synthesis"})
            except InterruptedError:
                raise
            except Exception as exc:
                events.put(("failed", {"id": segment.id, "error": friendly_error(exc), "trace": traceback.format_exc()}))
            events.put(("progress", round((index + 1) / len(targets) * 100)))
        events.put(("done", None))
    except InterruptedError as exc:
        events.put(("cancelled", str(exc)))
    except Exception as exc:
        events.put(("error", friendly_error(exc)))
        events.put(("trace", traceback.format_exc()))
    finally:
        if backend:
            backend.unload()


def friendly_error(exc: Exception) -> str:
    text = str(exc)
    if "out of memory" in text.lower():
        return "Memory exhausted. Close GPU applications, shorten segments, or select CPU and retry. " + text
    if isinstance(exc, MemoryError):
        return "System RAM exhausted. Close other applications and generate fewer lines at once."
    if "403" in text or "401" in text or "gated" in text.lower():
        return "Model access denied. Accept the model terms on Hugging Face and authenticate locally. " + text
    return text
