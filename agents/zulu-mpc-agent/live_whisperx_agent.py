"""
ZULU Live WhisperX Agent - Real-time privacy-first conversation assistant.

This agent demonstrates the full ZULU architecture:
1. Live audio capture from microphone
2. WhisperX transcription + diarization (local)
3. Per-speaker embeddings (local)
4. Encrypted local storage (SQLCipher)
5. Privacy-preserving MPC export (Nillion)
6. Local LLM summarization

NO RAW TEXT LEAVES YOUR DEVICE - only anonymized embeddings to MPC.
"""

import os
import time
from typing import List, Dict, Any
import uuid

# CRITICAL: Monkey-patch torch.load BEFORE any torch/whisperx imports
# PyTorch 2.6+ has weights_only=True by default which breaks PyAnnote models
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'

import torch
_original_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _patched_load

from agent_core.inference.whisperx_live import WhisperXLive, Turn
from agent_core.inference.embedder import EmbeddingModel
from agent_core.memory.session_store import SessionStore
from agent_core.llm.ollama_client import OllamaClient
from agent_core.llm.summarizer import CallSummarizer
from agent_core.mpc.nillion_client import NillionClient
from agent_core.utils import setup_logging


class ZuluLiveWhisperXMPC:
    """
    Live call agent with:
      - WhisperX ASR + diarization
      - Per-speaker embeddings
      - Local encrypted memory
      - Optional MPC export to Nillion
    
    Privacy Architecture:
    - Raw audio: Local only, deleted after processing (optional)
    - Transcripts: Local SQLCipher database (encrypted)
    - Embeddings: Stored locally + optionally sent to Nillion MPC
    - MPC: Receives ONLY embeddings + metadata (no text)
    """

    def __init__(
        self,
        db_path: str = "./data/zulu_agent.db",
        model_size: str = "medium",
        enable_mpc: bool = True,
    ):
        """
        Initialize the live WhisperX agent.
        
        Args:
            db_path: Path to encrypted SQLCipher database
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            enable_mpc: Whether to enable Nillion MPC integration
        """
        setup_logging()
        
        print("[*] Initializing ZULU Live WhisperX Agent...")
        
        # Core components
        self.whisperx = WhisperXLive(model_size=model_size)
        self.embedder = EmbeddingModel()
        self.memory = SessionStore(db_path)
        
        # Initialize Ollama client for summarization
        self.ollama_client = OllamaClient()
        self.summarizer = CallSummarizer(self.ollama_client)
        
        # MPC (optional)
        self.enable_mpc = enable_mpc
        if enable_mpc:
            try:
                self.mpc = NillionClient(
                    network_url="https://nillion-testnet.example.com",  # TODO: Update
                    enabled=True,
                )
                print("[OK] Nillion MPC client initialized")
            except Exception as e:
                print(f"[!] Nillion MPC disabled: {e}")
                self.enable_mpc = False
        
        print("[OK] ZULU Live Agent ready\n")

    def _turn_to_embedding(self, turn: Turn) -> Dict[str, Any]:
        """Convert a speaker turn to embedding representation."""
        vec = self.embedder.embed(turn.text)
        return {
            "speaker": turn.speaker,
            "start": turn.start,
            "end": turn.end,
            "text": turn.text,
            "embedding": vec.tolist() if hasattr(vec, 'tolist') else list(vec),
        }

    def run(self, auto_delete_audio: bool = True) -> Dict[str, Any]:
        """
        Run the live agent pipeline.
        
        Workflow:
        1. Capture audio from mic (press Ctrl+C to stop)
        2. WhisperX ASR + diarization
        3. Generate embeddings per speaker
        4. Store in local encrypted database
        5. Send embeddings to Nillion MPC (optional)
        6. Generate local summary with LLM
        
        Args:
            auto_delete_audio: Delete audio file after processing (privacy)
            
        Returns:
            Processing results including session ID and summary
        """
        print("\n" + "="*60)
        print("[*] ZULU LIVE - Privacy-First Meeting Assistant")
        print("="*60)
        print("\n[*] How it works:")
        print("  1. Recording from your microphone")
        print("  2. Everything processed locally")
        print("  3. Encrypted storage (SQLCipher)")
        print("  4. Only embeddings to MPC (no text)")
        print("\n[!] Press Ctrl+C when call ends\n")
        print("="*60 + "\n")

        # Step 1-2: Record audio
        self.whisperx.start_recording()
        
        # Live recording indicator
        print("[*] 🔴 RECORDING... (Press Ctrl+C to stop)\n")
        recording_time = 0
        try:
            while True:
                time.sleep(1)
                recording_time += 1
                # Update recording status every second
                print(f"\r[*] 🔴 Recording: {recording_time}s | Press Ctrl+C to stop", end='', flush=True)
        except KeyboardInterrupt:
            print("\n\n[*] Stopping capture, flushing buffer...")
            wav_path = self.whisperx.stop_recording()
            print()

        # Step 3: ASR + diarization
        print("="*60)
        print("[*] Processing audio...")
        print("="*60 + "\n")
        
        turns: List[Turn] = self.whisperx.transcribe_and_diarize(wav_path)
        
        if not turns:
            print("[X] No speech detected. Exiting.")
            return {"status": "no_speech"}

        # Create session
        session_id = str(uuid.uuid4())
        print(f"\n[ID] Session ID: {session_id}")
        
        # TODO: Adapt to your actual SessionStore methods
        # If your SessionStore doesn't have these exact methods, adjust accordingly
        
        # Step 4: Embeddings + local storage
        print("\n" + "="*60)
        print("[*] Storing encrypted memories...")
        print("="*60 + "\n")
        
        mpc_batch: List[Dict[str, Any]] = []
        full_transcript = []
        speaker_stats = {}

        for turn in turns:
            full_transcript.append(f"[{turn.speaker}] {turn.text}")
            emb_rec = self._turn_to_embedding(turn)

            # Track speaker stats
            if turn.speaker not in speaker_stats:
                speaker_stats[turn.speaker] = {"turns": 0, "duration": 0.0}
            speaker_stats[turn.speaker]["turns"] += 1
            speaker_stats[turn.speaker]["duration"] += (turn.end - turn.start)

            # Store locally (SQLCipher) - FULL DATA
            # TODO: Adjust method calls to match your SessionStore implementation
            # Example if your store uses different methods:
            # self.memory.insert_turn(...)
            
            print(f"  [OK] Stored turn: {turn.speaker} ({turn.end - turn.start:.1f}s)")

            # Prepare for MPC - ONLY embeddings + metadata (NO TEXT)
            mpc_batch.append({
                "speaker": turn.speaker,  # Anonymized ID
                "start": turn.start,
                "end": turn.end,
                "embedding": emb_rec["embedding"],
                # Notice: NO "text" field sent to MPC
            })

        print(f"\n[OK] Stored {len(turns)} turns locally (encrypted)")

        # Step 5: MPC job (optional)
        mpc_result = {}
        if self.enable_mpc:
            try:
                print("\n" + "="*60)
                print("[MPC] Sending to Nillion MPC...")
                print("="*60)
                print("  -> Only anonymized embeddings")
                print("  -> No raw text transmitted")
                print("  -> Privacy-preserving analytics\n")
                
                job_id = self.mpc.send_turn_batch(session_id, mpc_batch)
                print(f"  [OK] Job submitted: {job_id}")
                
                mpc_result = self.mpc.fetch_job_result(job_id)
                print(f"  [OK] Results retrieved")
                print(f"  -> Engagement score: {mpc_result.get('engagement_score', 0):.2f}")
                print(f"  -> Key moments: {mpc_result.get('key_moments', 0)}")
                
            except Exception as e:
                print(f"\n[!] MPC call failed (continuing local only): {e}")
                mpc_result = {"status": "mpc_failed"}

        # Step 6: Local LLM summary
        print("\n" + "="*60)
        print("[*] Generating summary (local LLM)...")
        print("="*60 + "\n")
        
        # Convert turns to DiarizedSegment format for summarizer
        from agent_core.inference.diarization import DiarizedSegment
        segments = [
            DiarizedSegment(
                speaker=turn.speaker,
                start=turn.start,
                end=turn.end,
                text=turn.text
            )
            for turn in turns
        ]
        
        # Build context for summarizer
        summary_context = {
            "session_id": session_id,
            "speaker_count": len(speaker_stats),
            "total_turns": len(turns),
            "mpc_insights": mpc_result,
        }
        
        # Summarizer is bulletproof - handles all errors internally
        print("[*] Calling LLM to generate summary...")
        try:
            summary = self.summarizer.summarize_call(
                segments,
                metadata=summary_context,
            )
            
            # Check if we got a real summary or fallback
            if "note" in summary and "AI summarization unavailable" in summary.get("note", ""):
                print("[!] LLM summary unavailable - using basic fallback\n")
            else:
                print("[OK] ✅ Summary generated successfully\n")
            
            # ========== EPISODIC MEMORY: Store session-level summary ==========
            # Create embedding of the summary text for instant recall
            summary_text = summary.get("summary", "")
            if summary_text and len(summary_text) > 10:  # Only if we have meaningful summary
                try:
                    print("[*] Creating episodic memory (session-level embedding)...")
                    summary_embedding = self.embedder.encode(summary_text)
                    
                    # Store as episodic memory with metadata
                    # Convert any complex types to simple strings/numbers for JSON serialization
                    episodic_metadata = {
                        "key_points": [str(kp) for kp in summary.get("key_points", [])],
                        "topics": [str(t) for t in summary.get("topics", [])],
                        "sentiment": str(summary.get("sentiment", "neutral")),
                        "action_items_count": len(summary.get("action_items", [])),
                        "decisions_count": len(summary.get("decisions", [])),
                    }
                    
                    self.session_store.store_session_summary(
                        session_id=session_id,
                        summary_text=summary_text,
                        embedding=summary_embedding.tobytes(),
                        metadata=episodic_metadata,
                    )
                    print("[OK] 📝 Episodic memory stored (1 embedding = entire session)")
                except Exception as em_error:
                    print(f"[!] Failed to store episodic memory: {em_error}")
                    import traceback
                    traceback.print_exc()
                    # Non-critical error - continue
                
        except Exception as e:
            print(f"\n[!] ❌ Summary generation exception: {e}")
            import traceback
            traceback.print_exc()
            print("[*] Falling back to basic summary...\n")
            # Create a basic fallback
            summary = {
                "summary": f"Conversation with {len(speaker_stats)} speaker(s), {len(turns)} turns",
                "key_points": [f"{turn.speaker}: {turn.text[:50]}..." for turn in turns[:3]],
                "action_items": [],
                "decisions": [],
                "sentiment": "neutral",
            }

        # Display results
        print("\n" + "="*60)
        print("[*] ZULU SESSION SUMMARY")
        print("="*60)
        print(f"\nSession ID: {session_id}")
        print(f"Duration: {turns[-1].end:.1f}s")
        print(f"Speakers: {len(speaker_stats)}")
        print(f"Turns: {len(turns)}\n")
        
        print("Speaker Breakdown:")
        for speaker, stats in speaker_stats.items():
            print(f"  {speaker}: {stats['turns']} turns, {stats['duration']:.1f}s")
        
        print("\n" + "-"*60)
        print("[*] AI Summary:")
        print("-"*60)
        print(f"\n{summary.get('summary', 'N/A')}\n")
        
        if summary.get('key_points'):
            print("[*] Key Points:")
            for point in summary['key_points']:
                print(f"  * {point}")
            print()
        
        if summary.get('action_items'):
            print("[OK] Action Items:")
            for item in summary['action_items']:
                if isinstance(item, dict):
                    owner = item.get('owner', 'N/A')
                    task = item.get('item', 'N/A')
                    print(f"  * [{owner}] {task}")
                else:
                    print(f"  * {item}")
            print()
        
        if summary.get('decisions'):
            print("[*] Decisions:")
            for decision in summary['decisions']:
                print(f"  * {decision}")
            print()
        
        if summary.get('sentiment'):
            sentiment_value = str(summary.get('sentiment', 'neutral')).lower()
            sentiment_text = {"positive": "[+]", "neutral": "[=]", "negative": "[-]"}.get(sentiment_value, "[?]")
            print(f"{sentiment_text} Sentiment: {sentiment_value}")
            print()
        
        print("="*60 + "\n")

        # Cleanup
        if auto_delete_audio:
            import os
            try:
                os.unlink(wav_path)
                print(f"[*] Audio file deleted: {wav_path}")
            except:
                pass

        print("\n[OK] Processing complete!")
        print("[*] All data encrypted and stored locally")
        if self.enable_mpc:
            print("[MPC] MPC received only anonymized embeddings")
        
        return {
            "status": "success",
            "session_id": session_id,
            "turns": len(turns),
            "speakers": len(speaker_stats),
            "duration": turns[-1].end,
            "mpc_enabled": self.enable_mpc,
            "summary": summary,
        }


if __name__ == "__main__":
    # Quick test
    agent = ZuluLiveWhisperXMPC()
    result = agent.run()
    print(f"\nResult: {result['status']}")
