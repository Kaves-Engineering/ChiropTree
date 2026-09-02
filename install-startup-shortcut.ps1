$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $root "start-local-server.ps1"
$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "TreeOfBatLife Local Server.lnk"

if (-not (Test-Path -LiteralPath $startScript)) {
    throw "Startup script not found: $startScript"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`""
$shortcut.WorkingDirectory = $root
$shortcut.WindowStyle = 7
$shortcut.Description = "Starts the TreeOfBatLife localhost server."
$shortcut.Save()

& $startScript

Write-Host "Installed startup shortcut: $shortcutPath"
Write-Host "Open http://127.0.0.1:8000/chiroptera-tree.html"
