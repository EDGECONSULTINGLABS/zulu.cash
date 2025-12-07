"""
Live audio capture with WhisperX ASR and speaker diarization.

This module provides real-time audio recording and processing using:
- sounddevice for audio capture
- WhisperX for high-quality ASR with word-level timestamps
- PyAnnote-based diarization for speaker identification
"""

import os
import tempfile
import queue
from dataclasses import dataclass
from typing import List, Optional

import sounddevice as sd
import numpy as np

# CRITICAL: Monkey-patch torch.load BEFORE importing torch fully
# PyTorch 2.6+ has weights_only=True by default which breaks PyAnnote
import torch
_original_load = torch.load

def _patched_load(*args, **kwargs):
    """Force weights_only=False for PyAnnote compatibility."""
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)

torch.load = _patched_load
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'

# WhisperX imports (installed separately)
try:
    import whisperx
    WHISPERX_AVAILABLE = True
except ImportError:
    WHISPERX_AVAILABLE = False
    print("[!] WhisperX not available. Install with: pip install whisperx")


AUDIO_RATE = 16000
CHUNK = 4096


@dataclass
class Turn:
    """Represents a single speaker turn in a conversation."""
    speaker: str
    start: float
    end: float
    text: str


class WhisperXLive:
    """
    Live audio capture and processing pipeline.
    
    Records audio from microphone, then processes with:
    - WhisperX ASR (state-of-the-art transcription)
    - Word-level alignment
    - Speaker diarization (PyAnnote)
    
    All processing happens locally - no data leaves the device.
    """

    def __init__(self, device: Optional[str] = None, model_size: str = "medium"):
        """
        Initialize WhisperX live agent.
        
        Args:
            device: 'cuda', 'cpu', or None (auto-detect)
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        """
        if not WHISPERX_AVAILABLE:
            raise ImportError(
                "WhisperX is not installed. "
                "Install with: pip install whisperx"
            )
        
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_size = model_size
        self._asr_model = None
        self._align_model = None
        self._diar_model = None
        self.q: queue.Queue[bytes] = queue.Queue()
        self.stop_flag = False
        self.stream = None

    # ---------- Audio Capture ----------

    def _callback(self, indata, frames, time_info, status):
        """Callback for sounddevice audio stream."""
        if status:
            print(f"[!] Audio status: {status}")
        self.q.put(bytes(indata))

    def start_recording(self):
        """Start capturing audio from the microphone."""
        # Removed print - parent agent handles UI feedback
        self.stop_flag = False
        self.stream = sd.RawInputStream(
            samplerate=AUDIO_RATE,
            blocksize=CHUNK,
            channels=1,
            dtype="int16",
            callback=self._callback,
        )
        self.stream.start()

    def stop_recording(self) -> str:
        """
        Stop recording and save audio to temporary file.
        
        Returns:
            Path to temporary WAV file containing the recording
        """
        # Removed print - parent agent handles UI feedback
        self.stop_flag = True
        
        if self.stream:
            self.stream.stop()
            self.stream.close()

        # Combine all audio chunks
        audio_bytes = b"".join(list(self.q.queue))
        audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

        # Save to temporary WAV file
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        
        import soundfile as sf
        sf.write(tmp_wav.name, audio_np, AUDIO_RATE)
        tmp_wav.close()
        
        print(f"[*] Audio saved to: {tmp_wav.name}")
        return tmp_wav.name

    # ---------- WhisperX Processing Stack ----------

    def _load_models(self):
        """Lazy-load WhisperX models (ASR, alignment, diarization)."""
        if self._asr_model is not None:
            return

        print(f"[*] Loading WhisperX {self.model_size} on {self.device}...")
        self._asr_model = whisperx.load_model(
            self.model_size, 
            self.device,
            compute_type="int8" if self.device == "cpu" else "float16"
        )

        # Alignment model for word-level timestamps
        print("[*] Loading alignment model...")
        self._align_model, self._metadata = whisperx.load_align_model(
            language_code="en", 
            device=self.device
        )

        # Diarization model - DISABLED for demo (version conflicts)
        # TODO: Migrate to WhisperX 3.7+ diarization API or use Python 3.10
        print("[!] Diarization disabled (all speakers labeled as SPEAKER_00)")
        self._diar_model = None

    def transcribe_and_diarize(self, wav_path: str) -> List[Turn]:
        """
        Process audio file with WhisperX pipeline.
        
        Args:
            wav_path: Path to WAV file
            
        Returns:
            List of Turn objects with speaker labels and timestamps
        """
        self._load_models()

        # Step 1: ASR (transcription)
        print("[*] Running ASR...")
        asr_result = self._asr_model.transcribe(wav_path)

        # Step 2: Alignment (word-level timestamps)
        print("[*] Aligning...")
        asr_result = whisperx.align(
            asr_result["segments"],
            self._align_model,
            self._metadata,
            wav_path,
            self.device,
        )

        # Step 3: Diarization (speaker identification)
        if self._diar_model is not None:
            print("[*] Running diarization...")
            diar_result = self._diar_model(wav_path)

            print("[*] Assigning speakers...")
            asr_result = whisperx.assign_word_speakers(diar_result, asr_result)
        else:
            print("[!] Skipping diarization (no HF_TOKEN)")

        # Convert to Turn objects
        turns: List[Turn] = []
        for seg in asr_result["segments"]:
            speaker = seg.get("speaker", "SPEAKER_00")
            text = seg.get("text", "").strip()
            if not text:
                continue
                
            turns.append(
                Turn(
                    speaker=speaker,
                    start=float(seg["start"]),
                    end=float(seg["end"]),
                    text=text,
                )
            )

        print(f"[OK] Processed {len(turns)} speaker turns")
        return turns
