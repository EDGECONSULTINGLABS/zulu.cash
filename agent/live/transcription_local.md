# Local Transcription — Whisper.cpp

## Overview

ZULU uses **Whisper.cpp** for offline speech-to-text transcription.

## Why Whisper.cpp?

- ✅ **Fully offline** — No cloud API calls
- ✅ **Fast inference** — Optimized C++ implementation
- ✅ **Cross-platform** — Windows, macOS, Linux
- ✅ **Multiple models** — Tiny, base, small, medium, large

## Architecture

```
Microphone → VAD → Audio Buffer → Whisper.cpp → Transcript → Context Manager
```

## Setup

### 1. Install Whisper.cpp

```bash
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
make
```

### 2. Download Model

```bash
bash ./models/download-ggml-model.sh base
```

### 3. Test Transcription

```bash
./main -m models/ggml-base.bin -f samples/jfk.wav
```

## Integration with ZULU

```python
from audio_pipeline import AudioPipeline

pipeline = AudioPipeline()
pipeline.start_capture()

# Transcribe in real-time
for transcript in pipeline.stream_transcription():
    print(f"Transcribed: {transcript}")
    # Store in encrypted memory
```

## Privacy Guarantees

- ❌ No audio sent to cloud
- ❌ No API keys required
- ❌ No telemetry
- ✅ All processing on-device
- ✅ Encrypted storage only

## Performance

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| Tiny | 75 MB | Very Fast | Good |
| Base | 142 MB | Fast | Better |
| Small | 466 MB | Moderate | Great |
| Medium | 1.5 GB | Slow | Excellent |

**Recommended:** Base or Small for real-time use.

## Next Steps

- [ ] Implement VAD integration
- [ ] Add streaming transcription
- [ ] Optimize buffer management
- [ ] Add language detection

---

> **Local Transcription = Zero Cloud Leakage**
