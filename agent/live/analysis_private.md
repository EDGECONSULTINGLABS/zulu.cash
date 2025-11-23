# Private Analysis — On-Device LLM

## Overview

ZULU analyzes conversations using **local LLMs** via Ollama.

## Why Local Analysis?

- ✅ **Zero cloud exposure** — All inference on-device
- ✅ **No API keys** — No external LLM services
- ✅ **No logging** — No conversation telemetry
- ✅ **Full privacy** — Your data never leaves your machine

## Architecture

```
Transcript → Context Manager → Ollama LLM → Analysis → Encrypted Storage
```

## Supported Models

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| Phi-3 Mini | 3.8 GB | Fast | Good |
| Llama-3.1 (8B) | 4.7 GB | Moderate | Great |
| Mistral (7B) | 4.1 GB | Moderate | Great |

## Analysis Types

### 1. Contextual Summary
Generate a concise summary of the conversation.

```python
summary = llm.summarize(transcript)
# "Discussed Q3 budget allocation and marketing strategy."
```

### 2. Action Items
Extract action items and commitments.

```python
actions = llm.extract_actions(transcript)
# ["Follow up with accounting team", "Review proposal by Friday"]
```

### 3. Key Topics
Identify main topics discussed.

```python
topics = llm.extract_topics(transcript)
# ["budget", "marketing", "Q3 planning"]
```

### 4. Sentiment Analysis
Analyze conversation sentiment.

```python
sentiment = llm.analyze_sentiment(transcript)
# "Positive, collaborative tone"
```

## Privacy Model

### What Gets Analyzed
- ✅ Transcript text (local)
- ✅ Context from memory (local)
- ✅ Previous summaries (local)

### What Never Gets Analyzed
- ❌ Cloud LLM APIs
- ❌ External services
- ❌ Telemetry systems

## Example Usage

```python
from context_manager import ContextManager
from ollama import Client

# Initialize
manager = ContextManager("./zulu_memory.db")
llm = Client(host="http://localhost:11434")

# Analyze transcript
transcript = "..."
analysis = llm.generate(
    model="phi3",
    prompt=f"Analyze this conversation: {transcript}"
)

# Store encrypted
manager.store_to_memory(analysis)
```

## Performance

- **Latency:** 1-3 seconds per analysis
- **Memory:** 4-8 GB RAM
- **CPU:** Multi-core recommended
- **GPU:** Optional (speeds up inference)

## Next Steps

- [ ] Implement streaming analysis
- [ ] Add custom prompts for different contexts
- [ ] Optimize token usage
- [ ] Add caching for repeated queries

---

> **Private Analysis = Your Intelligence, Your Device**
