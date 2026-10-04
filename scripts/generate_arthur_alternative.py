import os
from pathlib import Path
import json
import time
ROOT = Path(__file__).resolve().parents[1]
os.environ['HF_HOME'] = str(ROOT / 'models' / 'hf-cache')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from malayalam_voice_studio.core.domain import Character, Segment, Performance
from malayalam_voice_studio.audio.processor import process_segment
from malayalam_voice_studio.tts.registry import create_backend
from malayalam_voice_studio.tts.base import GenerationRequest

OUT = ROOT / 'exports' / 'rdr2_malayalam' / 'arthur_alternative'
OUT.mkdir(parents=True, exist_ok=True)
backend = create_backend('praha')
print('Loading local Malayalam speech model...', flush=True)
backend.load(ROOT / 'models' / 'praha', 'cuda')

def synthesize(text, reference, filename, seed):
    character = Character(name='Arthur alternative', reference=str(reference) if reference else '')
    segment = Segment(text=text, character=character.name, seed=seed, performance=Performance(intensity=0.3, cfg_weight=0.5))
    result = backend.synthesize(GenerationRequest(segment, character), lambda: False)
    sf.write(OUT / filename, result.samples, result.sample_rate, subtype='FLOAT')
    return OUT / filename

def finish(source, destination):
    audio, rate = sf.read(source, dtype='float32')
    audio = resample_poly(audio, 48000, rate)
    assert len(audio) and np.isfinite(audio).all()
    peak = np.max(np.abs(audio))
    if peak:
        audio *= 0.89 / peak
    sf.write(destination, audio, 48000, subtype='PCM_24')
    return len(audio) / 48000

reference_text = 'ഇതൊരു നല്ല ആശയം തന്നെയാ. പക്ഷേ നമ്മൾ സൂക്ഷിക്കണം. ആദ്യം വേണ്ട സാധനങ്ങൾ ഒരുക്കാം. ബാക്കി കാര്യങ്ങൾ പിന്നെ നോക്കാം.'
raw_reference = synthesize(reference_text, None, 'reference_raw.wav', 73)
process_segment(raw_reference, OUT / 'reference_deep_float.wav', Performance(pitch=-1.7, speed=0.97))
finish(OUT / 'reference_deep_float.wav', OUT / 'arthur_original_deep_reference.wav')
print('New original Malayalam reference created.', flush=True)
test_text = 'ഇതൊരു നല്ല ആശയം തന്നെയാ. നിനക്കിങ്ങനെയൊരു ബുദ്ധി തോന്നുന്നത് ആദ്യമായിട്ടാണെന്ന് തോന്നുന്നു.'
raw_test = synthesize(test_text, OUT / 'arthur_original_deep_reference.wav', 'test_raw.wav', 73)
natural_duration = finish(raw_test, OUT / 'arthur_new_voice_natural.wav')
process_segment(raw_test, OUT / 'test_deep_float.wav', Performance(pitch=-1.0, speed=0.96))
deep_duration = finish(OUT / 'test_deep_float.wav', OUT / 'arthur_new_voice_deep.wav')
report = {'reference_origin': 'Locally generated original Malayalam speech using Praha built-in conditioning; no actor recording used.', 'reference_text': reference_text, 'test_text': test_text, 'natural_seconds': natural_duration, 'deep_seconds': deep_duration, 'reference_pitch_semitones': -1.7, 'deep_preview_additional_pitch_semitones': -1.0, 'review': 'Listening review required for pronunciation and suitability. Synthetic reference conditioning is experimental.'}
(OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
backend.unload()
print('COMPLETE: two new Arthur voice previews and reusable reference.', flush=True)
