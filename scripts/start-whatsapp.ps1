param([ValidateSet('receiver', 'worker')][string]$Mode = 'receiver')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Falta el entorno Python del proyecto.' }
# Foreground, temporary processes only. Ctrl+C stops this component.
# Access logging is disabled: Meta verification uses a secret in the query string.
if ($Mode -eq 'receiver') {
    & $python -m uvicorn jordy.messaging.webhook:app --app-dir backend --host 127.0.0.1 --port 8001 --no-access-log --no-proxy-headers --limit-concurrency 32 --timeout-keep-alive 5
} else {
    $env:PYTHONPATH = Join-Path $projectRoot 'backend'
    & $python -m jordy.messaging.worker
}
exit $LASTEXITCODE
