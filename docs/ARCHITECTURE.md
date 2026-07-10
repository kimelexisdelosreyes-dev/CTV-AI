# Architecture

## Request Flow

Open WebUI or another client
→ CTV-AI Core
→ Assistant Router
→ Ollama Service
→ Local Qwen model

## Main API Groups

- `/api/v1/*` for native CTV-AI endpoints
- `/v1/*` for OpenAI-compatible clients

## Main Components

- `app/api`: routes
- `app/core`: configuration, logging, prompts
- `app/schemas`: validation models
- `app/services`: routing and Ollama access
- `tests`: automated tests

## Future Modules

- Authentication and roles
- RAG and document ingestion
- Conversation memory
- NAS and media search
- Whisper transcription
- Adobe and DaVinci integrations
