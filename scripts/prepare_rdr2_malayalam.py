import csv
import json
import subprocess
from pathlib import Path
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'exports' / 'rdr2_malayalam'
rows = json.loads((OUT / 'english_transcript.json').read_text(encoding='utf-8'))
translations = [
'പെട്ടെന്ന് തീപിടിക്കുന്ന എന്തെങ്കിലും നിറച്ചൊരു വണ്ടി വേണം. എണ്ണ!',
'അത് റെയിൽപ്പാളത്തിൽ നിർത്താം. അവരത് കാണും.',
'അപ്പോൾ നിർത്തിയില്ലെങ്കിൽ ചാകുമെന്ന് അവർക്കറിയാം.',
'ഒരു ട്രെയിൻ ഡ്രൈവർക്കും ജീവനോടെ വെന്തുചാകാൻ ആഗ്രഹമുണ്ടാവില്ല.',
'കൊള്ളാമല്ലോ ഈ ബുദ്ധി.',
'നിന്റെ നിലവാരം വെച്ച് നോക്കുമ്പോൾ!',
'ഇതൊരു നല്ല ആശയം തന്നെയാ.',
'നിനക്കിങ്ങനെയൊരു ബുദ്ധി തോന്നുന്നത് ആദ്യമായിട്ടാണെന്ന് തോന്നുന്നു.',
'ഒന്ന് മിണ്ടാതിരിയെടാ.',
'നീയായിരിക്കും ആദ്യത്തെ തെണ്ടി,',
'ചെന്നായ തലച്ചോറിന്റെ പകുതി തിന്നിട്ടും,',
'ബുദ്ധി കൂടിയവൻ!',
'അപ്പോൾ നമ്മളിത് ചെയ്യുന്നുണ്ടോ?',
'ഉവ്വ്. വെടിയുണ്ടകളും തോക്കുകളും വേണം.',
'കണ്ടാൽ പേടി തോന്നണം. ട്രെയിൻ പൊളിക്കാൻ കുറച്ച് ഡൈനാമൈറ്റും വേണം.',
'സാധനങ്ങൾ ഞാൻ കൊണ്ടുവരാം.',
'എന്തായാലും അബിഗെയിലിനുവേണ്ടി ടൗണിൽ പോകാനുണ്ട്.',
'അതെന്തിനാണെന്ന് ചോദിക്കണ്ട.',
'നീ നമുക്കൊരു എണ്ണവണ്ടി കണ്ടുപിടിക്ക്.',
'ആ, പറ്റിയൊരു സ്ഥലം എനിക്കറിയാം.',
'ആ എണ്ണശുദ്ധീകരണശാലയിലേക്ക് വണ്ടികൾ എപ്പോഴും പോകുന്നുണ്ട്.',
'അതിർത്തി കടന്നാൽ പഴയൊരു പൊളിഞ്ഞ കുടിലുണ്ട്.',
'ഡ്യൂബെറി ക്രീക്ക് എന്ന സ്ഥലത്തിന് വടക്ക്.',
'അതിനടുത്ത് എവിടെയെങ്കിലും വണ്ടി ഒളിപ്പിച്ചിട്ടേക്ക്.',
'എങ്ങനെയുണ്ട്?',
'കുഴപ്പമില്ല.',
'അത് കേട്ടാൽ മതി.',
'സത്യം പറഞ്ഞാൽ, അത്ര സുഖമില്ല.',
'ഓ... ശരി.',
'ഹേയ്... പേടിക്കണ്ട, മോളേ.'
]
assert len(rows) == len(translations)
for i, (row, ml) in enumerate(zip(rows, translations)):
    row.pop('words', None)
    row['malayalam'] = ml
    row['character'] = 'John' if i in [0,1,2,3,8,12,15,16,17,18,21,22,23] else 'Arthur' if i < 24 or i in [24,26,28,29] else 'Unidentified NPC'
    row['speaker_status'] = 'Inferred from scene; review required' if i < 24 else 'Review required'
# Word alignment attached a silent gap to this greeting. Keep the actual greeting window.
rows[24]['start'] = 66.3
(OUT / 'malayalam_dialogue.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
with (OUT / 'studio_batch.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['character','emotion','intensity','dialogue'])
    w.writeheader()
    for i, row in enumerate(rows):
        w.writerow({'character': row['character'] if row['character'] != 'Unidentified NPC' else 'Custom Character', 'emotion': 'Sarcastic' if i in [4,5,6,7,9,10,11] else 'Neutral', 'intensity': 45, 'dialogue': row['malayalam']})
def stamp(t):
    ms = round(t * 1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
(OUT / 'malayalam_subtitles.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(r["start"])} --> {stamp(r["end"])}\n{r["malayalam"]}' for i,r in enumerate(rows))+'\n', encoding='utf-8')
lines = ['# RDR2 Malayalam dialogue draft', '', 'Automatic English transcription with Malayalam adaptation. Dialogue and approximate timings need listening review. John/Arthur assignments are inferred; later NPC speakers are unverified.', '', 'The opening line begins mid-scene. Reference clips contain game ambience and are not isolated studio vocals.', '']
for i, r in enumerate(rows):
    lines += [f'### {i+1}. {r["start"]:.2f}–{r["end"]:.2f} seconds — {r["character"]}', '', r['english'], '', r['malayalam'], '']
(OUT / 'dialogue_review.md').write_text('\n'.join(lines), encoding='utf-8')
for name, start, end in [('john_reference', 0, 10.8), ('arthur_reference', 17.1, 24.2)]:
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-ss', str(start), '-i', str(OUT / 'source_audio.wav'), '-t', str(end-start), '-ar', '24000', '-ac', '1', str(OUT / (name+'.wav'))], check=True, capture_output=True)
print('Created translation, subtitles, studio import, and two reference clips.')
