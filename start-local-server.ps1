$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$serveScript = Join-Path $root "serve-tree.ps1"

$existing = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existing) {
    exit 0
}

Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", $serveScript) `
    -WorkingDirectory $root `
    -WindowStyle Hidden
