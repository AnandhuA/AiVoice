import os
from pathlib import Path
import json
import subprocess
ROOT = Path(__file__).resolve().parents[1]
os.environ['HF_HOME'] = str(ROOT / 'models' / 'hf-cache')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import imageio_ffmpeg
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from malayalam_voice_studio.core.domain import Character, Segment, Performance
from malayalam_voice_studio.tts.base import GenerationRequest
from malayalam_voice_studio.tts.registry import create_backend
OUT = ROOT / 'exports' / 'rdr2_malayalam' / 'youtube_references'
text = 'ഇതൊരു നല്ല ആശയം തന്നെയാ. നിനക്കിങ്ങനെയൊരു ബുദ്ധി തോന്നുന്നത് ആദ്യമായിട്ടാണെന്ന് തോന്നുന്നു.'
report = []
backend = create_backend('praha')
print('Loading model for two linked voice references...', flush=True)
backend.load(ROOT / 'models' / 'praha', 'cuda')
for i, ident in enumerate(['wHiIyNtd3EY', '_3Lz5ex55F4'], 1):
    reference = OUT / f'arthur_short_{i}_reference.wav'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-ss', '0', '-i', str(OUT / (ident+'.webm')), '-t', '8', '-ar', '24000', '-ac', '1', '-af', 'highpass=f=75,lowpass=f=10000,afftdn=nr=6', str(reference)], capture_output=True, check=True)
    character = Character(name='Arthur', reference=str(reference))
    segment = Segment(text=text, character='Arthur', seed=42, performance=Performance(intensity=0.35, cfg_weight=0.5))
    result = backend.synthesize(GenerationRequest(segment, character), lambda: False)
    audio = resample_poly(result.samples, 48000, result.sample_rate)
    assert len(audio) and np.isfinite(audio).all()
    peak = np.max(np.abs(audio))
    if peak:
        audio *= .89 / peak
    dest = OUT / f'arthur_short_{i}_malayalam_preview.wav'
    sf.write(dest, audio, 48000, subtype='PCM_24')
    report.append({'source': f'https://www.youtube.com/shorts/{ident}', 'creator': 'VISHNU VIJAYAN', 'reference_range': [0,8], 'reference':reference.name,'preview':dest.name,'text':text,'duration':len(audio)/48000,'review':'Experimental reference-conditioned preview. Listening review required; background music/other voices may affect conditioning.'})
    print(json.dumps(report[-1], ensure_ascii=True), flush=True)
(OUT / 'shorts_preview_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
backend.unload()
print('COMPLETE', flush=True)
