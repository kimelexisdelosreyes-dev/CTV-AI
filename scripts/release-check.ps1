$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent

Push-Location "$RepoRoot\backend"
& ".\.venv\Scripts\python.exe" -m compileall app
& ".\.venv\Scripts\python.exe" -m pytest
Pop-Location

Push-Location "$RepoRoot\frontend\enterprise-ui"
npm run lint
npm run build
Pop-Location

Write-Host "CTV ONE release checks passed." -ForegroundColor Green
