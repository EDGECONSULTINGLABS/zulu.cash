"""Main Whisper diarization pipeline for ZULU MPC Agent."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_core.inference import (
    DiarizationPipeline,
    DiarizedSegment,
    EmbeddingModel,
    LocalWhisper,
)
from agent_core.llm import CallSummarizer, OllamaClient
from agent_core.memory import SessionStore
from agent_core.mpc import NillionClient
from agent_core.utils import LoggerMixin, anonymize_speaker_label, hash_vector


class WhisperDiarizationAgent(LoggerMixin):
    """
    Main agent for call transcription, diarization, and MPC analysis.
    
    Pipeline:
    1. Transcribe audio with Whisper (local)
    2. Diarize speakers (local)
    3. Store utterances in encrypted SQLCipher DB (local)
    4. Summarize with Ollama (local)
    5. Extract embeddings (local)
    6. Optional: Secret-share features to Nillion for MPC computation
    """
    
    def __init__(
        self,
        db_path: str,
        whisper_config: Dict[str, Any],
        diarization_config: Dict[str, Any],
        ollama_config: Dict[str, Any],
        embeddings_config: Dict[str, Any],
        nillion_config: Optional[Dict[str, Any]] = None,
        privacy_config: Optional[Dict[str, Any]] = None,
        features_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the agent.
        
        Args:
            db_path: Path to SQLCipher database.
            whisper_config: Whisper model configuration.
            diarization_config: Diarization configuration.
            ollama_config: Ollama LLM configuration.
            embeddings_config: Embeddings model configuration.
            nillion_config: Optional Nillion MPC configuration.
            privacy_config: Privacy settings.
            features_config: Feature extraction settings.
        """
        self.logger.info("Initializing WhisperDiarizationAgent...")
        
        # Initialize components
        self.whisper = LocalWhisper(**whisper_config)
        self.diarizer = DiarizationPipeline(**diarization_config)
        self.store = SessionStore(db_path)
        self.ollama = OllamaClient(**ollama_config)
        self.summarizer = CallSummarizer(self.ollama)
        self.embedder = EmbeddingModel(**embeddings_config)
        
        # Optional MPC
        self.nillion = None
        if nillion_config and nillion_config.get('enabled'):
            self.nillion = NillionClient(**nillion_config)
        
        # Configuration
        self.privacy_config = privacy_config or {}
        self.features_config = features_config or {}
        
        self.logger.info("WhisperDiarizationAgent initialized successfully")
    
    def process_call(
        self,
        audio_path: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Process a call recording through the full pipeline.
        
        Args:
            audio_path: Path to audio file.
            meta: Optional metadata (title, tags, etc.).
            
        Returns:
            Session ID.
        """
        meta = meta or {}
        session_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        self.logger.info(f"Processing call: session_id={session_id}")
        
        try:
            # Step 1: Transcribe with Whisper
            self.logger.info("Step 1/6: Transcribing audio...")
            whisper_segments, transcription_info = self.whisper.transcribe(
                audio_path,
                language=meta.get('language', 'en'),
            )
            
            # Step 2: Diarize speakers
            self.logger.info("Step 2/6: Diarizing speakers...")
            diarized_segments = self.diarizer.diarize(
                audio_path,
                whisper_segments,
            )
            
            # Get speaker statistics
            speaker_stats = self.diarizer.get_speaker_stats(diarized_segments)
            
            # Step 3: Store utterances
            self.logger.info("Step 3/6: Storing utterances...")
            for seg in diarized_segments:
                # Anonymize speaker label if configured
                speaker_label = seg.speaker
                if self.privacy_config.get('anonymize_speakers'):
                    speaker_label = anonymize_speaker_label(seg.speaker, session_id)
                
                self.store.insert_utterance(
                    session_id=session_id,
                    speaker_label=speaker_label,
                    start_time=seg.start,
                    end_time=seg.end,
                    text=seg.text,
                    confidence=seg.confidence,
                )
            
            # Step 4: Generate summary with Ollama
            self.logger.info("Step 4/6: Generating summary...")
            summary_result = self.summarizer.summarize_call(
                diarized_segments,
                metadata=meta,
            )
            
            # Extract summary components
            summary_text = summary_result.get('summary', '')
            action_items = summary_result.get('action_items', [])
            decisions = summary_result.get('decisions', [])
            
            # Calculate duration
            duration = diarized_segments[-1].end if diarized_segments else 0
            
            # Store session
            session_metadata = {
                **meta,
                'speaker_stats': speaker_stats,
                'transcription_info': {
                    'language': transcription_info.language,
                    'language_probability': transcription_info.language_probability,
                },
                'summary_result': summary_result,
            }
            
            self.store.insert_session(
                session_id=session_id,
                started_at=start_time.isoformat(),
                ended_at=datetime.utcnow().isoformat(),
                title=meta.get('title', 'Untitled call'),
                summary=summary_text,
                metadata=session_metadata,
                audio_path=audio_path if self.privacy_config.get('store_audio_files') else None,
                duration_seconds=duration,
                language=transcription_info.language,
            )
            
            # Store action items
            for action in action_items:
                self.store.insert_action_item(
                    session_id=session_id,
                    owner_speaker=action.get('owner', 'unknown'),
                    item=action.get('item', ''),
                    due_date=action.get('due'),
                )
            
            # Store decisions
            for decision in decisions:
                self.store.insert_decision(
                    session_id=session_id,
                    decision=decision,
                )
            
            # Step 5: Extract embeddings
            if self.features_config.get('extract_embeddings', True):
                self.logger.info("Step 5/6: Extracting embeddings...")
                embedding = self.embedder.embed_summary(summary_text)
                feature_hash = hash_vector(embedding)
                
                # Step 6: MPC layer (optional)
                if self.nillion:
                    self.logger.info("Step 6/6: Processing with MPC...")
                    nillion_handle = self.nillion.secret_share_vector(embedding)
                    
                    if self.features_config.get('extract_attention_scores', True):
                        attention_score = self.nillion.compute_attention_score(nillion_handle)
                        
                        # Store MPC feature
                        self.store.insert_mpc_feature(
                            session_id=session_id,
                            feature_kind="attention_score",
                            feature_hash=feature_hash,
                            nillion_handle=nillion_handle,
                            feature_dim=len(embedding),
                            computation_result={'score': attention_score},
                        )
                        
                        # Update session with score
                        self.store.update_session_score(session_id, attention_score)
                        
                        self.logger.info(f"MPC attention score: {attention_score:.4f}")
                else:
                    self.logger.info("Step 6/6: Skipping MPC (not configured)")
            
            # Cleanup audio file if configured
            if self.privacy_config.get('cleanup_after_processing'):
                try:
                    Path(audio_path).unlink()
                    self.logger.debug(f"Cleaned up audio file: {audio_path}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup audio: {e}")
            
            self.logger.info(
                f"Call processed successfully: session_id={session_id}, "
                f"duration={duration:.1f}s, speakers={len(speaker_stats['speakers'])}"
            )
            
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to process call: {e}", exc_info=True)
            raise
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a complete summary of a session.
        
        Args:
            session_id: Session ID.
            
        Returns:
            Session summary with all details.
        """
        session = self.store.get_session(session_id)
        if not session:
            return None
        
        utterances = self.store.get_utterances(session_id)
        action_items = self.store.get_action_items(session_id)
        decisions = self.store.get_decisions(session_id)
        mpc_features = self.store.get_mpc_features(session_id)
        
        return {
            'session': session,
            'utterances': utterances,
            'action_items': action_items,
            'decisions': decisions,
            'mpc_features': mpc_features,
        }
    
    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List recent sessions.
        
        Args:
            limit: Maximum number of sessions.
            offset: Offset for pagination.
            
        Returns:
            List of session summaries.
        """
        return self.store.list_sessions(limit=limit, offset=offset)
    
    def delete_session(self, session_id: str) -> None:
        """
        Delete a session and all related data.
        
        Args:
            session_id: Session ID to delete.
        """
        self.logger.info(f"Deleting session: {session_id}")
        self.store.delete_session(session_id)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of all components.
        
        Returns:
            Health status dict.
        """
        health = {
            'whisper': True,
            'diarization': True,
            'database': True,
            'ollama': False,
            'embeddings': True,
            'nillion': False,
        }
        
        # Check Ollama
        try:
            health['ollama'] = self.ollama.check_model()
        except Exception:
            pass
        
        # Check Nillion
        if self.nillion:
            try:
                health['nillion'] = self.nillion.health_check()
            except Exception:
                pass
        
        health['overall'] = all(
            v for k, v in health.items()
            if k != 'nillion' or self.nillion  # Only check Nillion if enabled
        )
        
        return health
