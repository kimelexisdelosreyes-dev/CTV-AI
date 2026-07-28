# CTV-AI Canonical Repository

CTV-AI is a local-first AI platform for a small multimedia company.

This repository is the single source of truth moving forward.

## Included

- FastAPI backend
- Ollama integration
- OpenAI-compatible API for Open WebUI
- Specialist assistants
- Streaming chat
- Environment configuration
- Logging
- Tests
- Docker support
- Windows startup scripts
- Documentation

## Specialist Models

- `ctv-ai-general`
- `ctv-ai-production`
- `ctv-ai-graphics`
- `ctv-ai-drone`
- `ctv-ai-it`

## Quick Start

```powershell
cd B:\CTV_AI\backend
Set-ExecutionPolicy -Scope Process RemoteSigned
.\start.ps1
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Office LAN Access

To present CTV ONE from this workstation to other laptops on the same Private office network, use:

```powershell
cd B:\CTV_AI
.\scripts\start-lan.ps1
```

See [docs/LAN_ACCESS.md](docs/LAN_ACCESS.md) for firewall rules, test URLs, and troubleshooting.

## Open WebUI Connection

```text
Base URL: http://host.docker.internal:8000/v1
API Key: ctv-ai-local
```

## Tests

```powershell
cd B:\CTV_AI\backend
.\.venv\Scripts\Activate.ps1
python -m pytest
```

## Canonical Git Baseline

```powershell
git add .
git commit -m "feat(core): establish canonical CTV-AI platform"
git tag v1.0.0
git push -u origin main
git push origin v1.0.0
```
