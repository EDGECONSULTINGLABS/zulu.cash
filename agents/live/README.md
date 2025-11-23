# Live Agent — Conversation Memory

## Purpose
Records and remembers your conversations privately.

## Features
- **Whisper.cpp** → Offline transcription
- **Local LLM** → Context understanding
- **Encrypted memory** → SQLCipher storage
- **Zero cloud** → Nothing leaves device

## Architecture
```
Microphone → VAD → Whisper → LLM → Encrypted Memory
```

## Privacy
- ✅ All processing on-device
- ✅ No cloud uploads
- ✅ Encrypted storage
- ❌ Zero telemetry

---

> **Remembers your mind, not your wallet.**
