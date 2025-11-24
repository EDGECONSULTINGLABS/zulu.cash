# agent-core

Core intelligence for ZULU:

- Whisper + diarization
- Ollama LLM inference
- Pipelines for transcription → analysis → actions
- Memory abstraction on top of encrypted storage

Subfolders:
- `inference/` – model runners, adapters, and utilities
- `pipelines/` – end-to-end flows (audio → text → JSON)
- `prompts/` – system and agent prompts
- `memory/` – local memory logic on top of SQLCipher
