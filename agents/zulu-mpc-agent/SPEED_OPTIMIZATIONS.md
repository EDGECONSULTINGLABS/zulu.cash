# Speed Optimizations for ZULU Live Agent

## Problem: Slow Startup (15-25 seconds)

The live agent loads multiple large AI models:
- Sentence transformers: 384MB
- WhisperX: 484MB - 2.9GB
- PyAnnote diarization: ~500MB
- Total: **~1.4GB - 3.7GB** of models in RAM

---

## Quick Fixes

### 1. Use Tiny Model (Fastest) ⚡
```bash
python cli.py live-whisperx --model-size tiny --no-mpc

# Startup: ~3-5 seconds
# Model: 75MB (vs 484MB for small)
# Trade-off: Lower transcription accuracy
```

### 2. Skip Diarization (10s Faster) 🏃
```bash
# Unset HF_TOKEN to disable diarization
unset HF_TOKEN  # Linux/Mac
Remove-Item Env:HF_TOKEN  # PowerShell

python cli.py live-whisperx --model-size small --no-mpc

# Saves: ~5-8 seconds
# Trade-off: All speakers labeled as "SPEAKER_00"
```

### 3. Disable MPC (2s Faster) 💨
```bash
python cli.py live-whisperx --model-size small --no-mpc

# Already doing this with --no-mpc flag
# Saves: ~1-2 seconds
```

### 4. Use GPU (5-10x Faster) 🚀
```bash
# Requires CUDA-capable GPU
# Models load faster from VRAM
# Inference is 5-10x faster

python cli.py live-whisperx --model-size medium
# (GPU auto-detected if available)
```

---

## Model Size Comparison

| Model | Size | Load Time | Accuracy | Best For |
|-------|------|-----------|----------|----------|
| **tiny** | 75MB | ~3s | 📊 Good | Quick tests, demos |
| **base** | 145MB | ~4s | 📊📊 Better | Fast processing |
| **small** | 484MB | ~5s | 📊📊📊 Good | Default choice |
| **medium** | 1.5GB | ~8s | 📊📊📊📊 Great | Production |
| **large** | 2.9GB | ~12s | 📊📊📊📊📊 Best | Maximum accuracy |

---

## Permanent Optimizations

### Create Fast-Start Script

**File:** `quick_agent.sh` (Linux/Mac) or `quick_agent.ps1` (Windows)

```bash
#!/bin/bash
# Quick-start ZULU with minimal models
export HF_TOKEN=""  # Disable diarization
python cli.py live-whisperx --model-size tiny --no-mpc --keep-audio
```

**PowerShell:**
```powershell
# quick_agent.ps1
$env:HF_TOKEN = ""
python cli.py live-whisperx --model-size tiny --no-mpc --keep-audio
```

Then run:
```bash
./quick_agent.sh  # Or .\quick_agent.ps1 on Windows
```

---

## Why Each Component Takes Time

### 1. Sentence Transformers (~4s)
**What:** Converts text to 384-dimensional vectors  
**Why slow:** 384MB model + computation graph  
**Can skip?** ❌ No - needed for embeddings

### 2. WhisperX Model (~5-10s)
**What:** Speech-to-text transcription  
**Why slow:** Large neural network (484MB - 2.9GB)  
**Can skip?** ❌ No - core feature

### 3. PyAnnote Diarization (~5-8s)
**What:** Identifies different speakers  
**Why slow:** Deep learning speaker embeddings  
**Can skip?** ✅ Yes - all speech labeled as one speaker

### 4. Ollama Client (~1s)
**What:** Connects to local LLM for summaries  
**Why slow:** Network request to localhost:11434  
**Can skip?** ✅ Yes - but no summary generation

---

## Advanced: Pre-load Models (Fastest Repeated Use)

### Keep Agent Running as Service

Instead of starting fresh each time, run the agent as a service:

**Option A: Leave it running**
```bash
# Start agent once
python cli.py live-whisperx

# Models stay in RAM between recordings
# Subsequent calls: instant start
```

**Option B: Create daemon mode** (future enhancement)
```python
# Future feature: background service
zulu daemon start  # Models loaded once
zulu record       # Instant start
zulu daemon stop  # Cleanup
```

---

## GPU Acceleration (10x Speedup)

If you have NVIDIA GPU:

```bash
# Check CUDA availability
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# If True, models auto-use GPU:
python cli.py live-whisperx --model-size medium

# Results:
# - Model load: 3-5s (vs 8-12s on CPU)
# - Transcription: 2-3s per 5min (vs 30s on CPU)
# - Diarization: 1-2s (vs 5-8s on CPU)
```

---

## Caching (Second Run is Faster)

**First run:** 15-25 seconds (downloads + loads)  
**Second run:** 5-10 seconds (loads only)

Models are cached in:
```
~/.cache/huggingface/hub/
C:\Users\<you>\.cache\huggingface\hub\  (Windows)
```

Once downloaded, subsequent runs only load from disk.

---

## Recommended Configurations

### For Demo (Fast Start)
```bash
python cli.py live-whisperx --model-size tiny --no-mpc
# Startup: ~3-5s
# Good enough for showing it works
```

### For Development (Balanced)
```bash
python cli.py live-whisperx --model-size small --no-mpc
# Startup: ~8-10s
# Good accuracy, reasonable speed
```

### For Production (Best Quality)
```bash
python cli.py live-whisperx --model-size medium
# Startup: ~12-15s
# High accuracy, MPC enabled
```

### For Maximum Speed (GPU)
```bash
# Requires CUDA GPU
python cli.py live-whisperx --model-size large
# Startup: ~5-8s (on GPU)
# Processing: 10x faster than CPU
```

---

## Comparison: ZULU vs Competitors

### ZULU (Local)
- **First start:** 15-25s (model loading)
- **Processing:** 30s per 5min (CPU), 3s per 5min (GPU)
- **Privacy:** 100% local, zero data leakage

### Otter/Fireflies (Cloud)
- **First start:** Instant (no local models)
- **Processing:** 10-30s per 5min (their servers)
- **Privacy:** ❌ Your audio on their servers

**Trade-off:**  
ZULU is slower to start but **keeps your data private**.  
Competitors are faster but **upload everything to the cloud**.

---

## Future Optimizations (Roadmap)

1. **Model quantization** - Reduce model size by 50-75%
2. **Lazy loading** - Load models only when needed
3. **Daemon mode** - Keep models in RAM between recordings
4. **Streaming inference** - Start transcribing during recording
5. **Model preloading** - Background service loads on system startup

---

## Bottom Line

**Current:**
- Cold start: 15-25 seconds (downloading + loading models)
- Warm start: 5-10 seconds (loading only)
- With GPU: 3-5 seconds

**This is normal for local AI.**

**Why it's worth it:**
- Your data stays private
- No cloud API calls
- No monthly fees
- Complete control

**For fastest demo:**
```bash
python cli.py live-whisperx --model-size tiny --no-mpc
```

**Starts in ~5 seconds and proves the concept.** 🚀
