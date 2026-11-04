param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
try {
    if (-not (Test-Path -LiteralPath $python)) { throw 'Falta instalar el entorno de Python. Consulta docs/panel.md.' }
    $launchArgs = @((Join-Path $PSScriptRoot 'launch_panel.py'))
    if ($NoBrowser) { $launchArgs += '--no-browser' }
    & $python @launchArgs
    exit $LASTEXITCODE
} catch {
    $logDirectory = Join-Path $projectRoot '.local'
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
    $message = $_.Exception.Message
    Add-Content -LiteralPath (Join-Path $logDirectory 'launcher.log') -Value $message
    if (-not $NoBrowser) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show($message, 'Jordy Studio', 'OK', 'Error') | Out-Null
    }
    exit 1
}
