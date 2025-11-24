"""Call summarization using local LLM (Ollama)."""

import json
from pathlib import Path
from typing import Any, Dict, List

from agent_core.inference.diarization import DiarizedSegment
from agent_core.llm.ollama_client import OllamaClient
from agent_core.utils import LoggerMixin


class CallSummarizer(LoggerMixin):
    """
    Summarize call transcripts using local Ollama LLM.
    """
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        prompt_template_path: Optional[str] = None,
    ):
        """
        Initialize call summarizer.
        
        Args:
            ollama_client: Configured Ollama client.
            prompt_template_path: Path to prompt template file.
        """
        self.client = ollama_client
        
        # Load prompt template
        if prompt_template_path is None:
            prompt_template_path = (
                Path(__file__).parent.parent / "prompts" / "call_summarizer.md"
            )
        
        self.prompt_template = self._load_prompt_template(prompt_template_path)
        self.logger.info("CallSummarizer initialized")
    
    def _load_prompt_template(self, path: str) -> str:
        """Load prompt template from file."""
        try:
            with open(path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.warning(f"Prompt template not found: {path}, using default")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Get default prompt template."""
        return """You are ZULU, a private local-first AI agent that analyzes call transcripts.

You receive a list of utterances from a call with fields:
- speaker: Speaker label (e.g., SPK_1, SPK_2)
- start_time: Start timestamp in seconds
- end_time: End timestamp in seconds
- text: What was said

Your goals:
1. Provide a concise summary of the call (2-3 paragraphs max)
2. Extract decisions, action items, and deadlines
3. Identify any risks or concerns mentioned
4. Keep privacy: do NOT infer or guess real names, companies, or identities
5. Output ONLY valid JSON with no additional text

Output format (JSON only, no markdown):
{
  "summary": "Brief summary of the call discussion",
  "key_points": ["Point 1", "Point 2", "Point 3"],
  "action_items": [
    {
      "owner": "SPK_1",
      "item": "Task description",
      "due": "2024-01-15 or null"
    }
  ],
  "decisions": [
    "Decision 1",
    "Decision 2"
  ],
  "risks": [
    "Risk 1",
    "Risk 2"
  ],
  "topics": ["topic1", "topic2"],
  "sentiment": "positive|neutral|negative"
}

Utterances:
{utterances}

Remember: Output ONLY the JSON object, nothing else."""
    
    def summarize_call(
        self,
        segments: List[DiarizedSegment],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Summarize a call from diarized segments.
        
        Args:
            segments: List of diarized segments.
            metadata: Optional call metadata.
            
        Returns:
            Summary dict with structured information.
        """
        self.logger.info(f"Summarizing call with {len(segments)} segments")
        
        # Format utterances for prompt
        utterances_text = self._format_utterances(segments)
        
        # Build prompt
        prompt = self.prompt_template.format(utterances=utterances_text)
        
        # Generate summary
        try:
            response = self.client.generate_json(
                prompt=prompt,
                temperature=0.1,
            )
            
            self.logger.info("Call summary generated successfully")
            return response
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse summary JSON: {e}")
            # Return basic fallback summary
            return self._create_fallback_summary(segments)
        except Exception as e:
            self.logger.error(f"Summarization failed: {e}")
            return self._create_fallback_summary(segments)
    
    def _format_utterances(self, segments: List[DiarizedSegment]) -> str:
        """Format segments as text for prompt."""
        lines = []
        for seg in segments:
            lines.append(
                f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.speaker}: {seg.text}"
            )
        return "\n".join(lines)
    
    def _create_fallback_summary(self, segments: List[DiarizedSegment]) -> Dict[str, Any]:
        """Create a basic fallback summary if LLM fails."""
        total_time = segments[-1].end if segments else 0
        speakers = list(set(seg.speaker for seg in segments))
        
        return {
            "summary": f"Call with {len(speakers)} speakers, duration {total_time:.1f}s. "
                      f"Automatic summarization unavailable.",
            "key_points": [],
            "action_items": [],
            "decisions": [],
            "risks": [],
            "topics": [],
            "sentiment": "neutral",
            "error": "LLM summarization failed",
        }


def summarize_call(
    segments: List[DiarizedSegment],
    ollama_client: Optional[OllamaClient] = None,
) -> Dict[str, Any]:
    """
    Convenience function to summarize a call.
    
    Args:
        segments: Diarized segments.
        ollama_client: Optional pre-configured client.
        
    Returns:
        Summary dict.
    """
    if ollama_client is None:
        ollama_client = OllamaClient()
    
    summarizer = CallSummarizer(ollama_client)
    return summarizer.summarize_call(segments)
