# Start hotspot platform: bridge daemon + we-mp-rss
# Usage (from repo root): .\scripts\start_platform.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "[start] Repo: $Root"
uv run python scripts/start_platform.py @args
