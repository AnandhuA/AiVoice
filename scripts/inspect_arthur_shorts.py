import os
from pathlib import Path
import json
import subprocess
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
os.environ['HF_HUB_DISABLE_XET'] = '1'
import imageio_ffmpeg
import soundfile as sf
from faster_whisper import WhisperModel
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'exports' / 'rdr2_malayalam' / 'youtube_references'
model = WhisperModel('base', device='cpu', compute_type='int8', download_root=str(ROOT / 'models' / 'whisper'), cpu_threads=4)
for ident in ['wHiIyNtd3EY', '_3Lz5ex55F4']:
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-i', str(OUT / (ident+'.webm')), '-ar', '16000', '-ac', '1', str(OUT / (ident+'.wav'))], capture_output=True, check=True)
    audio, sr = sf.read(OUT / (ident+'.wav'), dtype='float32')
    segments, _ = model.transcribe(audio, language='ml', word_timestamps=True, vad_filter=True)
    rows = [{'start':s.start,'end':s.end,'text':s.text,'words':[{'text':w.word,'start':w.start,'end':w.end} for w in s.words]} for s in segments]
    (OUT / (ident+'_transcript.json')).write_text(json.dumps(rows, indent=2), encoding='utf-8')
    print(ident, json.dumps(rows), flush=True)
