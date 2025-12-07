# Fix Windows Microphone Permissions

## Problem
Audio stream starts but no data captured: `[X] Error: No audio data captured`

This means Windows is blocking desktop apps from accessing your microphone.

---

## Solution (3 Steps)

### Step 1: Enable Microphone for Desktop Apps

1. Press `Windows + I` to open Settings
2. Go to **Privacy & Security** → **Microphone**
3. Ensure these are ON:
   - ✅ **Microphone access**
   - ✅ **Let apps access your microphone**
   - ✅ **Let desktop apps access your microphone** ← **THIS IS KEY!**

### Step 2: Test Microphone in Windows

1. Right-click speaker icon in system tray
2. Click **Sound settings**
3. Under **Input**, select your microphone
4. **Speak** and watch the blue bar move
5. If bar doesn't move → mic is muted or wrong device selected

### Step 3: Unmute Microphone (if needed)

1. In **Sound settings** → **Input**
2. Click on your microphone device
3. Check **Mute** is OFF
4. Adjust volume slider if needed

---

## Quick Test

Run this to verify Python can access mic:

```bash
python diagnose_mic.py
```

**Expected output:**
```
[OK] ✅ Microphone is working!
    Audio levels look good.
```

**If you see:**
```
[!] WARNING: Very low audio levels!
```

Then mic is muted or permissions are still blocked.

---

## Alternative: Use Different Audio API

If permissions are correct but still doesn't work, try WASAPI:

```python
# In whisperx_live.py, change:
self.stream = sd.RawInputStream(
    device=12,  # Use device 12 (WASAPI) instead of default
    samplerate=AUDIO_RATE,
    ...
)
```

Device 12 from your system:
```
12 Microphone Array (AMD Audio Device), Windows WASAPI (2 in, 0 out)
```

---

## Test Again

After fixing permissions:

```bash
python cli.py live-whisperx --model-size medium
```

**You should see:**
```
[OK] Audio stream started (device: 1)
[OK] Audio data flowing (amplitude: 5234)  ← NEW: Shows mic is working!
[*] 🔴 Recording: 10s | Press Ctrl+C to stop
```

---

## Still Not Working?

1. **Restart terminal** after changing permissions
2. **Restart Ollama** if it's using resources
3. **Close other apps** using the mic (Teams, Zoom, etc.)
4. **Try a different mic** if you have one
5. **Check Windows Privacy Dashboard** for blocked apps

---

**Privacy Note:** ZULU only processes audio locally. Nothing is sent to the cloud.
