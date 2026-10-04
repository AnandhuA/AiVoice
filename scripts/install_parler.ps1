param([switch]$CPU)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$index = if ($CPU) { 'https://download.pytorch.org/whl/cpu' } else { 'https://download.pytorch.org/whl/cu124' }
& .\.venv\Scripts\python.exe -m pip install --timeout 180 torch==2.5.1 torchaudio==2.5.1 --index-url $index
if ($LASTEXITCODE -ne 0) { throw 'PyTorch installation failed.' }
& .\.venv\Scripts\python.exe -m pip install --timeout 180 'parler-tts @ git+https://github.com/huggingface/parler-tts.git@d108732cd57788ec86bc857d99a6cabd66663d68' transformers==4.46.1 sentencepiece==0.2.0 protobuf==5.29.3
if ($LASTEXITCODE -ne 0) { throw 'Parler dependencies failed to install. See README troubleshooting.' }
& .\.venv\Scripts\python.exe -c "import torch; from parler_tts import ParlerTTSForConditionalGeneration; print('CUDA:', torch.cuda.is_available())"
if ($LASTEXITCODE -ne 0) { throw 'Backend import check failed.' }
Write-Host 'Backend code installed. No model weights have been downloaded.'
