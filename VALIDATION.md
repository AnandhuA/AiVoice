# Validation record

This file records actual checks, not claims about completed speech inference.

## Verified in this workspace

- Windows RTX 4050 Laptop GPU, 6GB VRAM detected; CUDA works in the studio's PyTorch runtime.
- Python 3.12 virtual environment created; source compiles successfully.
- 62 automated tests passed after final model integration: Unicode/markup, long dialogue, pause timing, DSP tempo/pitch independence, WAV metadata, project portability, cache keys, capability gating, stale results, and Qt media decoding.
- Real PySide6 widgets rendered to `validation/studio.png`; Malayalam rendering was visually checked after explicit Nirmala font registration.
- FFmpeg processing tests use the bundled executable and actual audio transformations.
- Qt media loading verified for a generated 48kHz/24-bit WAV. This does not establish audible hardware playback or speech quality.
- Praha adapter and all Chatterbox base assets installed; published weight SHA-256 hashes verified. Both Python environments pass `pip check`.
- Actual Malayalam synthesis succeeded on CUDA with PyTorch 2.6.0+cu124. The first two-segment run generated 2.683625 seconds of audio and recorded 3.718 GB peak allocated CUDA memory. It took 128.44 seconds after model loading, including first-use overhead. This is a single example, not a general speed guarantee.
- The desktop controller ran the isolated `.praha` process, regenerated only the selected segment, preserved the other take, rendered the mix, exported WAV and MP3, and saved/reopened its project.
- Qt loaded the actual speech WAV and reported `PlayingState`. Output is under `validation/desktop-acceptance`; the test screenshot includes the generated waveform.
- A pause-only edit to 725ms reused the existing raw take through the desktop generation controller; see `validation/desktop-acceptance/cache-report.json`.
- Actual model report: `validation/real-audio/report.json`. Desktop integration report: `validation/desktop-acceptance/report.json`.

## In progress / not established

- Reference voice inference using user-owned audio.
- Native-speaker evaluation of pronunciation, naturalness, emotional adherence and phrase continuity.
- IndicF5 Windows inference and optional Parler inference. Their adapters remain unvalidated without their model assets.

No mock generator is registered in the application. Automated DSP signals are test fixtures only. The MVP is now validated for real synthesis and desktop audio workflow; naturalness and acting quality still require listening review.

## Reproduction

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -X utf8 scripts\ui_check.py
Remove-Item Env:\QT_QPA_PLATFORM
.\.praha\Scripts\python.exe -X utf8 scripts\real_audio_check.py --backend praha --device Auto
```
