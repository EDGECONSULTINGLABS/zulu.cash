# ZULU Scripts — Production Pipeline

## 🎯 Core Scripts

### 1. `zulu_live_pipeline.py`
**Whisper → Ollama → Structured Analysis**

Fully local pipeline for ZULU Live Agent:
- Transcribes audio with Whisper
- Analyzes with local Ollama LLM
- Returns structured JSON (summary, actions, tags)

**Usage:**
```bash
pip install openai-whisper requests
ollama pull phi3 && ollama serve
python zulu_live_pipeline.py path/to/audio.wav
```

### 2. `db-memory.ts`
**Memory Database Connection (SQLCipher)**

TypeScript functions for encrypted memory.db:
- `openMemoryDb()` - Connect to encrypted DB
- `createSession()` - Store meeting session
- `createNote()` - Store note/summary
- `createTask()` - Create action item

### 3. `db-ledger.ts`
**Ledger Database Connection (SQLCipher)**

TypeScript functions for encrypted ledger.db:
- `openLedgerDb()` - Connect to encrypted DB
- `addWallet()` - Add viewing key
- `recordTransaction()` - Log ZEC transaction
- `getWalletBalances()` - Query balances

---

> **All scripts run locally. Zero cloud dependencies.**
