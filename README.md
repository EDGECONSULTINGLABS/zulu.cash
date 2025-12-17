# ZULU.CASH — Private AI Agent OS for ZEC

**Built for Zypherpunk · Privacy First · MIT License**

**Local-First AI • Shielded Identity • Private Memory • Zero Cloud**

🌐 [Website](https://zulu.cash) · 📄 [Lite Paper](docs/litepaper.md) · 🏗 [Architecture](docs/architecture.md) · ❓ [FAQ](docs/faq.md)

---

> Every home got a personal computer.  
> Every person will get a private AI.  
> **ZULU is the first one built for that world.**

Zulu is a warrior who remembers your mind — not your wallet.

---

## What ZULU Is

**ZULU is a local-first AI agent OS that lives entirely on your device.**

It can:
- Join live calls
- Transcribe in real time
- Identify speakers
- Summarize context
- Store long-term memory

All data is stored **locally**, **encrypted**, and **never sent to the cloud**.

There is:
- ❌ No cloud inference  
- ❌ No upstream embeddings  
- ❌ No hidden training  
- ❌ No telemetry  

Your conversations, your memory, your data — stay inside your machine.

---

## Why Legacy AI Will Lose

Every "AI note-taker" SaaS (Otter, Fireflies, Rewind):

- Streams audio to cloud GPUs  
- Fingerprints your voice  
- Stores embeddings remotely  
- Builds behavioral profiles  
- Trains models on your conversations  

They sell convenience while mining the most valuable human asset of the 21st century:  
**attention + memory**.

**ZULU is the opposite.**  
It does not mine you. It works for you.

---

## 🧠 Local-First Software (Ink & Switch Alignment)

ZULU is built on the principles of **Local-First Software**, as defined by Ink & Switch:  
https://www.inkandswitch.com/essay/local-first/

Local-first software treats the user's device as the **primary computer**, not a thin client for someone else's server.

This is not a UX preference.  
It is a systems architecture decision.

### How ZULU Implements Local-First (For Real)

**Fast**  
- Local inference (Ollama, Whisper)
- No network latency

**Works Offline**  
- Fully functional without internet
- No auth servers, no cloud dependencies

**Data Ownership**  
- All data stored in a local SQLCipher vault
- Delete a file = delete your data

**Privacy by Default**  
- No telemetry
- No SaaS LLMs
- No upstream embeddings

**User Control**  
- Selective disclosure
- Explicit, scoped memory sharing
- You don't "log in" — you reveal a note

**Resilience**  
- No server outages
- No account lockouts
- No API quota failures

**Transparency**  
- Open source
- Auditable storage
- Deterministic behavior

---

## �️ Verifiable Integrity (BLAKE3)

ZULU does not trust files by name, version, or source.

It verifies **every byte**.

### What This Means
- Models, plugins, and memory are **stream-verified**
- If **one bit changes**, verification fails
- No cloud trust assumptions
- No silent corruption

---

## 🧪 Verification System — Working Demo

The verification engine is implemented and tested locally.

**Location**: `agents/zulu-verification/`

### Proven Capabilities

✅ BIP-39 seed phrase generation  
✅ Ed25519 key infrastructure  
✅ BLAKE3 hashing  
✅ Deterministic chunking (MODEL = 1 MiB)  
✅ Per-chunk verification  
✅ Root commitments  
✅ Integrity receipts (SQLCipher-ready)  

### What the Demo Does

1. Generates a 12-word seed phrase  
2. Creates a 5 MB test artifact  
3. Splits into deterministic chunks  
4. Hashes each chunk with BLAKE3  
5. Builds a root commitment  
6. Verifies every chunk  

If any chunk is modified, verification fails immediately.

**Run the demos:**
```bash
# From repo root
cd agents/zulu-verification

# Build TypeScript
npm run build

# Verify clean artifact
npm run demo

# Run adversarial tamper tests
npm run demo:attack

# Test deterministic key derivation
npm run demo:keys
```

Each command:
- Compiles TypeScript → `dist/`
- Runs against production JS
- Demonstrates real cryptographic guarantees

This module underpins:
- Model installs
- Plugin loading
- Memory export/import
- Resume-safe downloads
- Future P2P distribution

---

## 🚀 Production-Ready: ZULU MPC Agent

📍 `agents/zulu-mpc-agent/` 

A complete production implementation:

- ✅ ~4,500 LOC Python
- ✅ Local Whisper transcription (GPU)
- ✅ Speaker diarization (WhisperX / PyAnnote)
- ✅ Encrypted SQLCipher memory (AES-256)
- ✅ Local LLM summarization (Ollama)
- ✅ Episodic memory architecture
- ✅ MPC-ready (Nillion framework)
- ✅ Full CLI + Docker support

### Quick Start

```bash
cd agents/zulu-mpc-agent
./quickstart.sh
zulu process audio.wav --title "Team Meeting"
```

**Docs**: [`docs/zulu-mpc-agent.md`](docs/zulu-mpc-agent.md)

### 🧠 Hierarchical Summarization (Zero Hallucination)

- **Qwen2.5-1.5B** → fast factual chunk summaries
- **Llama3.1-8B** → high-quality synthesis
- Auto-chunking for long audio
- Fact-only constraints

**Result:**  
Accurate summaries grounded in real audio.  
No invented context. No hallucinations.

### 📚 Episodic Memory System

ZULU remembers like a human:

- Session-level summaries
- Encrypted long-term recall
- One embedding = entire event
- 300× faster retrieval

Memory stores what happened, not guesses.

---

##  Why Zcash?

Zcash is the only chain designed for selective disclosure by default.

ZULU uses:
- Orchard shielded receivers
- Viewing-key-based access
- No custodial wallets
- No payment processing

Zcash is not a payment rail here.  
It is a cryptographic identity primitive.

---

## 🧩 Example Use Cases

### 1. Personal AI Memory
Your assistant remembers conversations and knowledge — encrypted, local, private.

### 2. Selective Sharing
Reveal a bounded memory trace to:
- An accountant
- A partner
- A doctor

No logins. No global access. Just proof.

---

## 🧠 Live Agent Advantage

Every competitor is "after the call".

ZULU is **during the call**:
- Local speech pipeline
- Local embeddings
- Local memory

No cloud. No honeypots. No surveillance.

---

## ⚙️ Tech Stack

| Component | Technology |
|-----------|------------|
| **LLM** | Ollama (Llama-3.1, Phi-3, Mistral) |
| **Memory** | SQLCipher + local embeddings |
| **Audio** | Whisper (offline) |
| **Integrity** | BLAKE3 |
| **Identity** | Zcash Orchard |
| **UI** | Electron + Tailwind |
| **Servers** | None |

---

## 📦 Repository Structure

```
zulu.cash/
├── agents/
│   ├── zulu-mpc-agent/       # ⭐ production agent
│   ├── zulu-verification/
│   ├── live/                 # future
│   └── ledger/               # future
├── ui/
├── wallet/
├── storage/
├── docs/
└── scripts/
```

---

## 🧭 What This Shows Judges

✅ Real code  
✅ Production MVP  
✅ Privacy by architecture  
✅ No cloud dependency  
✅ Honest scope  
✅ Zypherpunk-aligned

---

## 🎯 Vision

Artificial intelligence should be your ally — not your spy.

Local inference.  
Encrypted memory.  
Selective disclosure.

AI as a personal asset — not a rented service.

---

## 🛠️ Getting Started

### Requirements
- Node.js 18+
- Python 3.10+
- Ollama
- SQLCipher

### Run agent:
```bash
npm run setup
npm run demo
```

---

## 🤝 Contributing

We welcome:
- Inference speedups
- Memory research
- MPC experiments
- UI improvements

We reject:
- Cloud SaaS designs
- Surveillance analytics
- Data extraction shortcuts

ZULU is sacred. Not negotiable.

---

## 📜 License

MIT License.

Open for builders. Closed to extractors.

---

## 🟣 Follow the Build

**Website**: https://zulu.cash  
**X**: @MyCrypt0world  
**GitHub**: edgeconsultinglabs/zulu.cash  
**Hackathon**: zypherpunk.xyz

---

The future of AI is private.

Not rented. Not surveilled. Not harvested.

ZULU is how people reclaim it.
