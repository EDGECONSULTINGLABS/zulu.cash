"""Speaker diarization pipeline for ZULU MPC Agent."""

from dataclasses import dataclass
from typing import List, Optional

from agent_core.utils import LoggerMixin


@dataclass
class DiarizedSegment:
    """A speech segment with speaker label."""
    speaker: str
    start: float
    end: float
    text: str
    confidence: Optional[float] = None


class DiarizationPipeline(LoggerMixin):
    """
    Speaker diarization pipeline.
    
    Supports multiple backends:
    - simple: Alternating speakers (MVP, no ML)
    - pyannote: PyAnnote.audio models (requires HuggingFace token)
    - whisperx: WhisperX diarization (future)
    """
    
    def __init__(
        self,
        backend: str = "simple",
        min_speakers: int = 1,
        max_speakers: int = 10,
        hf_token: Optional[str] = None,
    ):
        """
        Initialize diarization pipeline.
        
        Args:
            backend: Diarization backend (simple, pyannote, whisperx).
            min_speakers: Minimum number of speakers.
            max_speakers: Maximum number of speakers.
            hf_token: HuggingFace token for pyannote models.
        """
        self.backend = backend
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        self.hf_token = hf_token
        
        self.logger.info(f"Initializing diarization with backend: {backend}")
        
        # Load backend
        if backend == "pyannote":
            self._init_pyannote()
        elif backend == "whisperx":
            self._init_whisperx()
        elif backend == "simple":
            self.logger.warning(
                "Using simple diarization (alternating speakers). "
                "For production, consider pyannote or whisperx."
            )
        else:
            raise ValueError(f"Unknown diarization backend: {backend}")
    
    def _init_pyannote(self) -> None:
        """Initialize PyAnnote.audio pipeline."""
        try:
            from pyannote.audio import Pipeline
            
            if not self.hf_token:
                raise ValueError(
                    "HuggingFace token required for pyannote. "
                    "Set HF_TOKEN environment variable or pass hf_token parameter."
                )
            
            self.logger.info("Loading pyannote diarization pipeline...")
            
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token,
            )
            
            # Move to GPU if available
            import torch
            if torch.cuda.is_available():
                self.pipeline.to(torch.device("cuda"))
            
            self.logger.info("PyAnnote pipeline loaded")
            
        except ImportError:
            raise ImportError(
                "pyannote.audio not installed. "
                "Install with: pip install pyannote.audio"
            )
    
    def _init_whisperx(self) -> None:
        """Initialize WhisperX diarization."""
        try:
            import whisperx
            self.whisperx = whisperx
            self.logger.info("WhisperX available")
        except ImportError:
            raise ImportError(
                "whisperx not installed. "
                "Install with: pip install whisperx"
            )
    
    def diarize(
        self,
        audio_path: str,
        whisper_segments: List,
    ) -> List[DiarizedSegment]:
        """
        Perform speaker diarization.
        
        Args:
            audio_path: Path to audio file.
            whisper_segments: Whisper transcription segments.
            
        Returns:
            List of diarized segments with speaker labels.
        """
        if self.backend == "simple":
            return self._diarize_simple(whisper_segments)
        elif self.backend == "pyannote":
            return self._diarize_pyannote(audio_path, whisper_segments)
        elif self.backend == "whisperx":
            return self._diarize_whisperx(audio_path, whisper_segments)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
    
    def _diarize_simple(
        self,
        whisper_segments: List,
    ) -> List[DiarizedSegment]:
        """
        Simple diarization: alternate between speakers.
        This is a minimal MVP - replace with real diarization in production.
        """
        diarized = []
        num_speakers = min(2, self.max_speakers)  # Default to 2 speakers
        
        for i, seg in enumerate(whisper_segments):
            speaker_id = (i % num_speakers) + 1
            diarized.append(
                DiarizedSegment(
                    speaker=f"SPK_{speaker_id}",
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                    confidence=getattr(seg, 'avg_logprob', None),
                )
            )
        
        self.logger.info(f"Simple diarization: {len(diarized)} segments")
        return diarized
    
    def _diarize_pyannote(
        self,
        audio_path: str,
        whisper_segments: List,
    ) -> List[DiarizedSegment]:
        """
        Diarize using PyAnnote.audio.
        """
        self.logger.info("Running pyannote diarization...")
        
        # Run diarization
        diarization = self.pipeline(
            audio_path,
            min_speakers=self.min_speakers,
            max_speakers=self.max_speakers,
        )
        
        # Map Whisper segments to speakers
        diarized = []
        
        for seg in whisper_segments:
            # Find dominant speaker for this segment
            seg_start = seg.start
            seg_end = seg.end
            seg_duration = seg_end - seg_start
            
            # Get speaker timeline for this segment
            speaker_times = {}
            
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                # Check if this turn overlaps with our segment
                overlap_start = max(turn.start, seg_start)
                overlap_end = min(turn.end, seg_end)
                overlap = overlap_end - overlap_start
                
                if overlap > 0:
                    speaker_times[speaker] = speaker_times.get(speaker, 0) + overlap
            
            # Assign to speaker with most time in this segment
            if speaker_times:
                dominant_speaker = max(speaker_times, key=speaker_times.get)
            else:
                dominant_speaker = "SPEAKER_00"  # Fallback
            
            diarized.append(
                DiarizedSegment(
                    speaker=dominant_speaker,
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                    confidence=getattr(seg, 'avg_logprob', None),
                )
            )
        
        self.logger.info(
            f"PyAnnote diarization: {len(diarized)} segments, "
            f"{len(set(s.speaker for s in diarized))} speakers"
        )
        
        return diarized
    
    def _diarize_whisperx(
        self,
        audio_path: str,
        whisper_segments: List,
    ) -> List[DiarizedSegment]:
        """
        Diarize using WhisperX.
        """
        # TODO: Implement WhisperX diarization
        # This is a placeholder for future implementation
        raise NotImplementedError("WhisperX diarization not yet implemented")
    
    def get_speaker_stats(
        self,
        segments: List[DiarizedSegment],
    ) -> dict:
        """
        Get statistics about speakers.
        
        Returns:
            Dict with speaker statistics (time, segments, etc.).
        """
        speaker_times = {}
        speaker_segments = {}
        
        for seg in segments:
            duration = seg.end - seg.start
            speaker_times[seg.speaker] = speaker_times.get(seg.speaker, 0) + duration
            speaker_segments[seg.speaker] = speaker_segments.get(seg.speaker, 0) + 1
        
        return {
            "num_speakers": len(speaker_times),
            "speakers": list(speaker_times.keys()),
            "speaking_time": speaker_times,
            "segment_count": speaker_segments,
            "total_time": sum(speaker_times.values()),
        }
