$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$page = Join-Path $root "public\index.html"

if (-not (Test-Path -LiteralPath $page)) {
    throw "Bundled page not found: $page. Run build.sh first, or open chiroptera-tree.html through a local HTTP server."
}

Start-Process -FilePath $page
