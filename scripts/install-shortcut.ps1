$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $PSScriptRoot 'start-panel.ps1'
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'Jordy Studio.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$target = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $launcher + '"'
if (Test-Path -LiteralPath $shortcutPath) {
    if ($shortcut.TargetPath -ne $target -or $shortcut.WorkingDirectory -ne $projectRoot -or -not $shortcut.Arguments.Contains('"' + $launcher + '"')) {
        throw 'Ya existe un acceso directo Jordy Studio de otro proyecto. No se modificó.'
    }
}
$shortcut.TargetPath = $target
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $projectRoot
$shortcut.WindowStyle = 7
$shortcut.Description = 'Abre el panel privado de Jordy Studio en esta computadora.'
$shortcut.IconLocation = (Join-Path $env:SystemRoot 'System32\shell32.dll') + ',21'
$shortcut.Save()
Write-Output "Acceso directo creado: $shortcutPath"
