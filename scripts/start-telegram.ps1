$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Falta el entorno Python del proyecto.' }
Push-Location -LiteralPath (Join-Path $projectRoot 'backend')
try {
    & $python -m jordy.telegram
    $botExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $botExitCode
