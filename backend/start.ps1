$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

Set-ExecutionPolicy -Scope Process RemoteSigned -Force
& ".\.venv\Scripts\Activate.ps1"

python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

python -m uvicorn app.main:app --reload
