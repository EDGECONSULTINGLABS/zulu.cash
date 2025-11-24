"""Local Whisper transcription model using faster-whisper."""

from pathlib import Path
from typing import List, Tuple, Optional

from faster_whisper import WhisperModel
from faster_whisper.transcribe import Segment, TranscriptionInfo

from agent_core.utils import LoggerMixin


class LocalWhisper(LoggerMixin):
    """
    Local Whisper transcription using faster-whisper.
    Runs entirely offline with local model weights.
    """
    
    def __init__(
        self,
        model_size: str = "medium",
        device: str = "auto",
        compute_type: str = "auto",
        model_dir: str = "./data/models/whisper",
    ):
        """
        Initialize Whisper model.
        
        Args:
            model_size: Model size (tiny, base, small, medium, large-v2, large-v3).
            device: Device to use (auto, cuda, cpu).
            compute_type: Compute type (auto, float16, int8).
            model_dir: Directory for model weights.
        """
        self.model_size = model_size
        
        # Auto-detect optimal settings
        if device == "auto":
            device = "cuda" if self._has_cuda() else "cpu"
        
        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"
        
        self.device = device
        self.compute_type = compute_type
        
        # Create model directory
        Path(model_dir).mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            f"Loading Whisper model: {model_size} on {device} ({compute_type})"
        )
        
        # Load model
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=model_dir,
        )
        
        self.logger.info("Whisper model loaded successfully")
    
    def _has_cuda(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except (ImportError, Exception):
            return False
    
    def transcribe(
        self,
        audio_path: str,
        language: str = "en",
        beam_size: int = 5,
        temperature: float = 0.0,
        vad_filter: bool = True,
        vad_min_silence_ms: int = 500,
    ) -> Tuple[List[Segment], TranscriptionInfo]:
        """
        Transcribe audio file.
        
        Args:
            audio_path: Path to audio file.
            language: Language code (e.g., "en", "es", "fr").
            beam_size: Beam size for decoding.
            temperature: Sampling temperature.
            vad_filter: Enable voice activity detection.
            vad_min_silence_ms: Minimum silence duration for VAD.
            
        Returns:
            Tuple of (segments, transcription_info).
        """
        self.logger.info(f"Transcribing: {audio_path}")
        
        # Configure VAD parameters
        vad_parameters = None
        if vad_filter:
            vad_parameters = dict(
                min_silence_duration_ms=vad_min_silence_ms,
                speech_pad_ms=400,
            )
        
        # Transcribe
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=beam_size,
            temperature=temperature,
            vad_filter=vad_filter,
            vad_parameters=vad_parameters,
            word_timestamps=False,  # Set to True if you need word-level timing
        )
        
        # Convert generator to list
        segments_list = list(segments)
        
        self.logger.info(
            f"Transcription complete: {len(segments_list)} segments, "
            f"language={info.language} (prob={info.language_probability:.2f})"
        )
        
        return segments_list, info
    
    def transcribe_with_progress(
        self,
        audio_path: str,
        **kwargs
    ) -> Tuple[List[Segment], TranscriptionInfo]:
        """
        Transcribe with progress logging.
        
        Args:
            audio_path: Path to audio file.
            **kwargs: Additional transcription parameters.
            
        Returns:
            Tuple of (segments, transcription_info).
        """
        from tqdm import tqdm
        
        segments, info = self.model.transcribe(audio_path, **kwargs)
        
        segments_list = []
        with tqdm(desc="Transcribing", unit="seg") as pbar:
            for segment in segments:
                segments_list.append(segment)
                pbar.update(1)
        
        return segments_list, info
    
    def get_model_info(self) -> dict:
        """Get model configuration info."""
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
        }
