import json
import os
from pathlib import Path
import subprocess
import imageio_ffmpeg
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
from faster_whisper import WhisperModel
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'exports' / 'rdr2_malayalam'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = next(Path(r'C:\Users\Anandhu\Videos\NVIDIA\Red Dead Redemption 2').glob('*.mp4'))
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-i', str(SOURCE), '-vn', '-ar', '16000', '-ac', '1', str(OUT / 'source_audio.wav')], check=True, capture_output=True)
os.environ['HF_HUB_DISABLE_XET'] = '1'
model = WhisperModel('small.en', device='cpu', compute_type='int8', download_root=str(ROOT / 'models' / 'whisper'), cpu_threads=8)
audio, _ = sf.read(OUT / 'source_audio.wav', dtype='float32')
segments, info = model.transcribe(audio, language='en', beam_size=5, vad_filter=True, word_timestamps=True)
rows = []
for s in segments:
    row = {'start': round(s.words[0].start if s.words else s.start, 3), 'end': round(s.words[-1].end if s.words else s.end, 3), 'english': s.text.strip(), 'words': [{'word': w.word, 'start': w.start, 'end': w.end} for w in (s.words or [])]}
    rows.append(row)
    print(json.dumps(row), flush=True)
(OUT / 'english_transcript.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
print('TRANSCRIPTION COMPLETE', flush=True)
