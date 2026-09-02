$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python not found at $python"
}

$existing = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8000 -ErrorAction SilentlyContinue
if ($existing) {
    exit 0
}

Set-Location -LiteralPath $root
& $python -m http.server 8000 --bind 127.0.0.1
