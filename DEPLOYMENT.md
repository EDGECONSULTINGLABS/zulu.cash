# 🚀 ZULU Deployment Guide

**Deploy ZULU Live Agent (Dragon Mode) in under 5 minutes.**

---

## Prerequisites

- **Python 3.10+**
- **4GB+ RAM**
- **Microphone**
- **Internet** (for initial setup only)

---

## Quick Start (3 Commands)

### 1. Install Ollama

**macOS/Linux:**
```bash
curl https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai/download

### 2. Pull LLM Model

```bash
ollama pull llama3.1:8b
```

*This downloads ~4.7GB. Wait for completion.*

### 3. Run ZULU Dragon Mode

```bash
cd agents/zulu-mpc-agent
pip install -r requirements.txt
python cli.py live-whisperx --model-size medium
```

**Done!** 🎉 Speak into your mic and press Ctrl+C when finished.

---

## Detailed Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/edgeconsultinglabs/zulu.cash.git
cd zulu.cash
```

### Step 2: Install Python Dependencies

```bash
cd agents/zulu-mpc-agent
pip install -r requirements.txt
```

**Required packages:**
- faster-whisper (ASR)
- whisperx (alignment + diarization)
- sentence-transformers (embeddings)
- sounddevice (audio capture)
- sqlcipher3 (encrypted database)
- ollama (LLM client)

### Step 3: Verify Ollama

```bash
# Check Ollama is running
curl http://localhost:11434

# List installed models
ollama list

# Pull llama3.1:8b if not present
ollama pull llama3.1:8b
```

### Step 4: Test Dragon Mode

```bash
python cli.py live-whisperx --model-size medium
```

**Expected output:**
```
[*] Initializing ZULU Live WhisperX Agent...
[OK] ZULU Live Agent ready

[*] 🔴 RECORDING... (Press Ctrl+C to stop)
```

Speak for 10-30 seconds, then press **Ctrl+C**.

You should see:
- ✅ Audio transcription
- ✅ Speaker diarization
- ✅ LLM summary generation
- ✅ Encrypted storage
- ✅ MPC submission

---

## Configuration Options

### WhisperX Model Sizes

Choose based on your hardware:

| Model | Size | Speed | Accuracy | Recommended For |
|-------|------|-------|----------|-----------------|
| `tiny` | 39M | Fastest | Low | Testing only |
| `base` | 74M | Fast | Medium | Quick demos |
| `small` | 244M | Moderate | Good | Laptops |
| **`medium`** | **769M** | **Slow** | **High** | **Production** ⭐ |
| `large` | 1550M | Slowest | Best | Desktop (GPU) |

**Usage:**
```bash
python cli.py live-whisperx --model-size small  # Faster
python cli.py live-whisperx --model-size medium # Recommended
python cli.py live-whisperx --model-size large  # Best quality
```

### Ollama Model Selection

Edit `agent_core/llm/ollama_client.py`:
```python
def __init__(
    self,
    model: str = "llama3.1:8b",  # Change here
    ...
)
```

**Recommended models:**
- `llama3.1:8b` — Best quality (4.7GB) ⭐
- `phi3:latest` — Fastest (2.2GB)
- `mistral:latest` — Balanced (4.1GB)

### Enable Multi-Speaker Diarization

**1. Get HuggingFace Token:**
- Go to https://huggingface.co/settings/tokens
- Create new token (read access)

**2. Accept Model Terms:**
- Visit https://huggingface.co/pyannote/speaker-diarization
- Click "Agree and access repository"

**3. Set Environment Variable:**

**Linux/Mac:**
```bash
export HF_TOKEN="hf_xxxxxxxxxxxxx"
python cli.py live-whisperx
```

**Windows:**
```powershell
$env:HF_TOKEN = "hf_xxxxxxxxxxxxx"
python cli.py live-whisperx
```

---

## Docker Deployment (Optional)

### Build Image

```bash
cd agents/zulu-mpc-agent
docker build -t zulu-agent .
```

### Run Container

```bash
docker run -it \
  -v $(pwd)/data:/app/data \
  -e HF_TOKEN=your_token \
  --device /dev/snd \
  zulu-agent python cli.py live-whisperx
```

**Note:** Docker requires additional audio device mapping on macOS/Windows.

---

## Production Checklist

Before deploying to production:

- [ ] Install Ollama and pull model
- [ ] Test microphone permissions
- [ ] Verify SQLCipher encryption works
- [ ] Set `HF_TOKEN` for multi-speaker
- [ ] Configure desired WhisperX model size
- [ ] Test end-to-end recording → summary flow
- [ ] Review privacy settings (MPC enabled/disabled)
- [ ] Set up monitoring/logging
- [ ] Document your setup

---

## Troubleshooting

### "Ollama not found"

**Check if Ollama is running:**
```bash
curl http://localhost:11434
```

**Start Ollama:**
```bash
ollama serve
```

### "Model not found"

**List available models:**
```bash
ollama list
```

**Pull missing model:**
```bash
ollama pull llama3.1:8b
```

### "No audio input"

**macOS:**
- System Preferences → Security & Privacy → Microphone
- Grant permission to Terminal/Python

**Linux:**
```bash
# Test audio
arecord -l
# Install ALSA utils if needed
sudo apt install alsa-utils
```

**Windows:**
- Settings → Privacy → Microphone
- Enable for Python apps

### "Diarization disabled"

This is **normal** if you haven't set `HF_TOKEN`.

Single-speaker mode works perfectly. Multi-speaker requires HuggingFace token (see Configuration above).

### "LLM timeout"

**Reduce model size:**
```bash
# Use faster model
ollama pull phi3:latest
```

Then edit `ollama_client.py` to use `phi3:latest`.

### "SQLCipher error"

**Install SQLCipher:**

**macOS:**
```bash
brew install sqlcipher
```

**Linux:**
```bash
sudo apt install libsqlcipher-dev
```

**Windows:**
```bash
pip install pysqlcipher3
```

---

## Performance Tuning

### GPU Acceleration

**CUDA (NVIDIA):**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

**Metal (Apple Silicon):**
Already supported via PyTorch MPS backend.

### Reduce Memory Usage

**Use smaller models:**
- WhisperX: `tiny` or `base`
- Ollama: `phi3:latest`

**Limit context window:**
Edit `ollama_client.py`:
```python
num_ctx: int = 4096  # Reduced from 8192
```

---

## Security Best Practices

1. **Never commit `.env` files** — Already in `.gitignore`
2. **Keep HF_TOKEN private** — Don't share your token
3. **Review MPC submissions** — Only embeddings, no text
4. **Backup encrypted database** — `data/zulu_agent.db`
5. **Use strong DB password** — Configure in `.env`

---

## Next Steps

Once Dragon Mode is running:

1. **Test with real meetings** — Record team calls
2. **Review summaries** — Check LLM quality
3. **Tune parameters** — Adjust models for your hardware
4. **Explore MPC analytics** — See engagement scores
5. **Integrate with apps** — Build custom workflows

---

## Support

**Issues?** Open a GitHub issue: https://github.com/edgeconsultinglabs/zulu.cash/issues

**Questions?** Email: team@edgeconsultinglabs.com

**Hackathon Judges:** See [`DRAGON_MODE.md`](agents/zulu-mpc-agent/DRAGON_MODE.md) for technical details.

---

**🐉 Dragon Mode is ready. Deploy with confidence. 🐉**
