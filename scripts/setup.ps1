param([string]$Python = "py", [switch]$Dev)
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = '1'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    if ($Python -eq 'py') { & py -3.11 -m venv .venv } else { & $Python -m venv .venv }
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required. Install it or pass -Python with its full path.' }
}
$package = if ($Dev) { '.[dev]' } else { '.' }
& .\.venv\Scripts\python.exe -m pip install --timeout 180 --retries 5 -r requirements.txt -e $package
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Review the pip output above.' }
Write-Host 'Studio installed. Next: scripts\install_parler.ps1. Model weights are installed separately with approval.'
