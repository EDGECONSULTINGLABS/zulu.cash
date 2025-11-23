"""
ZULU Live Pipeline
Whisper → Ollama → Structured Analysis

This is the core engine behind Zulu Live Agent.
"""

import json
import whisper
import requests
from datetime import datetime
from pathlib import Path

OLLAMA_MODEL = "phi3"
OLLAMA_URL = "http://localhost:11434/api/chat"

def transcribe_audio(path: str) -> str:
    """
    Transcribe audio using local Whisper model.
    
    Args:
        path: Path to audio file
        
    Returns:
        Transcribed text
    """
    model = whisper.load_model("base")  # choose size: tiny/base/small/medium
    result = model.transcribe(path, fp16=False)
    return result["text"].strip()

def ask_ollama_system(transcript: str) -> dict:
    """
    Send transcript to local LLM, ask for summary + action items.
    
    Args:
        transcript: Raw transcript text
        
    Returns:
        Structured analysis dict
    """
    system_prompt = """
You are ZULU Live, a private on-device meeting assistant.
Given a raw transcript, return a compact JSON object with:

- "summary": 3-5 sentence summary of the conversation
- "decisions": list of key decisions made
- "actions_mine": list of action items for the user
- "actions_others": list of action items for other people (with names if clear)
- "tags": list of short topic tags

ONLY return valid JSON.
"""

    user_prompt = f"Transcript:\n{transcript}"

    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=600)
    resp.raise_for_status()
    content = resp.json()["message"]["content"]

    # Ollama returns plain text, we expect JSON in it
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: wrap in basic structure
        data = {
            "summary": content,
            "decisions": [],
            "actions_mine": [],
            "actions_others": [],
            "tags": [],
        }
    return data

def run_pipeline(audio_path: str, output_dir: str = "storage"):
    """
    Run the complete pipeline: transcribe → analyze → save.
    
    Args:
        audio_path: Path to audio file
        output_dir: Directory to save output JSON
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"[ZULU] Transcribing {audio_path}...")
    transcript = transcribe_audio(audio_path)
    
    print(f"[ZULU] Analyzing with local LLM...")
    analysis = ask_ollama_system(transcript)

    ts = datetime.utcnow().isoformat()
    out = {
        "created_at": ts,
        "audio_path": audio_path,
        "transcript": transcript,
        "analysis": analysis,
    }

    out_file = Path(output_dir) / f"meeting-{Path(audio_path).stem}.json"
    out_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[ZULU] Saved analysis → {out_file}")
    print(f"[ZULU] ✅ Complete. No cloud uploads. No telemetry.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python zulu_live_pipeline.py path/to/audio.wav")
        print("\nExample:")
        print("  python zulu_live_pipeline.py recordings/team-standup.wav")
        print("\nRequirements:")
        print("  - pip install openai-whisper requests")
        print("  - ollama pull phi3 && ollama serve")
        raise SystemExit(1)
    
    run_pipeline(sys.argv[1])
