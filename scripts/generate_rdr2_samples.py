import json
import os
from pathlib import Path
import time
os.environ['HF_HOME'] = str(Path(__file__).resolve().parents[1] / 'models' / 'hf-cache')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import soundfile as sf
import numpy as np
from scipy.signal import resample_poly
from malayalam_voice_studio.core.domain import Character, Segment, Performance
from malayalam_voice_studio.tts.base import GenerationRequest
from malayalam_voice_studio.tts.registry import create_backend

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'exports' / 'rdr2_malayalam'
backend = create_backend('praha')
backend.load(ROOT / 'models' / 'praha', 'cuda')
samples = [('john', 'അത് റെയിൽപ്പാളത്തിൽ നിർത്താം. നിർത്തിയില്ലെങ്കിൽ ചാകുമെന്ന് അവർക്കറിയാം.'), ('arthur', 'ഇതൊരു നല്ല ആശയം തന്നെയാ. നിനക്കിങ്ങനെയൊരു ബുദ്ധി തോന്നുന്നത് ആദ്യമായിട്ടാണെന്ന് തോന്നുന്നു.')]
report = []
for name, text in samples:
    started = time.monotonic()
    character = Character(name=name.title(), reference=str(OUT / (name+'_reference.wav')))
    segment = Segment(text=text, character=character.name, performance=Performance(intensity=0.45, cfg_weight=0.5))
    result = backend.synthesize(GenerationRequest(segment, character), lambda: False)
    audio = resample_poly(result.samples, 48000, result.sample_rate)
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio * (0.89 / peak)
    path = OUT / (name+'_malayalam_sample.wav')
    sf.write(path, audio, 48000, subtype='PCM_24')
    report.append({'character': character.name, 'text': text, 'file': path.name, 'seconds': len(audio)/48000, 'generation_seconds': time.monotonic()-started, 'review': 'Pronunciation, voice similarity, and acting need listening review.'})
    print(json.dumps(report[-1], ensure_ascii=True), flush=True)
(OUT / 'sample_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
backend.unload()
