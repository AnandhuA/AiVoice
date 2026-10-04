"""Real inference acceptance check; never substitutes generated tones for speech."""
import argparse
import json
import os
from pathlib import Path
import time

import soundfile as sf

from malayalam_voice_studio.audio.exporter import export_audio
from malayalam_voice_studio.audio.mixer import mix
from malayalam_voice_studio.audio.processor import process_segment, master
from malayalam_voice_studio.core.acting_engine import analyze
from malayalam_voice_studio.core.config import Paths
from malayalam_voice_studio.core.domain import Project
from malayalam_voice_studio.core.presets import characters
from malayalam_voice_studio.core.project_manager import save_project, load_project
from malayalam_voice_studio.tts.base import GenerationRequest
from malayalam_voice_studio.tts.device import detect, resolve
from malayalam_voice_studio.tts.registry import create_backend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--device', choices=['Auto', 'CPU', 'CUDA'], default='Auto')
    parser.add_argument('--backend', choices=['praha', 'parler'], default='praha')
    args = parser.parse_args()
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    paths = Paths()
    os.environ['HF_HOME'] = str(paths.models / 'hf-cache')
    backend = create_backend(args.backend)
    device, _ = resolve(args.device, detect()['available'])
    backend.load(paths.models / args.backend, device)
    destination = paths.root / 'validation' / 'real-audio'
    destination.mkdir(parents=True, exist_ok=True)
    scene = Project(characters=characters(), backend=args.backend)
    scene.original = 'നീ... [PAUSE:400] ഇവിടെ വന്നത് എന്തിനാ?'
    result = analyze(scene.original, 'Arthur', scene.characters['Arthur'].performance)
    scene.segments, scene.tail_pause_ms = result.segments, result.tail_pause_ms
    started = time.monotonic()
    for i, segment in enumerate(scene.segments):
        output = backend.synthesize(GenerationRequest(segment, scene.characters['Arthur']), lambda: False)
        raw, processed = destination / f'segment_{i + 1:03}.wav', destination / f'processed_{i + 1:03}.wav'
        sf.write(raw, output.samples, output.sample_rate, subtype='FLOAT')
        segment.duration = process_segment(raw, processed, segment.performance)
        segment.raw_path, segment.processed_path = str(raw), str(processed)
        segment.status = 'Ready'
    audio = master(mix(scene), 48000, scene.effects, paths.cache / 'temporary')
    export_audio(audio, destination / 'dialogue.wav')
    save_project(scene, destination / 'project')
    restored, warnings = load_project(destination / 'project')
    assert not warnings and len(restored.segments) == len(scene.segments)
    import torch
    report = {'device': device, 'generation_seconds': time.monotonic() - started,
              'audio_seconds': len(audio) / 48000,
              'peak_cuda_gb': torch.cuda.max_memory_allocated() / 1024**3 if device.startswith('cuda') else 0,
              'listening_review': 'Required: intelligibility, naturalness, continuity, emotional delivery.'}
    (destination / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    backend.unload()


if __name__ == '__main__':
    main()
