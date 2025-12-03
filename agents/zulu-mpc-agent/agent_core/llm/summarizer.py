"""Call summarization using local LLM (Ollama)."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_core.inference.diarization import DiarizedSegment
from agent_core.llm.ollama_client import OllamaClient
from agent_core.utils import LoggerMixin


def safe_json_extract(text: str) -> Optional[dict]:
    """
    Extracts JSON objects from messy LLM output.
    Attempts multiple cleaning heuristics before giving up.
    
    Args:
        text: Raw LLM response text
        
    Returns:
        Parsed JSON dict or None if extraction fails
    """
    if not text:
        return None
    
    # 1. Extract the JSON substring (greedy)
    json_candidates = re.findall(r"\{.*\}", text, re.DOTALL)
    
    # If no complete JSON found, try to find partial and wrap it
    if not json_candidates:
        # Look for JSON-like content starting with keys
        if '"summary"' in text or "'summary'" in text:
            # Try to extract from first quote to end
            start_idx = text.find('"summary"')
            if start_idx == -1:
                start_idx = text.find("'summary'")
            if start_idx != -1:
                # Wrap it in braces
                raw = "{" + text[start_idx:] + "}"
            else:
                return None
        else:
            return None
    else:
        raw = json_candidates[0]

    # 2. Cleanup: remove backticks & markdown artifacts
    cleaned = (
        raw.replace("```json", "")
           .replace("```", "")
           .strip()
    )

    # 3. Fix common LLM formatting mistakes
    fixes = [
        (r",\s*}", "}"),         # trailing commas
        (r",\s*]", "]"),         # trailing commas in arrays
        (r'["""]', '"'),         # smart quotes (using character class)
    ]
    for pattern, repl in fixes:
        cleaned = re.sub(pattern, repl, cleaned)
    
    # Replace single quotes with double quotes (but be careful with contractions)
    # Only replace single quotes that are not part of words
    cleaned = re.sub(r"(?<!\w)'|'(?!\w)", '"', cleaned)

    # 4. Try parse directly
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 5. Try with newlines removed
    try:
        no_newlines = cleaned.replace("\n", " ").replace("\r", " ")
        return json.loads(no_newlines)
    except Exception:
        pass

    # 6. Try adding missing brackets
    try:
        return json.loads(cleaned + "}")
    except Exception:
        pass
    
    # 7. Try adding missing opening bracket
    try:
        return json.loads("{" + cleaned)
    except Exception:
        pass
    
    # 8. Try fixing multiline strings
    try:
        # Replace literal newlines inside strings with \n
        fixed = re.sub(r':\s*"([^"]*?)\n([^"]*?)"', r': "\1 \2"', cleaned, flags=re.DOTALL)
        return json.loads(fixed)
    except Exception:
        pass

    return None


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
        # Using PLACEHOLDER for utterances, will replace manually to avoid .format() issues with JSON
        return """You are ZULU, a privacy-first AI that analyzes call transcripts.

TRANSCRIPT:
UTTERANCES_PLACEHOLDER

INSTRUCTIONS:
Analyze the transcript and output a JSON summary. Focus on:
- Main discussion topics and outcomes
- Action items and decisions
- Any concerns or risks mentioned
- Overall sentiment

PRIVACY: Use only speaker labels (SPEAKER_00, etc). Do NOT guess real names or companies.

OUTPUT FORMAT - Return ONLY valid JSON. Start with { and end with }. No extra text before or after.
{
  "summary": "2-3 sentence summary of the call",
  "key_points": ["point 1", "point 2", "point 3"],
  "action_items": [
    {"owner": "SPEAKER_00", "item": "task description", "due": null}
  ],
  "decisions": ["decision 1", "decision 2"],
  "risks": ["risk 1 if any"],
  "topics": ["topic1", "topic2"],
  "sentiment": "positive"
}

CRITICAL RULES:
1. Output must START with { and END with }
2. No markdown formatting (no ```json or ```)
3. No explanatory text before or after the JSON
4. Use double quotes for all strings
5. Ensure all JSON is valid and complete"""
    
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
        
        # Build prompt (using replace to avoid .format() issues with JSON braces)
        prompt = self.prompt_template.replace("UTTERANCES_PLACEHOLDER", utterances_text)
        # Fallback for old format-style templates
        if "UTTERANCES_PLACEHOLDER" not in self.prompt_template:
            prompt = self.prompt_template.replace("{utterances}", utterances_text)
        
        # Generate summary with bulletproof JSON parsing
        try:
            # Generate response (not using format="json" due to Ollama issues)
            print("  -> Waiting for LLM (this may take 10-30 seconds)...")
            import time
            start_time = time.time()
            
            llm_response = self.client.generate(
                prompt=prompt,
                temperature=0.1,
            )
            
            elapsed = time.time() - start_time
            print(f"  -> LLM responded in {elapsed:.1f}s")
            
            # DEBUG: Show what we got
            print(f"\n[DEBUG] LLM Response ({len(llm_response)} chars):")
            print(f"{llm_response[:300]}")
            print()
            
            # Use our enhanced JSON extractor
            parsed = safe_json_extract(llm_response)
            
            if not parsed:
                print(f"[!] Failed to extract JSON from LLM response")
                print(f"[DEBUG] Full response:\n{llm_response}\n")
                return self._create_fallback_summary(segments)
            
            if parsed and "summary" in parsed:
                self.logger.info("✅ Call summary parsed successfully")
                # Normalize keys (handle variations)
                return {
                    "summary": parsed.get("summary") or parsed.get("Summary", ""),
                    "key_points": parsed.get("key_points") or parsed.get("KeyPoints", []),
                    "action_items": parsed.get("action_items") or parsed.get("Actions", []),
                    "decisions": parsed.get("decisions", []),
                    "risks": parsed.get("risks", []),
                    "topics": parsed.get("topics", []),
                    "sentiment": parsed.get("sentiment", "neutral"),
                }
            else:
                self.logger.warning("⚠️  LLM response didn't contain valid summary JSON")
                if parsed:
                    self.logger.warning(f"Parsed dict keys: {list(parsed.keys())}")
                return self._create_fallback_summary(segments)
            
        except Exception as e:
            self.logger.error(f"❌ Summarization failed: {e}")
            self.logger.error(f"💡 Is Ollama running? Check: http://localhost:11434")
            import traceback
            self.logger.debug(f"Full traceback: {traceback.format_exc()}")
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
        
        # Extract first few sentences as key points
        key_points = []
        for seg in segments[:3]:  # First 3 turns
            text = seg.text[:100]  # Truncate long texts
            if text:
                key_points.append(f"{seg.speaker}: {text}")
        
        return {
            "summary": f"Recorded conversation with {len(speakers)} speaker(s), "
                      f"{len(segments)} turns, duration {total_time:.1f}s. "
                      f"Full transcript available in encrypted database.",
            "key_points": key_points,
            "action_items": [],
            "decisions": [],
            "risks": [],
            "topics": ["conversation"],
            "sentiment": "neutral",
            "note": "AI summarization unavailable - using basic transcript summary",
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
