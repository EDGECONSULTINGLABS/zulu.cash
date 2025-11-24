# agent-core/inference

Model runners and inference adapters for ZULU.

## Components

- **Whisper**: Local speech-to-text transcription
- **Ollama**: Local LLM for analysis and summarization
- **Diarization**: Speaker identification (future)

## Files

- `whisper-local.py`: Offline Whisper transcription wrapper

## Usage

All inference runs locally. No external API calls.

```python
# Example: Transcribe audio with Whisper
python whisper-local.py audio.wav
```

See `../pipelines/` for end-to-end flows.
