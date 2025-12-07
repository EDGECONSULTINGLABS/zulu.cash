"""
summarizer_v2.py

Optimized summarization for Zulu:
- Small, fast model for chunk summaries
- Larger model for final synthesis
- Chunked + hierarchical summarization
- Real-time caching ("Otter-style")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol, Optional, Dict, Any
import uuid
import datetime


# ============================================================
# Interfaces / Protocols
# ============================================================

class LLMClient(Protocol):
    """
    Abstract LLM client.

    You can back this with:
      - Ollama
      - llama.cpp
      - OpenAI-compatible API
      - Local inference server
    """

    def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> str:
        ...


class SummaryStore(Protocol):
    """
    Abstract store for summaries (e.g., SQLCipher-backed DB).

    Implement with your encrypted vault layer.
    """

    def put_chunk_summary(
        self,
        conversation_id: str,
        chunk_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        ...

    def get_chunk_summaries(
        self,
        conversation_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Should return list of dicts with at least:
        {
            "chunk_id": str,
            "content": str,
            "created_at": datetime or str
        }
        """
        ...

    def clear_conversation(
        self,
        conversation_id: str,
    ) -> None:
        ...

    def put_final_summary(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        ...


# ============================================================
# Config
# ============================================================

@dataclass
class SummarizerConfig:
    """
    Config knobs for Zulu summarization.
    """

    # Model routing
    chunk_model: str = "qwen2.5:1.5b"        # fast, small, good enough
    synthesis_model: str = "llama3.1:8b"       # larger, higher quality

    # Chunking
    max_chunk_chars: int = 2000              # ~300–400 tokens by rough estimate

    # Prompts
    chunk_prompt: str = (
        "Summarize the following text in 3–6 concise bullet points.\n"
        "- Focus on key actions, decisions, and facts.\n"
        "- Omit filler, repetitions, and greetings.\n"
        "- Use plain language.\n\n"
        "TEXT:\n"
    )

    synthesis_prompt: str = (
        "You are an executive assistant.\n"
        "You will receive multiple short summaries from one meeting.\n\n"
        "Combine them into a single, cohesive summary with:\n"
        "- A short overview (2–3 sentences)\n"
        "- 3–7 bullet points for key decisions, actions, and blockers\n"
        "- Clear, neutral tone\n\n"
        "Chunk summaries:\n"
    )

    # Generation settings
    chunk_max_tokens: int = 256
    synthesis_max_tokens: int = 512
    temperature: float = 0.1


# ============================================================
# Core Summarizer
# ============================================================

class ZuluSummarizer:
    """
    Optimized summarizer for Zulu.

    - Live: call `summarize_live_chunk(...)` repeatedly as audio is processed.
    - Post-call: call `generate_final_summary(...)` once.

    All storage is handled via SummaryStore (e.g. SQLCipher).
    """

    def __init__(
        self,
        llm_client: LLMClient,
        store: SummaryStore,
        config: Optional[SummarizerConfig] = None,
    ):
        self.llm = llm_client
        self.store = store
        self.config = config or SummarizerConfig()

    # --------------------------------------------------------
    # Chunking Helpers
    # --------------------------------------------------------

    def chunk_text(self, text: str) -> List[str]:
        """
        Simple char-based chunking.

        In production you might want token-based chunking using tiktoken
        or whatever your tokenizer is. But this is safe as a starting point.
        """
        text = text.strip()
        if not text:
            return []

        max_len = self.config.max_chunk_chars
        return [text[i : i + max_len] for i in range(0, len(text), max_len)]

    # --------------------------------------------------------
    # Live / Real-time Chunk Summarization
    # --------------------------------------------------------

    def summarize_live_chunk(
        self,
        conversation_id: str,
        raw_text: str,
        speaker_label: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> str:
        """
        Called during the call / meeting as WhisperX generates text.

        You can call this with:
        - a rolling buffer, or
        - fully pre-chunked segments.

        Returns the chunk summary so the UI can display it immediately.
        """

        raw_text = raw_text.strip()
        if not raw_text:
            return ""

        prompt = self.config.chunk_prompt + raw_text

        summary = self.llm.generate(
            model=self.config.chunk_model,
            prompt=prompt,
            max_tokens=self.config.chunk_max_tokens,
            temperature=self.config.temperature,
        )

        chunk_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat()

        metadata: Dict[str, Any] = {
            "speaker_label": speaker_label,
            "start_time": start_time,
            "end_time": end_time,
            "created_at": now,
            "model": self.config.chunk_model,
        }

        self.store.put_chunk_summary(
            conversation_id=conversation_id,
            chunk_id=chunk_id,
            content=summary,
            metadata=metadata,
        )

        return summary

    # --------------------------------------------------------
    # Batch / Offline Summarization (e.g., entire transcript string)
    # --------------------------------------------------------

    def summarize_full_transcript(
        self,
        conversation_id: str,
        transcript_text: str,
    ) -> None:
        """
        Optional helper: you already have a full transcript and want to:
        - chunk it,
        - summarize each chunk,
        - cache chunk summaries for the final synthesis.

        This can be used when no live mode is active.
        """
        chunks = self.chunk_text(transcript_text)

        for chunk in chunks:
            self.summarize_live_chunk(
                conversation_id=conversation_id,
                raw_text=chunk,
                speaker_label=None,
                start_time=None,
                end_time=None,
            )

    # --------------------------------------------------------
    # Final Synthesis Summary
    # --------------------------------------------------------

    def generate_final_summary(
        self,
        conversation_id: str,
        clear_cache: bool = True,
    ) -> str:
        """
        Run *once* after a call / meeting finishes.

        - Fetches all chunk summaries for the conversation
        - Feeds them into a larger synthesis model
        - Stores + returns the final summary
        """

        chunk_records = self.store.get_chunk_summaries(conversation_id)

        if not chunk_records:
            final_summary = "No chunk summaries available for this conversation."
            self.store.put_final_summary(
                conversation_id=conversation_id,
                content=final_summary,
                metadata={"error": "no_chunks"},
            )
            return final_summary

        # Sort by creation time if available
        try:
            chunk_records = sorted(
                chunk_records,
                key=lambda r: r.get("created_at", ""),
            )
        except Exception:
            # If sorting fails, just keep original order
            pass

        chunks_text = "\n\n---\n\n".join(
            r.get("content", "") for r in chunk_records if r.get("content")
        )

        prompt = self.config.synthesis_prompt + chunks_text

        final_summary = self.llm.generate(
            model=self.config.synthesis_model,
            prompt=prompt,
            max_tokens=self.config.synthesis_max_tokens,
            temperature=self.config.temperature,
        )

        metadata: Dict[str, Any] = {
            "chunk_count": len(chunk_records),
            "created_at": datetime.datetime.utcnow().isoformat(),
            "model": self.config.synthesis_model,
        }

        self.store.put_final_summary(
            conversation_id=conversation_id,
            content=final_summary,
            metadata=metadata,
        )

        if clear_cache:
            self.store.clear_conversation(conversation_id)

        return final_summary
