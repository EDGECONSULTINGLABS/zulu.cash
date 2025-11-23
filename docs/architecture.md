# ZULU Architecture — Private Agent OS

---

## Component Diagram

```
Local Audio → VAD → Whisper.cpp → LLM → Memory Store → ZEC Identity
```

---

## On-Device Data Flow

```
microphone → raw audio
     ↓
VAD (voice activity detection)
     ↓
Whisper.cpp (offline STT)
     ↓
LLM context transformer
     ↓
semantic vector
     ↓
SQLCipher + FAISS
     ↓
Shielded identity gating
```

---

## Identity Layer

### Orchard shielded receiver = identity slot
Each Unified Address creates an **isolated memory shard**.

### Viewing key = selective disclosure
Limited-scope access to specific memory partitions.

### Self-custody = local-only memory
No server-side storage, no multi-tenant databases.

---

## 1. Local Device Layer

### Audio Pipeline
- **Microphone input** → Raw audio stream
- **VAD (Voice Activity Detection)** → Filters silence
- **Whisper.cpp** → Offline speech-to-text
- **Transcript** → Local text buffer

### LLM Engine
- **Ollama** → Local inference server
- **Phi-3 Mini / Llama-3.1** → Language models
- **Context window** → Previous conversation history
- **Output** → Contextual summary / response

### Memory Store
- **SQLCipher** → Encrypted SQLite database
- **FAISS / Qdrant (local)** → Vector embeddings
- **Encryption at rest** → Always encrypted
- **No cloud sync** → Device-only storage

---

## 2. Identity Layer (ZEC)

### Orchard Receiver = Access Profile
Each shielded receiver acts as an **identity slot**.

- User creates multiple receivers for different contexts
- Each receiver isolates a **memory partition**
- No linkability between receivers

### Viewing Key = Selective Audit
Narrow-scope access to specific memory traces.

- User can share viewing key for a single partition
- Receiver can decrypt notes in that partition only
- No access to other memory shards

### Unified Address = Memory Partition
Each UA creates an **isolated memory shard**.

- Personal → Work → Medical → etc.
- No cross-contamination
- No global memory leakage

---

## 3. Vector Store

### Local Embeddings
- **Text → Vector** → Ollama embeddings API
- **Storage** → FAISS index (local file)
- **Query** → Semantic search over personal knowledge

### Privacy Guarantees
- ✅ **No cloud embeddings**
- ✅ **No shared index**
- ✅ **No telemetry**

---

## 4. Knowledge Engine

### Contextual Reasoning
LLM performs reasoning against **previous entries**.

```
User Query → Vector Search → Retrieve Context → LLM Response
```

### Example Queries
- "What did I discuss with my accountant last week?"
- "Summarize all medical conversations"
- "What tasks did I commit to in recent calls?"

### Privacy
- All queries processed **on-device**
- No API calls to external LLMs
- No logging to external servers

---

## 5. Selective Disclosure

### Scenario: Sharing with Your Accountant

1. User creates a **"tax" receiver** in ZULU
2. All tax-related calls use this receiver as the identity key
3. User generates a **viewing key** for this receiver
4. User shares viewing key with accountant
5. Accountant can decrypt **only tax-related notes**
6. Other memory partitions remain private

---

## 6. Privacy Model

### What ZULU Stores (Encrypted)
- ✅ Transcripts (local)
- ✅ Embeddings (local)
- ✅ Context summaries (local)
- ✅ Memory graph (local)

### What ZULU Never Sees
- ❌ Private keys
- ❌ Cloud storage
- ❌ Multi-tenant databases
- ❌ External analytics

### External Connections
- **lightwalletd** → For Zcash note scanning
- **None** → No other external services

---

## 7. Security Architecture

### Threat Model

**Adversaries:**
- Cloud telemetry miners
- SaaS inference leakers
- State-level forensic scraping

**Design Goal:**
Prevent ANY external party from reconstructing your cognitive data.

### Defense Layers

| Layer | Defense |
|-------|---------|
| **Network** | No cloud uploads |
| **Storage** | SQLCipher encryption |
| **Identity** | Zcash shielded receivers |
| **Memory** | Partitioned by receiver |
| **Inference** | Local-only (Ollama) |

---

## 8. Tech Stack

| Component | Technology |
|-----------|------------|
| **LLM** | Ollama (Phi-3, Llama-3.1) |
| **Memory** | SQLCipher + FAISS |
| **Audio** | Whisper.cpp |
| **Zcash** | Orchard UA |
| **Vector Store** | FAISS (local) |
| **Frontend** | Electron + Tailwind |
| **Backend** | Python + Node.js |

---

## 9. Deployment Model

### On-Premise
- **User device** → All computation
- **No servers** → No cloud infrastructure
- **Self-custody** → User owns all data

### Future: Optional MPC Layer
- **Nillion** → Secure multi-party computation
- **Fhenix** → Fully homomorphic encryption
- **Mina** → Zero-knowledge identity bridge

---

## 10. Comparison: ZULU vs. Competitors

| Feature | ZULU | Otter.ai | Fireflies | Rewind AI |
|---------|------|----------|-----------|-----------|
| **Cloud uploads** | ❌ | ✅ | ✅ | ✅ |
| **Local inference** | ✅ | ❌ | ❌ | ❌ |
| **Encrypted storage** | ✅ | ❌ | ❌ | ❌ |
| **Shielded identity** | ✅ | ❌ | ❌ | ❌ |
| **Selective disclosure** | ✅ | ❌ | ❌ | ❌ |
| **No telemetry** | ✅ | ❌ | ❌ | ❌ |

---

## 11. Future Architecture

### Advanced Privacy Layer

- **Nillion MPC** → Secure computation on encrypted data
- **Fhenix FHE** → Encrypted operations
- **Mina ZK** → Zero-knowledge identity proofs

### Cross-Device Sync (Privacy-Preserving)

- **Encrypted sync** → Between user's own devices
- **No cloud server** → Peer-to-peer or local network
- **Receiver-based** → Only sync specific partitions

---

## Summary

ZULU is a **local-first, privacy-first AI agent** that:

- ✅ Runs entirely on your device
- ✅ Uses Zcash shielded identities for access control
- ✅ Stores all memory encrypted
- ✅ Never uploads data to the cloud
- ✅ Enables selective disclosure via viewing keys

**This is the opposite of surveillance AI.**

---

> **Intelligence Without Surveillance.**  
> Built for the Zypherpunk Hackathon.
