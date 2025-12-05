"""Call summarization using local LLM (Ollama)."""

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_core.inference.diarization import DiarizedSegment
from agent_core.llm.ollama_client import OllamaClient
from agent_core.utils import LoggerMixin

# === ZULU Summarizer Config ===
MAX_SEGMENTS_PER_CHUNK = 40         # how many transcript segments per mini-summary
MAX_CHUNK_SUMMARIES_PER_PASS = 25   # safety limit for 2nd-pass merges
LLM_MAX_RETRIES = 2                 # retry LLM on malformed JSON


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
    
    def summarize_call(self, segments: List[DiarizedSegment], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Public entrypoint: summarize an entire call.
        Chooses hierarchical strategy automatically for long calls.
        """
        num_segments = len(segments)
        self.logger.info(f"Summarizing call with {num_segments} segments")
        
        if num_segments == 0:
            self.logger.warning("No segments to summarize.")
            return {
                "summary": "No audio content detected.",
                "key_points": [],
                "action_items": [],
                "sentiment": "neutral",
            }
        
        # For short calls, just one-pass summarization
        if num_segments <= MAX_SEGMENTS_PER_CHUNK:
            print(f"[*] Short recording: using single-pass summarization")
            result = self._summarize_chunk(segments)
        else:
            # For longer calls, use hierarchical summarization
            print(f"[!] Long recording detected ({num_segments} turns)")
            print(f"[*] Using hierarchical summarization (chunks of {MAX_SEGMENTS_PER_CHUNK})")
            result = self._summarize_hierarchical(segments)
        
        return result
    
    def _chunk_segments(self, segments, max_per_chunk=MAX_SEGMENTS_PER_CHUNK):
        """Yield chunks of segments for hierarchical summarization."""
        for i in range(0, len(segments), max_per_chunk):
            yield segments[i:i + max_per_chunk]
    
    def _format_segments_for_prompt(self, segments):
        """
        Turn segments into a compact text block for the LLM.
        Segments can be DiarizedSegment objects or dicts.
        """
        lines = []
        for seg in segments:
            # Handle both DiarizedSegment objects and dict summaries
            if isinstance(seg, dict):
                speaker = seg.get("speaker", "SPEAKER_00")
                text = seg.get("text", "").strip()
            else:
                speaker = getattr(seg, 'speaker', 'SPEAKER_00')
                text = getattr(seg, 'text', '').strip()
            
            if not text:
                continue
            lines.append(f"{speaker}: {text}")
        return "\n".join(lines)
    
    def _build_summary_prompt(self, segments, is_meta=False):
        """
        Build an instruction prompt:
        - if is_meta=False → summarize raw transcript segments
        - if is_meta=True  → summarize summaries of chunks
        """
        transcript_block = self._format_segments_for_prompt(segments)
        
        if not is_meta:
            task_instructions = (
                "You are ZULU, a privacy-first meeting assistant. Summarize the following conversation.\n"
                "- Focus on key decisions, action items, and topics.\n"
                "- Return STRICT JSON with keys: summary, key_points, action_items, sentiment.\n"
                "- Do NOT include any extra text outside the JSON.\n\n"
            )
        else:
            task_instructions = (
                "You are ZULU, a privacy-first meeting assistant. You are given summaries of several parts of a "
                "long conversation. Merge them into a single final summary.\n"
                "- Combine overlapping points.\n"
                "- Keep it concise but complete.\n"
                "- Return STRICT JSON with keys: summary, key_points, action_items, sentiment.\n"
                "- Do NOT include any extra text outside the JSON.\n\n"
            )
        
        prompt = task_instructions + "CONTENT:\n" + transcript_block
        return prompt
    
    def _call_llm(self, prompt):
        """
        Call the local LLM via Ollama client and return the raw text.
        """
        response = self.client.generate(prompt=prompt, temperature=0.1)
        
        # normalize as string
        if isinstance(response, dict):
            text = response.get("response") or response.get("text") or ""
        else:
            text = str(response)
        
        return text.strip()
    
    def _parse_summary_json(self, text):
        """
        Parse the LLM reply as JSON and validate required keys.
        Raises ValueError on failure.
        """
        # Use safe_json_extract for robustness
        data = safe_json_extract(text)
        
        if not data:
            raise ValueError("Failed to extract JSON from LLM response")
        
        # basic structure check
        required_keys = ["summary"]
        if not isinstance(data, dict):
            raise ValueError("LLM output is not a JSON object")
        
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise ValueError(f"LLM JSON missing keys: {missing}")
        
        return data
    
    def _summarize_chunk(self, segments, attempt=0):
        """
        Summarize a single chunk of segments.
        Returns a dict with summary, key_points, action_items, sentiment.
        """
        prompt = self._build_summary_prompt(segments, is_meta=False)
        
        start_time = time.time()
        raw = self._call_llm(prompt)
        elapsed = time.time() - start_time
        
        print(f"  -> LLM responded in {elapsed:.1f}s")
        
        try:
            parsed = self._parse_summary_json(raw)
            # Ensure all expected keys exist
            return {
                "summary": parsed.get("summary", ""),
                "key_points": parsed.get("key_points", []),
                "action_items": parsed.get("action_items", []),
                "decisions": parsed.get("decisions", []),
                "risks": parsed.get("risks", []),
                "topics": parsed.get("topics", []),
                "sentiment": parsed.get("sentiment", "neutral"),
            }
        except ValueError as e:
            self.logger.warning(
                f"⚠️  Chunk summary parse failed on attempt {attempt + 1}: {e}"
            )
            if attempt + 1 >= LLM_MAX_RETRIES:
                # last resort: return a minimal structure
                return {
                    "summary": "Summary unavailable for this chunk.",
                    "key_points": [],
                    "action_items": [],
                    "decisions": [],
                    "risks": [],
                    "topics": [],
                    "sentiment": "neutral",
                }
            # retry with a shorter prompt version
            shorter_segments = segments[: max(1, len(segments) // 2)]
            return self._summarize_chunk(shorter_segments, attempt=attempt + 1)
    
    def _summarize_hierarchical(self, segments):
        """
        Hierarchical summarization:
        - Split raw segments into chunks
        - Summarize each chunk independently
        - Merge the chunk-level summaries into a final summary
        """
        # 1) First-level: summarize each chunk
        chunk_summaries = []
        chunks_list = list(self._chunk_segments(segments))
        
        print(f"  -> Split into {len(chunks_list)} chunks of ~{MAX_SEGMENTS_PER_CHUNK} turns each")
        
        for idx, chunk in enumerate(chunks_list, 1):
            print(f"  -> Summarizing chunk {idx}/{len(chunks_list)}...")
            chunk_result = self._summarize_chunk(chunk)
            
            # turn that into a pseudo-segment so we can reuse _build_summary_prompt
            chunk_summaries.append({
                "speaker": "SUMMARY",
                "text": chunk_result.get("summary", ""),
                "start": 0.0,
                "end": 0.0,
            })
            
            # safety cap to prevent infinite growth
            if len(chunk_summaries) >= MAX_CHUNK_SUMMARIES_PER_PASS:
                break
        
        # If there's only one chunk, we're done
        if len(chunk_summaries) == 1:
            return self._summarize_chunk(segments)
        
        # 2) Second-level: merge all chunk summaries
        print(f"  -> Merging {len(chunk_summaries)} chunk summaries into final summary...")
        prompt = self._build_summary_prompt(chunk_summaries, is_meta=True)
        
        start_time = time.time()
        raw = self._call_llm(prompt)
        elapsed = time.time() - start_time
        
        print(f"  -> Final summary generated in {elapsed:.1f}s")
        
        try:
            parsed = self._parse_summary_json(raw)
            result = {
                "summary": parsed.get("summary", ""),
                "key_points": parsed.get("key_points", []),
                "action_items": parsed.get("action_items", []),
                "decisions": parsed.get("decisions", []),
                "risks": parsed.get("risks", []),
                "topics": parsed.get("topics", []),
                "sentiment": parsed.get("sentiment", "neutral"),
                "note": f"Hierarchical summary: {len(chunks_list)} chunks, {len(segments)} total turns",
            }
            self.logger.info("✅ Hierarchical summary completed successfully")
            return result
        except ValueError as e:
            self.logger.warning(
                f"⚠️  Final hierarchical summary parse failed: {e}. "
                f"Falling back to concatenated chunk summaries."
            )
            # Very safe fallback: stitch chunk summaries into one object
            merged_summary_text = "\n\n".join(
                [s["text"] for s in chunk_summaries if s.get("text")]
            )
            return {
                "summary": merged_summary_text or "Summary unavailable.",
                "key_points": [],
                "action_items": [],
                "decisions": [],
                "risks": [],
                "topics": [],
                "sentiment": "neutral",
                "note": f"Partial hierarchical summary: {len(chunks_list)} chunks processed",
            }
    
    def _format_utterances(self, segments: List[DiarizedSegment]) -> str:
        """Format segments as text for prompt."""
        lines = []
        for seg in segments:
            lines.append(
                f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.speaker}: {seg.text}"
            )
        return "\n".join(lines)
    
    def _create_fallback_summary(self, segments: List[DiarizedSegment], original_count: Optional[int] = None) -> Dict[str, Any]:
        """Create a basic fallback summary if LLM fails."""
        total_time = segments[-1].end if segments else 0
        speakers = list(set(seg.speaker for seg in segments))
        
        # Use original count if provided (for sampled recordings)
        turn_count = original_count if original_count else len(segments)
        
        # Extract first few sentences as key points
        key_points = []
        for seg in segments[:3]:  # First 3 turns
            text = seg.text[:100]  # Truncate long texts
            if text:
                key_points.append(f"{seg.speaker}: {text}")
        
        return {
            "summary": f"Recorded conversation with {len(speakers)} speaker(s), "
                      f"{turn_count} turns, duration {total_time:.1f}s. "
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
