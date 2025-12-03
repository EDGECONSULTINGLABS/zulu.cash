# 🐉 DRAGON MODE — Live WhisperX Agent

**Status:** ✅ **FULLY OPERATIONAL**

Dragon Mode is the **live, real-time implementation** of ZULU's privacy-first AI vision.

---

## What is Dragon Mode?

Dragon Mode = **ZULU Live WhisperX Agent**

A complete end-to-end pipeline that:
- 🎤 Records audio from your microphone **in real-time**
- 🗣️ Transcribes with **WhisperX** (local, offline)
- 👥 Diarizes speakers (PyAnnote)
- 🧠 Summarizes with **local LLM** (Ollama/llama3.1)
- 🔐 Encrypts everything in **SQLCipher**
- 🔢 Sends **only embeddings** to MPC (Nillion)
- 🗑️ Deletes raw audio after processing

---

## Key Features

### 🛡️ Privacy-First Architecture
- **Zero cloud inference** — all processing happens locally
- **No text transmission** — MPC receives only anonymized embeddings
- **Automatic audio deletion** — raw recordings never persist
- **Encrypted storage** — SQLCipher AES-256 encryption

### ⚡ Real-Time Processing
- Live recording with visual feedback
- Speaker diarization (multi-speaker support with HF_TOKEN)
- Per-turn embeddings and storage
- Instant encrypted memory storage

### 🤖 Local LLM Summarization
- Ollama integration (llama3.1:8b, phi3, etc.)
- Structured JSON output (summary, key points, decisions, sentiment)
- Action item extraction
- Risk identification
- Topic classification

### 🔢 MPC Integration
- Nillion testnet ready
- Privacy-preserving analytics
- Engagement scoring
- Key moment detection
- **Only embeddings transmitted** (no raw text)

---

## Quick Start

### 1. Install Dependencies

```bash
cd agents/zulu-mpc-agent
pip install -r requirements.txt
```

### 2. Install Ollama & Pull Model

```bash
# Install Ollama (see https://ollama.ai)
ollama pull llama3.1:8b
```

### 3. Run Dragon Mode

```bash
python cli.py live-whisperx --model-size medium
```

### 4. Record Session

- Speak into your microphone
- Press **Ctrl+C** when done
- Watch the magic happen! ✨

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   DRAGON MODE PIPELINE                   │
└─────────────────────────────────────────────────────────┘

    🎤 Microphone
         │
         ▼
    ┌─────────────┐
    │ Audio       │ ← Real-time capture with VAD
    │ Recording   │
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │ WhisperX    │ ← Local ASR (medium model)
    │ Transcribe  │   Language detection
    └─────────────┘   Word-level alignment
         │
         ▼
    ┌─────────────┐
    │ PyAnnote    │ ← Speaker diarization
    │ Diarization │   (requires HF_TOKEN)
    └─────────────┘
         │
         ▼
    ┌─────────────┐
    │ Embedding   │ ← sentence-transformers
    │ Model       │   all-MiniLM-L6-v2 (384d)
    └─────────────┘
         │
         ├──────────────────┬──────────────────┐
         ▼                  ▼                  ▼
    ┌─────────┐      ┌──────────┐      ┌──────────┐
    │SQLCipher│      │  Ollama  │      │ Nillion  │
    │Database │      │   LLM    │      │   MPC    │
    │(Local)  │      │ (Local)  │      │(Embeddings│
    └─────────┘      └──────────┘      │   Only)  │
         │                  │           └──────────┘
         │                  ▼
         │           ┌──────────┐
         │           │ Summary  │ ← Structured JSON
         │           │ • Topics │   • Key points
         │           │ • Actions│   • Decisions
         │           │ • Risks  │   • Sentiment
         │           └──────────┘
         │
         ▼
    ┌─────────────┐
    │   🗑️ Delete  │ ← Audio file removed
    │ Raw Audio   │   after processing
    └─────────────┘
```

---

## Privacy Guarantees

| Data Type | Storage | Transmission | Lifetime |
|-----------|---------|--------------|----------|
| **Raw Audio** | Temp file only | ❌ Never | Deleted immediately |
| **Transcripts** | SQLCipher (encrypted) | ❌ Never | Persistent (local) |
| **Embeddings** | SQLCipher (encrypted) | ✅ To MPC (anonymized) | Persistent (local) |
| **Summaries** | SQLCipher (encrypted) | ❌ Never | Persistent (local) |
| **Speaker IDs** | Generic labels only | ❌ Never | Persistent (local) |

**ZULU never transmits:**
- ❌ Raw audio
- ❌ Transcript text
- ❌ Speaker identities
- ❌ LLM summaries

**ZULU only transmits:**
- ✅ Anonymized embeddings (384-dimensional vectors)
- ✅ Session metadata (counts, durations)

---

## Example Session

See [`examples/dragon-mode-session.txt`](../../examples/dragon-mode-session.txt) for a complete example output.

**Key highlights:**
```
[*] 🔴 RECORDING... (Press Ctrl+C to stop)
[OK] Processed 8 speaker turns
[OK] Stored 8 turns locally (encrypted)
[MPC] -> Only anonymized embeddings
[OK] ✅ Summary generated successfully
[*] Audio file deleted
```

---

## Configuration

### Model Selection

**WhisperX Model Sizes:**
- `tiny` — Fastest, least accurate (39M params)
- `base` — Fast, decent (74M params)
- `small` — Balanced (244M params)
- `medium` — **Recommended** (769M params) ⭐
- `large` — Best accuracy, slowest (1550M params)

### Ollama Models

Tested and working:
- `llama3.1:8b` — Best quality ⭐
- `phi3:latest` — Fastest
- `mistral:latest` — Good balance

### Enable Multi-Speaker Diarization

1. Get HuggingFace token: https://huggingface.co/settings/tokens
2. Accept pyannote terms: https://huggingface.co/pyannote/speaker-diarization
3. Set environment variable:
   ```bash
   export HF_TOKEN="your_token_here"  # Linux/Mac
   $env:HF_TOKEN="your_token_here"     # Windows
   ```

---

## Technical Details

### Stack
- **Audio:** sounddevice, pydub, webrtcvad
- **ASR:** WhisperX (faster-whisper backend)
- **Diarization:** PyAnnote.audio
- **Embeddings:** sentence-transformers
- **LLM:** Ollama (llama3.1:8b)
- **Database:** SQLCipher (AES-256)
- **MPC:** Nillion Python SDK

### Performance
- **Recording:** Real-time
- **Transcription:** ~2-5x real-time (CPU medium)
- **LLM Summary:** 30-90s (depends on model/hardware)
- **Total:** ~1-2 minutes for 30s recording

### Requirements
- Python 3.10+
- 4GB+ RAM
- Ollama running (localhost:11434)
- Microphone

---

## Roadmap

### ✅ Completed (Dragon Mode v1.0)
- [x] Real-time audio capture
- [x] WhisperX transcription
- [x] Speaker diarization
- [x] Local LLM summarization
- [x] SQLCipher encryption
- [x] MPC integration framework
- [x] Auto audio deletion
- [x] Live recording UI

### 🚧 In Progress
- [ ] GPU acceleration (CUDA/Metal)
- [ ] Streaming transcription (chunk-by-chunk)
- [ ] Multi-speaker tracking improvements
- [ ] Real-time display UI

### 📋 Planned
- [ ] Voice activity detection optimization
- [ ] Custom wake word
- [ ] Meeting action item extraction
- [ ] Knowledge graph integration
- [ ] Desktop app (Electron)

---

## Troubleshooting

### "Model llama3.1:8b not found"
```bash
ollama pull llama3.1:8b
```

### "No audio input detected"
Check your microphone permissions and default input device.

### "Diarization disabled"
Set `HF_TOKEN` environment variable (see Configuration above).

### Slow LLM summarization
- Use a smaller model: `phi3:latest`
- Reduce context window
- Use GPU if available

---

## Why "Dragon Mode"?

Dragons are:
- 🐉 **Powerful** — Full-stack AI pipeline
- 🛡️ **Protective** — Privacy-first architecture
- 🔥 **Fierce** — No compromises on sovereignty
- 🏔️ **Legendary** — Production-ready excellence

**Dragon Mode = ZULU at full power.**

---

## Credits

Built for the **Zypherpunk Hackathon** by the ZULU team.

**Core Technologies:**
- WhisperX by [@m-bain](https://github.com/m-bain/whisperX)
- Ollama by [@jmorganca](https://github.com/jmorganca/ollama)
- PyAnnote by [@pyannote](https://github.com/pyannote/pyannote-audio)
- Nillion by [@NillionNetwork](https://nillion.com)

---

**🔥 Dragon Mode is live. Privacy is non-negotiable. ZULU is the way. 🔥**
