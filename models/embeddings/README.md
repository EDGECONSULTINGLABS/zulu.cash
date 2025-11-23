# Embeddings — Local Vector Store

## Purpose
Store conversation embeddings locally for semantic search.

## Technology
- **FAISS** or **Qdrant (local mode)**
- **Ollama embeddings** → phi3, llama3.1
- **Encrypted storage**

## Structure
```
embeddings/
├── conversations.faiss
├── metadata.json
└── index.config
```

## Privacy
- ✅ All embeddings stored locally
- ✅ No cloud vector store
- ✅ Encrypted at rest
- ❌ Never shared

---

> **Semantic memory without surveillance.**
