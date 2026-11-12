param([switch]$AuthorizeTemporaryExposure)
$ErrorActionPreference = 'Stop'
if (-not $AuthorizeTemporaryExposure) {
    throw 'No se abrió ningún túnel. Requiere autorización expresa de exposición temporal y -AuthorizeTemporaryExposure.'
}
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
& (Join-Path $projectRoot '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'check_webhook_isolation.py')
if ($LASTEXITCODE -ne 0) { throw 'Aislamiento no verificado. Túnel cancelado.' }
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    throw 'ngrok no está disponible. Configura el agente manualmente; no se instala ningún servicio.'
}
& ngrok http http://127.0.0.1:8001 --inspect=false
exit $LASTEXITCODE
