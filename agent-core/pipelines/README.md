# agent-core/pipelines

End-to-end pipelines for ZULU's core workflows.

## Pipelines

### Live Pipeline (Whisper → Ollama)

`zulu_live_pipeline.py`: Full audio → transcript → analysis flow

**What it does:**
1. Transcribes audio with Whisper (offline)
2. Sends transcript to Ollama (local LLM)
3. Returns structured JSON:
   - Summary
   - Decisions made
   - Action items (yours and others')
   - Tags

**Usage:**
```bash
python zulu_live_pipeline.py path/to/audio.wav
```

Output saved to `storage/meeting-{filename}.json`

## Design Principles

- **Local-first**: No cloud dependencies
- **Privacy-preserving**: No external API calls
- **Composable**: Pipelines can be chained or extended
