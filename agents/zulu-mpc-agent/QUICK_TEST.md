# Quick Test Guide for ZULU MPC Agent

## Setup Complete ✅

- Python 3.13.9 ✅
- Ollama with phi3 ✅
- Environment configured (.env created) ✅
- Dependencies installing...

## Next Steps

### 1. Install the Package

Once dependencies finish:
```powershell
pip install -e .
```

### 2. Initialize ZULU

```powershell
zulu init
```

This will:
- Create data directories
- Initialize the encrypted database
- Check system health

### 3. Test with Sample Audio

You can test with any audio file (.wav, .mp3, .m4a):

```powershell
# Process an audio file
zulu process path\to\audio.wav --title "Test Meeting"

# List sessions
zulu list

# Show details
zulu show <session_id>
```

### 4. Check System Health

```powershell
zulu health
```

Should show:
- ✅ Ollama connection
- ✅ Database initialized
- ✅ Whisper model available

## Creating Test Audio

If you don't have audio, you can:

1. **Record a quick voice memo** on your phone and transfer it
2. **Use Windows Voice Recorder** to record a test
3. **Download a sample** from YouTube (short clip)

## Troubleshooting

### If `zulu` command not found:
```powershell
python cli.py --help
```

### If Ollama connection fails:
```powershell
ollama serve
```

### If dependencies fail:
Some packages (like `sqlcipher3`) may have build issues on Windows.
You can skip them for initial testing - the agent will use regular SQLite as fallback.

## What to Expect

The agent will:
1. **Transcribe** your audio (takes ~30 seconds for 1 minute of audio)
2. **Diarize** speakers (identify who spoke when)
3. **Summarize** with Ollama (takes ~10-20 seconds)
4. **Extract** action items and decisions
5. **Save** everything to encrypted database

Output will be displayed in a nice Rich terminal UI with progress bars!
