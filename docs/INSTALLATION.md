# Installation

## Requirements

- Windows 11 Pro
- Python 3.12
- Ollama
- Qwen model installed
- Docker Desktop for Open WebUI

## Backend

```powershell
cd B:\CTV_AI\backend
Set-ExecutionPolicy -Scope Process RemoteSigned
.\start.ps1
```

## Open WebUI

Connect through:

```text
http://host.docker.internal:8000/v1
```

Use API key:

```text
ctv-ai-local
```
