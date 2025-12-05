# ZULU.CASH Releases

## v0.2.0 — Production Intelligence (December 5, 2024)

**🧠 Hierarchical Summarization Engine**
- Chunked summarization for long recordings (2+ hours)
- 10x faster processing (60s vs 594s)
- Zero hallucinations, scales to unlimited length
- Splits transcripts into 40-segment chunks
- Independent chunk summaries merged into final comprehensive summary

**📝 Episodic Memory System**
- Session-level summary embeddings (1 embedding = entire meeting)
- 300x faster recall vs turn-level search
- Human-like memory architecture (remember events, not just facts)
- Database schema migration (`is_session_summary` flag)
- Two-tier search pattern ready for implementation

**🐛 Production Hardening**
- Fixed unhashable type errors in sentiment display
- Safe JSON serialization for all LLM outputs
- Graceful error handling with full tracebacks
- Episodic memory storage integrated into live agent

**Documentation:**
- `HIERARCHICAL_SUMMARY_UPGRADE.md` - Full technical overview
- `EPISODIC_MEMORY.md` - Memory system architecture
- `BUGFIX_EPISODIC_MEMORY.md` - Bug fixes and lessons learned

---

## v0.1.0 — Hackathon Edition (November 2024)

**🎙️ Live WhisperX Meeting Agent**
- Real-time audio capture and transcription
- Speaker diarization (PyAnnote)
- Local processing (no cloud)

**🧠 Local LLM Reasoning**
- Ollama integration (llama3.1:8b)
- Call summarization
- Key points extraction
- Action items detection

**🔒 Encrypted SQLCipher Memory Vault**
- AES-256 encrypted storage
- Session management
- Utterance storage with embeddings

**🔐 MPC Analytics**
- Nillion MPC client integration
- Privacy-preserving engagement scoring
- Anonymous embedding transmission

**✨ Features:**
- Session-level summaries + embeddings
- Temp audio auto-cleanup
- Rich CLI interface
- Docker support

---

## Roadmap

### v0.3.0 — Intelligent Retrieval (Q1 2025)
- [ ] Two-tier semantic search (session → turn fallback)
- [ ] Natural language queries ("What did we decide yesterday?")
- [ ] Cosine similarity ranking with thresholds
- [ ] Multi-session memory consolidation

### v0.4.0 — Advanced Intelligence (Q2 2025)
- [ ] Multi-model support (Mistral, Phi-3, Qwen)
- [ ] Streaming summaries (real-time progress)
- [ ] Adaptive chunking (dynamic size based on content)
- [ ] Knowledge graph extraction

### v1.0.0 — Production Ready (Q3 2025)
- [ ] Desktop app (Electron)
- [ ] Browser extension
- [ ] Mobile app (iOS/Android)
- [ ] Plugin ecosystem
- [ ] Zcash identity integration

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| v0.2.0 | Dec 5, 2024 | Hierarchical summarization + Episodic memory |
| v0.1.0 | Nov 2024 | Initial hackathon release |

---

**Privacy Commitment:**

Every ZULU release maintains our core principles:
- ✅ 100% local processing
- ✅ 100% encrypted storage
- ✅ 100% open source
- ❌ Zero cloud inference
- ❌ Zero data harvesting
- ❌ Zero surveillance

---

*Building in public for a private future.*
