"""
Quick test script for ZULU Live Pipeline
Generates a test audio file and runs the full pipeline
"""

import os
import sys
import subprocess
from pathlib import Path

def check_ollama():
    """Check if Ollama is running"""
    import requests
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama is running")
            return True
    except:
        pass
    
    print("❌ Ollama is not running")
    print("   Start with: ollama serve")
    print("   Then pull a model: ollama pull phi3")
    return False

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        subprocess.run(["ffmpeg", "-version"], 
                      capture_output=True, 
                      check=True)
        print("✅ FFmpeg is installed")
        return True
    except:
        print("❌ FFmpeg not found")
        print("   Install from: https://ffmpeg.org/download.html")
        return False

def generate_test_audio():
    """Generate a simple test audio file using text-to-speech"""
    test_file = "test_audio.wav"
    
    # Try to generate with system TTS (Windows)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        
        test_text = """
        Good morning team. This is our Q4 planning meeting.
        We need to discuss three main topics today:
        First, budget allocation for the new product line.
        Second, hiring timeline for two senior engineers.
        Third, marketing strategy for the holiday season.
        Let's start with the budget discussion.
        Sarah, can you present the initial numbers?
        """
        
        engine.save_to_file(test_text, test_file)
        engine.runAndWait()
        
        if os.path.exists(test_file):
            print(f"✅ Generated test audio: {test_file}")
            return test_file
    except Exception as e:
        print(f"⚠️  Could not generate test audio: {e}")
        print("   Install pyttsx3: pip install pyttsx3")
        print("   Or provide your own audio file")
        return None

def run_pipeline(audio_file):
    """Run the ZULU pipeline"""
    if not os.path.exists(audio_file):
        print(f"❌ Audio file not found: {audio_file}")
        return False
    
    print(f"\n🚀 Running ZULU pipeline on {audio_file}...")
    print("   This may take a minute...")
    
    try:
        result = subprocess.run(
            [sys.executable, "scripts/zulu_live_pipeline.py", audio_file],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Pipeline timed out (>5 minutes)")
        return False
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ZULU LOCAL TEST")
    print("=" * 60)
    print()
    
    # Check prerequisites
    print("Checking prerequisites...")
    ollama_ok = check_ollama()
    ffmpeg_ok = check_ffmpeg()
    
    if not (ollama_ok and ffmpeg_ok):
        print("\n❌ Prerequisites not met. Please install missing components.")
        sys.exit(1)
    
    print()
    
    # Use provided audio or generate test
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        print(f"Using provided audio: {audio_file}")
    else:
        print("Generating test audio...")
        audio_file = generate_test_audio()
        
        if not audio_file:
            print("\n❌ No audio file available")
            print("Usage: python test_pipeline.py [path/to/audio.wav]")
            sys.exit(1)
    
    # Run pipeline
    success = run_pipeline(audio_file)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ ZULU PIPELINE TEST SUCCESSFUL!")
        print("=" * 60)
        print("\nCheck storage/ directory for output JSON")
    else:
        print("\n" + "=" * 60)
        print("❌ ZULU PIPELINE TEST FAILED")
        print("=" * 60)
        sys.exit(1)
