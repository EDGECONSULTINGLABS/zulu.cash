"""
Quick demo of Summarizer v2 without needing live audio.
Tests chunk summarization + final synthesis.
"""

import uuid
from agent_core.llm.summarizer_v2 import ZuluSummarizer, SummarizerConfig
from agent_core.llm.ollama_llm_client import OllamaLLMClient
from agent_core.memory.summary_store_adapter import SummaryStoreAdapter
from agent_core.memory.session_store import SessionStore

def main():
    print("\n" + "="*60)
    print("ZULU Summarizer v2 - Demo Test")
    print("="*60 + "\n")
    
    # Initialize components
    print("[*] Initializing summarizer v2...")
    llm_client = OllamaLLMClient()
    
    # Use test encryption key for demo
    import os
    if not os.environ.get("ZULU_DB_KEY"):
        os.environ["ZULU_DB_KEY"] = "demo-test-key-for-summarizer-v2-testing"
    
    store = SessionStore(db_path="./data/zulu_agent.db")
    adapter = SummaryStoreAdapter(store)
    
    config = SummarizerConfig(
        chunk_model="qwen2.5:1.5b",
        synthesis_model="llama3.1:8b",
        max_chunk_chars=500,  # Smaller for demo
    )
    
    summarizer = ZuluSummarizer(llm_client, adapter, config)
    conversation_id = str(uuid.uuid4())
    
    print(f"[OK] Conversation ID: {conversation_id}\n")
    
    # Simulate a conversation with 3 chunks
    chunks = [
        """
        John: Hey Sarah, thanks for joining the call. I wanted to discuss the Q1 project timeline.
        Sarah: Sure! What are the main concerns?
        John: We need to decide between launching in March or April. The marketing team needs at least 2 weeks lead time.
        Sarah: I think March 15 is doable if we prioritize Feature X over Feature Y.
        John: Good point. Feature X has more customer demand anyway.
        """,
        
        """
        Sarah: What about the budget? Do we have approval for external contractors if needed?
        John: Yes, the budget was approved yesterday. We can bring in help if the engineering team gets overloaded.
        Sarah: Perfect. That reduces the risk significantly.
        John: Agreed. Should we set up weekly check-ins starting Monday?
        Sarah: Definitely. Monday mornings at 10am work for me.
        """,
        
        """
        John: One last thing - there's a dependency on the third-party API. If that gets delayed, we're blocked.
        Sarah: Good catch. Let me reach out to their team today to confirm their timeline.
        John: Thanks. Can you also get capacity estimates from engineering by end of week?
        Sarah: Will do. I'll send those over by Friday.
        John: Great! I think we're aligned. Let's reconvene Monday.
        Sarah: Sounds good. Talk then!
        """
    ]
    
    # Generate chunk summaries (live simulation)
    print("[*] Generating chunk summaries (simulating live recording)...\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"--- Chunk {i} ---")
        summary = summarizer.summarize_live_chunk(
            conversation_id=conversation_id,
            raw_text=chunk.strip(),
        )
        print(f"\n[LIVE SUMMARY {i}]")
        print(summary)
        print("\n" + "="*60 + "\n")
    
    # Generate final synthesis
    print("[*] Call ended. Generating final executive summary...\n")
    
    final = summarizer.generate_final_summary(
        conversation_id=conversation_id,
        clear_cache=False,
    )
    
    print("="*60)
    print("[*] EXECUTIVE SUMMARY")
    print("="*60)
    print(final)
    print("="*60 + "\n")
    
    # Show what's in the database
    print("[*] Inspecting stored summaries...\n")
    
    chunks_stored = adapter.get_chunk_summaries(conversation_id)
    print(f"[OK] {len(chunks_stored)} chunk summaries stored")
    
    final_stored = adapter.get_final_summary(conversation_id)
    if final_stored:
        print(f"[OK] Final summary stored (model: {final_stored.get('model')})")
    
    print("\n[OK] ✅ Summarizer v2 test complete!")
    print(f"[*] Conversation ID: {conversation_id}")
    print("[*] All summaries encrypted in SQLCipher database\n")

if __name__ == "__main__":
    main()
