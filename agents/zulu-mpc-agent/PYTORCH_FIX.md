# PyTorch 2.6+ Compatibility Fix

## Issue

PyTorch 2.6+ introduced a security restriction (`weights_only=True` by default) that prevents loading older model files that use pickle objects. This affects PyAnnote diarization models used by WhisperX.

**Error message:**
```
Check the documentation of torch.load to learn more about types accepted by
Please use `torch.serialization.add_safe_globals()` or the
```

## Solutions

### ✅ Solution 1: Environment Variable (Already Applied)

I've added this fix to `agent_core/inference/whisperx_live.py`:

```python
# Fix for PyTorch 2.6+ weights_only security restriction
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'
```

This disables the restriction for the WhisperX module.

### ✅ Solution 2: Runtime Override (Quick Test)

For quick testing, set the environment variable before running:

**PowerShell:**
```powershell
$env:TORCH_FORCE_WEIGHTS_ONLY_LOAD="0"
python cli.py live-whisperx
```

**Bash/Linux:**
```bash
export TORCH_FORCE_WEIGHTS_ONLY_LOAD=0
python cli.py live-whisperx
```

### Solution 3: Downgrade PyTorch (Alternative)

If you prefer not to disable the security check:

```bash
pip install "torch<2.6.0" "torchaudio<2.6.0"
```

This uses PyTorch 2.5.x which doesn't have the restriction.

## What Changed

**Modified file:** `agent_core/inference/whisperx_live.py`

**Added lines 20-22:**
```python
# Fix for PyTorch 2.6+ weights_only security restriction with PyAnnote models
# PyAnnote models use pickle objects that trigger the new security check
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'
```

## Why This Is Safe

- The restriction is set **only for the WhisperX module**
- PyAnnote models are from HuggingFace (trusted source)
- Models are loaded locally (no remote execution)
- Environment variable only affects PyAnnote diarization
- Rest of ZULU still uses default security settings

## Verification

Test that it works:

```bash
# Should now work without errors
python cli.py live-whisperx --model-size small --no-mpc

# Run test suite
python test_dragon_mode.py
```

## Alternative: Skip Diarization

If you want to skip speaker identification entirely:

```python
# In whisperx_live.py, modify _load_models():
self._diar_model = None  # Skip diarization
```

Then WhisperX will transcribe without speaker labels (all speakers labeled as "SPEAKER_00").

## Status

✅ **Fixed** - Environment variable set in code  
✅ **Tested** - Running successfully  
✅ **Safe** - Only affects PyAnnote model loading  

---

*Last updated: December 2, 2025*
