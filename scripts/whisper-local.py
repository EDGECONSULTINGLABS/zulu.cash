"""
Whisper Local Transcription
Offline speech-to-text using Whisper.cpp
"""

import subprocess
from pathlib import Path

class WhisperLocal:
    """
    Local transcription using Whisper.cpp.
    
    No cloud APIs. Zero telemetry.
    """
    
    def __init__(self, model_path: str = "./models/ggml-base.bin"):
        self.model_path = model_path
        self.whisper_bin = self._find_whisper()
        
    def _find_whisper(self) -> Path:
        """Locate whisper.cpp binary."""
        # Check common locations
        locations = [
            Path("./whisper.cpp/main"),
            Path("/usr/local/bin/whisper"),
            Path("~/whisper.cpp/main").expanduser()
        ]
        
        for loc in locations:
            if loc.exists():
                return loc
                
        raise FileNotFoundError("whisper.cpp not found")
    
    def transcribe(self, audio_file: str) -> str:
        """
        Transcribe audio file locally.
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Transcribed text
        """
        cmd = [
            str(self.whisper_bin),
            "-m", self.model_path,
            "-f", audio_file,
            "--no-timestamps"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()
    
    def transcribe_stream(self, audio_stream):
        """Stream transcription for real-time use."""
        # TODO: Implement streaming
        pass


if __name__ == "__main__":
    whisper = WhisperLocal()
    print("ZULU Whisper - Local transcription ready")
    print("No cloud. No telemetry. Private by default.")
