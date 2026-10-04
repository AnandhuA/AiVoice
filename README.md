# Malayalam Voice Studio

A local Windows desktop studio for **character + emotion + acting + timing + synthesis + audio finishing**. It uses PySide6, PyTorch backends, soundfile, NumPy, SciPy and FFmpeg. No speech model is bundled, no game-character voice is shipped, and no fake speech generator is exposed in the application.

## Simple studio layout

Double-click **Open Voice Studio.bat** to launch the installed app.

- **Create dialogue:** choose a character or reference voice, write Malayalam, choose emotion/intensity/speed, and click **Generate voice** or **Play dialogue**.
- **Segments & timeline:** select, reorder, split, merge, regenerate, preview raw/processed takes, and change pauses. Select a segment here, then use **Create dialogue → Apply to selected segment** to change its delivery.
- Expand **Character details and defaults**, **Advanced acting controls**, or **Text tools and timing markup** for the full controls and presets.
- **Tools** contains batch import, models, audio effects, settings, and temporary-file cleanup. **File** contains project and SSML actions; Save and Export audio are also at the top.

## Windows setup

**Selected backend: PrahaTTS-ML.** New scenes default to your requested [Praha Malayalam adapter](https://huggingface.co/Praha-Labs/PrahaTTS-ML) over [Chatterbox non-turbo](https://huggingface.co/ResembleAI/chatterbox). The pinned files total 3,575,616,075 bytes (~3.58 GB). The adapter is Apache-2.0; the base is MIT.

Praha accepts optional **5–10 seconds of reference audio without a transcript**. Without it, the built-in Chatterbox conditioning is used. Harish/Anjali speaker names apply only to Parler. Intensity maps to native exaggeration and CFG weight is native; named emotions use editable analysis-time timing suggestions. The [demo source](https://huggingface.co/spaces/trysem/PrahaTTS-ML/blob/main/app.py) documents these inputs. Our backend fails if LoRA/vocabulary loading fails instead of silently using the base model.

After the main environment setup below, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_praha.ps1
.\.venv\Scripts\python.exe scripts\model_tool.py praha --install
.\.venv\Scripts\python.exe app.py
```

The studio automatically uses `.praha\Scripts\python.exe` for Praha when present. Settings → Inference python accepts an absolute override. This environment isolates Chatterbox 0.1.7's PyTorch 2.6/Transformers 5.2 dependencies from Parler. Public Praha downloads do not use cached credentials, so an expired unrelated Hugging Face token does not block them.

Real Praha validation uses:

```powershell
.\.praha\Scripts\python.exe scripts\real_audio_check.py --backend praha --device Auto
```

The Parler installation steps later in this guide are optional alternatives, not requirements for Praha.

Use Windows 10/11, Python 3.11 or 3.12 (64-bit), and an up-to-date NVIDIA driver for GPU inference. This workspace was validated with Python 3.12, Praha/Chatterbox, and an RTX 4050 6GB. A short actual speech run peaked at 3.72GB allocated CUDA memory; longer phrases can require more. The application also works without PyTorch installed so you can edit scenes and install models first.

Open **PowerShell** in the project directory:

```powershell
winget install --exact --id Python.Python.3.11
winget install --exact --id Git.Git
# Close and reopen PowerShell after installation.
Set-Location C:\Users\Anandhu\AiVoice
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --timeout 180 -e '.[dev]'
```

Or run the checked setup script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -Dev
```

An existing Python executable can be passed explicitly:

```powershell
.\scripts\setup.ps1 -Python 'C:\Path\To\Python312\python.exe' -Dev
```

Activation is optional: every command below uses the virtual environment directly. If desired, activate with `.\.venv\Scripts\Activate.ps1`. Do not change machine-wide execution policy just to run this project.

### CUDA / PyTorch and Parler dependencies

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_parler.ps1
```

The script installs matching PyTorch/torchaudio **2.5.1 CUDA 12.4** wheels and the pinned upstream Parler library, with Transformers 4.46.1. These inference wheels include the CUDA runtime; a separate CUDA toolkit is not required. `nvidia-smi` reports driver capability, not whether your Python installation has CUDA-enabled PyTorch.

CPU-only alternative:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_parler.ps1 -CPU
```

Verify imports and hardware:

```powershell
.\.venv\Scripts\python.exe -c "import torch; from parler_tts import ParlerTTSForConditionalGeneration; print(torch.__version__); print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

The studio serializes GPU work and defaults to conservative phrase lengths. Parler uses float16 on CUDA; the validated Praha runtime uses its upstream precision and peaked at 3.72GB allocated CUDA memory for the short test. Auto mode retries CUDA out-of-memory failures on CPU with a visible message. Explicit CUDA mode reports the failure. Longer phrases can need more memory. CPU fallback can be much slower.

### FFmpeg

The normal dependencies include `imageio-ffmpeg`, which supplies a project-local FFmpeg executable. An explicit **Settings → FFmpeg** path takes precedence. To use a separate installation:

```powershell
winget install --exact --id Gyan.FFmpeg
ffmpeg -version
```

Check the bundled fallback independently:

```powershell
.\.venv\Scripts\python.exe -c "import imageio_ffmpeg, subprocess; subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-version'], check=True)"
```

If the WinGet shortcut cannot run, leave the FFmpeg setting empty to select the fallback, or specify a working absolute executable path.

## Model installation and first speech

**Indic Parler-TTS** is an alternative backend. Its model card lists Malayalam voices Harish, Anjali and Anju, descriptive emotion prompting, and Apache-2.0 licensing. The pinned model checkpoint is approximately 3.76 GB on disk; inference also needs tokenizer files. Accept its gated access terms in your own Hugging Face account:

- [Indic Parler-TTS model card](https://huggingface.co/ai4bharat/indic-parler-tts)
- [Parler source](https://github.com/huggingface/parler-tts)

Authenticate in your own terminal. Do not put access tokens in source files, project JSON or chat:

```powershell
.\.venv\Scripts\huggingface-cli.exe login
.\.venv\Scripts\python.exe scripts\model_tool.py parler
.\.venv\Scripts\python.exe scripts\model_tool.py parler --install
```

The first command reads metadata only. The second prints all selected files, revisions, size and license, then requires typing `DOWNLOAD`. You can instead use **Models → Install / resume** in the GUI, review the details, and approve there. Interrupted installs retain downloaded files; a manifest is written only after every selected file completes. Model access acceptance is a user action the studio cannot perform for you.

Launch:

```powershell
.\.venv\Scripts\python.exe app.py
```

1. Select **Arthur** or **Custom Character** and save character defaults. Praha uses its built-in voice or an optional reference recording. If using Parler instead, select Harish/Anjali. The Arthur/Dutch/John/Sadie/Micah profiles describe general delivery.
2. Enter Malayalam dialogue, for example `നീ... [PAUSE:400] ഇവിടെ വന്നത് എന്തിനാ?`.
3. Choose Suspicious and an intensity, then **Split Sentence**. Review the phrase boundaries and suggestions.
4. Select a segment, change direction/speed/pitch, then **Apply to selected segment**. Use **Apply pauses** for precise boundary timing.
5. Click **Generate**. The worker produces independent real WAV files and reports each segment's status. Failed lines can be retried without losing successful takes.
6. Use **Play raw**, **Play processed**, or **Full dialogue**. **Regenerate selected** creates another take for only that segment.
7. **Save** into a dedicated scene folder. **Export** produces WAV or MP3 with the settings you selected.

Changing the dialogue editor does not silently overwrite the manual timeline. Use Split Sentence to reanalyze; replacing manually edited segments requires an explicit choice. **Add Line** appends the editor contents to the scene. Double-click a segment's dialogue cell to edit its speech text directly. Enter markup in the main editor, not in a speech-only segment cell.

## Performance semantics and honest limitations

| Control | Implementation |
|---|---|
| Emotion / intensity / style | Parler description prompts plus mild local timing/pitch/energy suggestions during analysis; approximate, not exact neural emotion parameters |
| Speed | Deterministic audio tempo processing |
| Pitch | Semitones, resampling with tempo compensation |
| Energy / volume | Relative gain; does not recreate an actor's vocal effort |
| Pause | Sample-counted silence outside TTS; native phonetic silence can still exist inside a take |
| Emphasis / endings | Parler prompt guidance; emphasis also adds mild whole-segment gain. Use markup to isolate a phrase. No forced word alignment; ending intonation is not controllable natively in Praha |
| Breathiness | Experimental prompt hint; not an acoustic breathiness model |
| Breath | Imported user-owned recording inserted only at explicitly selected boundaries |
| Whisper / crying / shouting / drunk | Performance directions with uncertain model adherence; not guaranteed voice transformations |
| Accent / age / gender / description | Character metadata; speaker choice and voice type drive the current Parler adapter |
| SSML | XML export for future supporting backends; neither current adapter receives SSML |

Character defaults are copied into analysis. Emotion suggestions are mild and editable. Markup overrides analysis state; manual segment edits take precedence afterward. Sentence segmentation is deterministic and conservative, **not an LLM screenplay interpretation**. It does not invent emotion changes based on story context. Automatic emphasis is not inferred semantically; add explicit emphasis for reliable intent.

The same speaker name and saved seed encourage consistency, but separate synthesis can change timbre or intonation. Excessively short segments often hurt naturalness: keep complete phrases and compare against longer takes. The studio does not promise film-quality voice acting from post-processing alone.

### Markup

| Syntax | Meaning |
|---|---|
| `...` / `…` | Suggested dramatic boundary |
| `[PAUSE:500]` | Explicit 500ms boundary; replaces the heuristic at this location |
| `[EMPHASIS]text[/EMPHASIS]` | Emphasis guidance |
| `[WHISPER]text[/WHISPER]` | Scoped whisper direction |
| `[BREATH]` | Short breath before the next phrase; requires imported asset |
| `[LOW]`, `[HIGH]` | -2/+2 semitone direction for subsequent spans |
| `[ANGRY:80]` | Anger with 80% intensity for subsequent spans |

Unknown tags, unmatched scopes and invalid pause/intensity values stop analysis with an error. Tags are never passed as speech. Pause-before and the previous segment's pause-after edit one shared boundary, so pauses cannot accidentally double. Moving a segment carries its preceding pause; merging removes the internal boundary and keeps the first segment's performance. Splitting creates a 120ms editable boundary and invalidates the split take.

### Natural Malayalam and pronunciation

Normalization uses NFC, preserves Malayalam joiners and mixed-script text, and avoids guessing ambiguous number or abbreviation expansions. **Pronunciations** accepts a JSON mapping of written expressions to their intended spoken forms. Original text remains visible.

**Natural Malayalam** uses a small, transparent local phrase-substitution set. Review and edit the proposal before saving; Cancel keeps the original. It is not a general-purpose Malayalam rewriting model and no cloud service is used.

## Reference voices / IndicF5

[IndicF5](https://huggingface.co/ai4bharat/IndicF5) documents Malayalam and reference-conditioned speech. Its upstream setup examples use Python 3.10. The studio's adapter is **experimental and unvalidated on Windows/Python 3.11+** until tested with installed model assets and your reference. It has no native emotion-slider API.

Import WAV/MP3/FLAC in **Reference audio**. The dialog converts a copy to mono WAV, displays its waveform and lets you select a trim range. **Apply trim** writes a new copy; it does not overwrite the source. IndicF5 requires the exact transcript of the trimmed reference; Praha does not. Use recordings you have permission to use. Parler does not consume references.

IndicF5 is optional and not required for the MVP. Install its dependencies in a separate environment if they conflict with Parler, then install the studio into that environment. Model file access/download approval is separate. Do not claim this adapter is validated merely because its controls appear in the UI.

Stock [XTTS-v2](https://huggingface.co/coqui/XTTS-v2) does not list Malayalam. Its registry entry returns an explicit unsupported-language error rather than trying Hindi or pretending Malayalam support. External/custom backends can implement `TTSBackend`; no external provider is active or transmitting text.

## Audio finishing, timeline and export

- Timeline blocks can be dragged to reorder. Drag purple pause regions horizontally or edit milliseconds for exact values. The table offers split, merge, volume through the performance inspector, and selected-segment regeneration.
- Waveforms show actual generated samples; timeline durations use estimates until a take exists.
- Raw WAVs are preserved. Speed/pitch/gain changes reuse speech; native prompt/text/voice/model/seed changes invalidate synthesis.
- Effects are off by default except final normalization/peak protection. Optional filters, EQ, gentle compression, noise reduction, saturation and short reverb run on the assembled mix. An ambience WAV/FLAC can be supplied by path.
- Breath files are selected in Effects; no random breathing, synthetic noise presented as breathing, or stock voice impersonations are used. Hesitations such as `മ്മ്...` or `അത്...` are normal, explicit speech segments.
- Default game export: **48kHz / 24-bit / mono WAV**. 22050/44100/48000 Hz, 16/24-bit and mono/stereo are supported. Stereo duplicates the mono voice. MP3 uses bitrate rather than bit depth.
- Resampling cannot recover high frequencies absent from a model's native output. Reverb can add a tail beyond the speech duration.

## Projects, batches and files

Source modules are in `malayalam_voice_studio/{gui,core,tts,audio}`. Application data is rooted at the launch directory, or `MVS_HOME` when explicitly set.

```text
models/       Approved local checkpoints and their install manifests
voices/       Imported reference copies, trims and presets
projects/     Scene directories chosen by the user
exports/      Default exports
cache/        Immutable raw takes, processed derivatives, temporary audio
logs/         Rotating diagnostic log
```

Each saved scene contains authoritative `project.json`, readable `dialogue.json`, `audio/segments`, `references`, and `exports`. Assets are copied into the scene and stored with relative paths; model weights are not duplicated into every scene. Projects can play saved takes without their original model. Missing models are reported at generation; missing audio is reported at open. Never select the same project folder for unrelated scenes unless intending to overwrite it.

**Batch import** accepts UTF-8/UTF-8-BOM CSV or JSON arrays with `character`, `emotion`, `intensity` (0–100), and `dialogue`. Create custom characters first. Invalid input is rejected before altering the scene. See `examples/dialogue.csv` and `examples/listening_lines.json`.

**Clean temp** only removes regular files in the configured cache's `temporary` directory. It does not remove models, saved projects, or retained raw takes.

## Tests and real-audio acceptance

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q malayalam_voice_studio
.\.venv\Scripts\python.exe scripts\real_audio_check.py --device Auto
```

The automated suite uses audio tones only to measure DSP behavior; there is no fake production TTS backend. Tests cover Malayalam Unicode, long/mixed dialogue, markup, shared pause boundaries, cache behavior, portable projects, CPU fallback, missing dependencies/audio, export format, independent tempo/pitch, and GUI updates.

The real-audio command requires the actual installed checkpoint. It synthesizes Malayalam, exports a real 48kHz/24-bit WAV, saves/reopens the scene, and records elapsed time and peak CUDA allocation under `validation/real-audio`. It deliberately fails if the model cannot load. Playback and a Malayalam speaker's listening review are still required: score pronunciation, naturalness, emotion, voice continuity and boundary quality. Compare neutral/long-phrase and acted/segmented versions of the supplied listening lines.

## Troubleshooting

| Problem | Recovery |
|---|---|
| Python / `py` not found | Install 64-bit Python 3.11, reopen PowerShell, or pass an absolute executable to setup |
| No CUDA in the studio | Verify the environment's torch build and NVIDIA driver; reinstall the CUDA wheels or choose CPU |
| Model missing | Install from Models; a Python package is not a model checkpoint |
| 401 / 403 / gated repository | Accept the specific model's access terms and run `huggingface-cli login` locally |
| Network timeout | Retry installation with a longer pip timeout; model install resumes existing files |
| Out of VRAM | Close GPU applications, split long phrases, use Auto/CPU; completed takes remain available |
| Out of RAM | Close other applications and reduce the scene size; long full mixes currently assemble in RAM |
| FFmpeg cannot run | Leave path empty for bundled fallback or select a valid executable |
| Invalid reference | Import a decodable file, trim a clean speech region, and provide its exact transcript |
| Missing tokenizer offline | Re-run approved model installation; the description tokenizer must also be installed |
| Model worker times out | Shorten phrases or increase Settings → timeout; cancellation retains completed takes |
| No playback | Verify Windows output device and volume; playback errors appear in the studio |
| Metallic joins or unstable emotion | Use longer phrases, less extreme speed/pitch, and lower intensity; compare alternate takes |
| Corrupt settings | Back up and rename `settings.json`; relaunch to recreate defaults |

Logs are in `logs/studio.log`. The GUI remains responsive during inference, model downloads and full-mix rendering. Cancellation requests a graceful stop, then terminates an unresponsive inference worker after three seconds. Third-party model download transfers finish their current network operation before the model window can close.

See `VALIDATION.md` for the actual checks completed in this workspace and remaining validation requirements.
