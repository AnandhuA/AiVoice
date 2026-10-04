$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath '.praha\Scripts\python.exe')) {
    & .\.venv\Scripts\python.exe -m venv .praha
    if ($LASTEXITCODE -ne 0) { throw 'Create the main studio environment first.' }
}
& .\.praha\Scripts\python.exe -m pip install --timeout 180 --retries 5 torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
if ($LASTEXITCODE -ne 0) { throw 'Praha PyTorch installation failed.' }
& .\.praha\Scripts\python.exe -m pip install --timeout 180 --retries 5 chatterbox-tts==0.1.7 peft==0.18.1 numpy==1.26.4 scipy==1.15.2 soundfile==0.13.1 PySide6==6.8.3 imageio-ffmpeg==0.6.0 'huggingface-hub<2'
if ($LASTEXITCODE -ne 0) { throw 'Praha runtime installation failed.' }
# The model runtime intentionally has its own Transformers/Hub versions.
& .\.praha\Scripts\python.exe -m pip install --no-deps -e .
if ($LASTEXITCODE -ne 0) { throw 'Studio worker package installation failed.' }
& .\.praha\Scripts\python.exe -c "from chatterbox.tts import ChatterboxTTS; from peft import PeftModel; print('Praha runtime imports OK')"
if ($LASTEXITCODE -ne 0) { throw 'Praha import check failed.' }
Write-Host 'Set Settings > Inference python to .praha\Scripts\python.exe (absolute path). Model files are installed separately.'
