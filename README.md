# CTV-AI Starter

CTV-AI is a local-first AI platform foundation for a small multimedia company.

## Milestone 1 Features

- FastAPI backend
- Ollama integration
- General, Production, Graphics, Drone, and IT assistants
- Health and version endpoints
- Environment-based configuration
- Structured application logging
- Pytest smoke tests
- Docker support
- Windows PowerShell startup script

## Requirements

- Windows 11 Pro
- Python 3.12
- Ollama running locally
- A downloaded model such as `qwen3:14b`
- Optional: Docker Desktop

## Quick Start on Windows

Open PowerShell:

```powershell
cd B:\CTV_AI\backend
Set-ExecutionPolicy -Scope Process RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

Open:

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/v1/health
- Version: http://127.0.0.1:8000/api/v1/version

## Test Chat

In Swagger, open `POST /api/v1/chat` and submit:

```json
{
  "message": "Introduce yourself in one sentence.",
  "assistant": "general"
}
```

Available assistants:

- `general`
- `production`
- `graphics`
- `drone`
- `it`

## Run Tests

```powershell
python -m pytest
```

## Git Baseline

After confirming the project works:

```powershell
git add .
git commit -m "feat(core): initialize CTV-AI platform"
git tag v0.1.0-alpha
git push -u origin main
git push origin v0.1.0-alpha
```
