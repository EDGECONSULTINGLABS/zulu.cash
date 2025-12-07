# Summarizer v2 Integration Guide

**Step-by-step instructions for integrating the optimized summarization system into ZULU.**

---

## Prerequisites

### 1. Install Required Models

```bash
# Small model for chunk summaries (1.5B params)
ollama pull qwen2.5:1.5b

# Verify large model for synthesis (8B params - already installed)
ollama list | grep llama3.1:8b
```

### 2. Update Database Schema

Add tables for chunk summaries and final summaries.

**Create migration:** `agent_core/memory/migrations/004_summarizer_v2.sql`

```sql
-- Chunk summaries (live, during call)
CREATE TABLE IF NOT EXISTS chunk_summaries (
    chunk_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    content TEXT NOT NULL,
    speaker_label TEXT,
    start_time REAL,
    end_time REAL,
    model TEXT,
    created_at TEXT NOT NULL,
    metadata_json TEXT,
    FOREIGN KEY (conversation_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_chunk_summaries_conversation 
ON chunk_summaries(conversation_id);

CREATE INDEX IF NOT EXISTS idx_chunk_summaries_created 
ON chunk_summaries(created_at);

-- Final summaries (post-call)
CREATE TABLE IF NOT EXISTS final_summaries (
    conversation_id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    chunk_count INTEGER,
    model TEXT,
    created_at TEXT NOT NULL,
    metadata_json TEXT,
    FOREIGN KEY (conversation_id) REFERENCES sessions(id)
);
```

---

## Step 1: Implement SummaryStore Adapter

**File:** `agent_core/memory/summary_store_adapter.py`

This adapter makes `SessionStore` compatible with the `SummaryStore` protocol.

```python
"""
Adapter to make SessionStore compatible with SummaryStore protocol.
"""

from typing import List, Dict, Any, Optional
import json
from agent_core.memory.session_store import SessionStore


class SummaryStoreAdapter:
    """
    Wraps SessionStore to implement SummaryStore protocol.
    """
    
    def __init__(self, session_store: SessionStore):
        self.store = session_store
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure chunk_summaries and final_summaries tables exist."""
        conn = self.store._get_connection()
        try:
            # Check if tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_summaries'"
            )
            if not cursor.fetchone():
                # Run migration
                self._create_tables(conn)
        finally:
            conn.close()
    
    def _create_tables(self, conn):
        """Create summarizer v2 tables."""
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chunk_summaries (
                chunk_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                content TEXT NOT NULL,
                speaker_label TEXT,
                start_time REAL,
                end_time REAL,
                model TEXT,
                created_at TEXT NOT NULL,
                metadata_json TEXT
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_chunk_summaries_conversation 
            ON chunk_summaries(conversation_id)
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS final_summaries (
                conversation_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                chunk_count INTEGER,
                model TEXT,
                created_at TEXT NOT NULL,
                metadata_json TEXT
            )
        ''')
        
        conn.commit()
    
    # ========== SummaryStore Protocol Implementation ==========
    
    def put_chunk_summary(
        self,
        conversation_id: str,
        chunk_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store a chunk summary."""
        conn = self.store._get_connection()
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            conn.execute(
                '''
                INSERT INTO chunk_summaries 
                (chunk_id, conversation_id, content, speaker_label, start_time, end_time, model, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    chunk_id,
                    conversation_id,
                    content,
                    metadata.get('speaker_label') if metadata else None,
                    metadata.get('start_time') if metadata else None,
                    metadata.get('end_time') if metadata else None,
                    metadata.get('model') if metadata else None,
                    metadata.get('created_at') if metadata else None,
                    metadata_json,
                )
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_chunk_summaries(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all chunk summaries for a conversation."""
        conn = self.store._get_connection()
        try:
            cursor = conn.execute(
                '''
                SELECT chunk_id, content, speaker_label, start_time, end_time, model, created_at, metadata_json
                FROM chunk_summaries
                WHERE conversation_id = ?
                ORDER BY created_at
                ''',
                (conversation_id,)
            )
            
            summaries = []
            for row in cursor.fetchall():
                summary = {
                    'chunk_id': row[0],
                    'content': row[1],
                    'speaker_label': row[2],
                    'start_time': row[3],
                    'end_time': row[4],
                    'model': row[5],
                    'created_at': row[6],
                }
                if row[7]:  # metadata_json
                    summary['metadata'] = json.loads(row[7])
                summaries.append(summary)
            
            return summaries
        finally:
            conn.close()
    
    def clear_conversation(self, conversation_id: str) -> None:
        """Clear all chunk summaries for a conversation."""
        conn = self.store._get_connection()
        try:
            conn.execute(
                'DELETE FROM chunk_summaries WHERE conversation_id = ?',
                (conversation_id,)
            )
            conn.commit()
        finally:
            conn.close()
    
    def put_final_summary(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store final summary."""
        conn = self.store._get_connection()
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            conn.execute(
                '''
                INSERT OR REPLACE INTO final_summaries 
                (conversation_id, content, chunk_count, model, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    conversation_id,
                    content,
                    metadata.get('chunk_count') if metadata else None,
                    metadata.get('model') if metadata else None,
                    metadata.get('created_at') if metadata else None,
                    metadata_json,
                )
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_final_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get final summary for a conversation."""
        conn = self.store._get_connection()
        try:
            cursor = conn.execute(
                '''
                SELECT content, chunk_count, model, created_at, metadata_json
                FROM final_summaries
                WHERE conversation_id = ?
                ''',
                (conversation_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
            
            summary = {
                'conversation_id': conversation_id,
                'content': row[0],
                'chunk_count': row[1],
                'model': row[2],
                'created_at': row[3],
            }
            if row[4]:  # metadata_json
                summary['metadata'] = json.loads(row[4])
            
            return summary
        finally:
            conn.close()
```

---

## Step 2: Create LLMClient Wrapper

**File:** `agent_core/llm/ollama_llm_client.py`

Wrap the existing OllamaClient to match the LLMClient protocol.

```python
"""
Wrapper for OllamaClient to match LLMClient protocol.
"""

from agent_core.llm.ollama_client import OllamaClient as BaseOllamaClient


class OllamaLLMClient:
    """
    Adapter to make OllamaClient compatible with LLMClient protocol.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 120):
        self.client = BaseOllamaClient(base_url=base_url, timeout=timeout)
    
    def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> str:
        """
        Generate text using Ollama.
        
        Maps to OllamaClient.generate() method.
        """
        response = self.client.generate(
            model=model,
            prompt=prompt,
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 40,
            }
        )
        
        return response.get("response", "")
```

---

## Step 3: Update Live Agent

**File:** `live_whisperx_agent.py`

Add incremental chunk summarization during the call.

### Additions to `__init__`:

```python
from agent_core.llm.summarizer_v2 import ZuluSummarizer, SummarizerConfig
from agent_core.llm.ollama_llm_client import OllamaLLMClient
from agent_core.memory.summary_store_adapter import SummaryStoreAdapter

class LiveWhisperXAgent:
    def __init__(self, ...):
        # Existing code...
        
        # Initialize v2 summarizer
        llm_client = OllamaLLMClient()
        summary_store = SummaryStoreAdapter(self.session_store)
        config = SummarizerConfig(
            chunk_model="qwen2.5:1.5b",
            synthesis_model="llama3.1:8b",
            max_chunk_chars=2000,
        )
        self.summarizer_v2 = ZuluSummarizer(llm_client, summary_store, config)
        
        # Buffer for live chunking
        self.summary_buffer = []
        self.last_summary_time = time.time()
```

### Add chunk summarization during processing:

```python
def run(self, ...):
    # ... existing code for transcription ...
    
    # After storing turns, add live chunk summarization
    for turn in turns:
        self.summary_buffer.append(turn.text)
        
        # Summarize every 30 seconds or 2000 chars
        now = time.time()
        buffer_text = " ".join(self.summary_buffer)
        
        if (now - self.last_summary_time > 30) or (len(buffer_text) > 2000):
            self._generate_live_chunk_summary(session_id, buffer_text)
            self.summary_buffer = []
            self.last_summary_time = now

def _generate_live_chunk_summary(self, session_id: str, text: str):
    """Generate and display live chunk summary."""
    if not text.strip():
        return
    
    try:
        chunk_summary = self.summarizer_v2.summarize_live_chunk(
            conversation_id=session_id,
            raw_text=text,
        )
        
        # Display to user
        print(f"\n[LIVE SUMMARY] {chunk_summary}\n")
        
    except Exception as e:
        print(f"[!] Live summary failed: {e}")
```

### Update final summary generation:

```python
# Replace existing summarizer call with:

try:
    # Flush any remaining buffer
    if self.summary_buffer:
        buffer_text = " ".join(self.summary_buffer)
        self._generate_live_chunk_summary(session_id, buffer_text)
    
    # Generate final synthesis
    print("\n[*] Generating final executive summary...")
    final_summary_text = self.summarizer_v2.generate_final_summary(
        conversation_id=session_id,
        clear_cache=False,  # Keep chunks for debugging
    )
    
    print(f"\n[OK] ✅ Final summary generated\n")
    print("="*60)
    print("[*] EXECUTIVE SUMMARY")
    print("="*60)
    print(final_summary_text)
    print("="*60 + "\n")
    
except Exception as e:
    print(f"[!] Summary generation failed: {e}")
    # Fallback to basic summary
    final_summary_text = "Summary generation failed. See logs."
```

---

## Step 4: Add CLI Commands

**File:** `cli.py`

Add commands to inspect summaries.

```python
@cli.command()
@click.argument('session_id')
def show_chunks(session_id: str):
    """Show all chunk summaries for a session."""
    from agent_core.memory.summary_store_adapter import SummaryStoreAdapter
    from agent_core.memory.session_store import SessionStore
    
    store = SessionStore()
    adapter = SummaryStoreAdapter(store)
    
    chunks = adapter.get_chunk_summaries(session_id)
    
    if not chunks:
        console.print("[yellow]No chunk summaries found.[/yellow]")
        return
    
    console.print(f"\n[bold]Chunk Summaries for {session_id[:8]}...[/bold]\n")
    
    for i, chunk in enumerate(chunks, 1):
        console.print(f"[cyan]Chunk {i}[/cyan] ({chunk.get('model', 'unknown')})")
        console.print(f"  {chunk['content']}\n")


@cli.command()
@click.argument('session_id')
def show_final(session_id: str):
    """Show final summary for a session."""
    from agent_core.memory.summary_store_adapter import SummaryStoreAdapter
    from agent_core.memory.session_store import SessionStore
    
    store = SessionStore()
    adapter = SummaryStoreAdapter(store)
    
    summary = adapter.get_final_summary(session_id)
    
    if not summary:
        console.print("[yellow]No final summary found.[/yellow]")
        return
    
    console.print(f"\n[bold]Final Summary[/bold]\n")
    console.print(summary['content'])
    console.print(f"\n[dim]Model: {summary.get('model')} | Chunks: {summary.get('chunk_count')}[/dim]\n")


@cli.command()
@click.argument('session_id')
def regenerate_summary(session_id: str):
    """Regenerate final summary from existing chunks."""
    from agent_core.llm.summarizer_v2 import ZuluSummarizer, SummarizerConfig
    from agent_core.llm.ollama_llm_client import OllamaLLMClient
    from agent_core.memory.summary_store_adapter import SummaryStoreAdapter
    from agent_core.memory.session_store import SessionStore
    
    llm_client = OllamaLLMClient()
    store = SessionStore()
    adapter = SummaryStoreAdapter(store)
    
    summarizer = ZuluSummarizer(llm_client, adapter, SummarizerConfig())
    
    console.print("[*] Regenerating final summary...")
    final = summarizer.generate_final_summary(session_id, clear_cache=False)
    console.print(f"\n[OK] ✅ Summary regenerated\n")
    console.print(final)
```

---

## Step 5: Test

### Test 1: Live Recording

```bash
python cli.py live-whisperx --model-size medium
# Record for 2+ minutes
# Watch for [LIVE SUMMARY] outputs during recording
# Press Ctrl+C
# Verify final executive summary appears
```

### Test 2: Inspect Chunks

```bash
# Get session ID from output
python cli.py show-chunks <session_id>
```

### Test 3: Inspect Final

```bash
python cli.py show-final <session_id>
```

### Test 4: Regenerate

```bash
# Test regeneration with different model
python cli.py regenerate-summary <session_id>
```

---

## Performance Validation

### Benchmark Script

Create `benchmarks/test_summarizer_v2.py`:

```python
import time
from agent_core.llm.summarizer_v2 import ZuluSummarizer, SummarizerConfig
from agent_core.llm.ollama_llm_client import OllamaLLMClient
from agent_core.memory.summary_store_adapter import SummaryStoreAdapter
from agent_core.memory.session_store import SessionStore

def benchmark():
    # Setup
    llm = OllamaLLMClient()
    store = SummaryStoreAdapter(SessionStore())
    config = SummarizerConfig()
    summarizer = ZuluSummarizer(llm, store, config)
    
    conversation_id = "benchmark-test"
    test_text = "Test transcript " * 500  # ~1500 chars
    
    # Test chunk summary
    start = time.time()
    chunk_summary = summarizer.summarize_live_chunk(conversation_id, test_text)
    chunk_time = time.time() - start
    
    print(f"Chunk summary: {chunk_time:.2f}s")
    print(f"Model: {config.chunk_model}")
    print(f"Output: {chunk_summary[:100]}...\n")
    
    # Test final summary
    start = time.time()
    final_summary = summarizer.generate_final_summary(conversation_id)
    final_time = time.time() - start
    
    print(f"Final summary: {final_time:.2f}s")
    print(f"Model: {config.synthesis_model}")
    print(f"Output: {final_summary[:100]}...\n")
    
    print(f"Total: {chunk_time + final_time:.2f}s")

if __name__ == "__main__":
    benchmark()
```

**Expected results:**
- Chunk: 1-2 seconds
- Final: 10-15 seconds
- Total: 11-17 seconds

---

## Rollback Plan

If issues occur, rollback is simple:

### 1. Disable v2 in agent

Comment out summarizer_v2 initialization in `live_whisperx_agent.py`

### 2. Revert to v1

Use existing CallSummarizer instead

### 3. Keep data

Chunk summaries and final summaries remain in database for future use

---

## Success Criteria

✅ **Live summaries appear during recording**  
✅ **Final summary generated < 20s after call ends**  
✅ **All summaries stored in encrypted database**  
✅ **No errors in logs**  
✅ **Models download and run correctly**

---

**Version:** 2.0  
**Status:** Ready for Integration  
**Last Updated:** December 6, 2024
