# Architecture

## Request Flow

Client → FastAPI API → AI Router → Ollama Service → Local Ollama Model

## Modules

- `app/api`: HTTP routes
- `app/core`: settings, prompts, logging
- `app/schemas`: request and response models
- `app/services`: AI routing and Ollama access
- `tests`: automated smoke tests

## Future Milestones

- Authentication and roles
- Company knowledge with RAG
- Conversation memory
- NAS and media indexing
- Whisper transcription
- Adobe and DaVinci integrations
