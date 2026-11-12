# Loads fixtures only in the running lab API, using its restricted database role.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$docker = (Get-Command docker -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $docker) {
    $docker = Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe'
}
if (-not (Test-Path -LiteralPath $docker)) { throw 'Se requiere Docker Desktop.' }

$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Get-Content -LiteralPath (Join-Path $PSScriptRoot 'seed_demo.py') -Raw -Encoding UTF8 |
    & $docker compose -f (Join-Path $root 'compose.yaml') --env-file (Join-Path $root '.env.compose') -p jordy-lab exec -T api python -
if ($LASTEXITCODE -ne 0) { throw 'No se pudo cargar la demo. Comprueba que jordy-lab esté iniciado y migrado.' }
