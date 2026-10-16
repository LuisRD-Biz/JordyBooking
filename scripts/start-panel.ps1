$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
& .venv/Scripts/python.exe scripts/setup_local.py
if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la base local.' }
& .venv/Scripts/python.exe -m uvicorn jordy.main:app --app-dir backend --host 127.0.0.1 --port 8000
