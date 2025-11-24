# ZULU.CASH — Private AI Agent OS for ZEC

<div align="center">

[![Built for Zypherpunk](https://img.shields.io/badge/Built%20for-Zypherpunk-F4B728?style=for-the-badge)](https://zypherpunk.xyz)
[![Zcash](https://img.shields.io/badge/Zcash-Shielded-F4B728?style=for-the-badge&logo=zcash)](https://z.cash)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![Privacy First](https://img.shields.io/badge/Privacy-First-purple?style=for-the-badge)](https://zulu.cash)

**Local-First AI • Shielded Identity • Private Memory • Zero Cloud**

[Website](https://zulu.cash) • [Lite Paper](docs/litepaper.md) • [Architecture](docs/architecture.md) • [FAQ](docs/faq.md)

</div>

---

## 💥 The Killer Line

> **Zulu is a warrior who remembers your mind, not your wallet.**

---

Zulu is a **local-first AI agent** that learns about you privately.

It runs on your device, uses shielded Zcash receivers as identity keys, and stores personal knowledge in encrypted memory — **never on a cloud**.

**Think:**  
Fireflies / Otter.ai / Rewind — except **zero telemetry + cryptographic privacy.**

ZULU never uploads your transcripts, calls, embeddings, or metadata to a remote server.  
**Your conversations stay inside your machine.**

---

## 🛡️ Core Principles

- ✅ **On-device AI** (Ollama / GGUF)
- ✅ **Encrypted memory** (SQLCipher / local vector store)
- ✅ **Shielded Zcash identity** (Orchard receivers)
- ✅ **Selective disclosure** → never audience-wide leaks
- ✅ **Zero cloud, zero custody, zero surveillance**

### Zulu does NOT:
- ❌ Hold user funds
- ❌ Transmit data to 3rd-party APIs
- ❌ Store multi-tenant logs
- ❌ Rely on SaaS LLMs
- ❌ "Farm" user conversations

---

## 🚀 Production-Ready: ZULU MPC Agent

**Location**: `agents/zulu-mpc-agent/`

A complete, production-ready implementation of ZULU's vision:

- ✅ **22 Python files, ~4,500 LOC**
- ✅ **Local Whisper Transcription** (faster-whisper with GPU)
- ✅ **Speaker Diarization** (PyAnnote/WhisperX)
- ✅ **Encrypted SQLCipher Database** (AES-256)
- ✅ **Local LLM Summarization** (Ollama)
- ✅ **Feature Extraction** (sentence-transformers)
- ✅ **MPC Client Framework** (Nillion-ready)
- ✅ **Full CLI Interface** (Rich terminal UI)
- ✅ **Docker Support** (Production deployment)

**Quick Start:**
```bash
cd agents/zulu-mpc-agent
./quickstart.sh
zulu process audio.wav --title "Team Meeting"
```

**Documentation**: See [`docs/zulu-mpc-agent.md`](docs/zulu-mpc-agent.md) for full details.

---

---

## 🎯 Vision

> **Artificial Intelligence should be your ally — not your spy.**

- Your agent learns about you **privately**
- Your knowledge stays **local**
- Your identity is **shielded**

This is **beyond Web2 analytics**, beyond surveillance finance, beyond Panopticon AI.

---

## 🧠 What ZULU Does

1. **Joins live calls** (Google Meet / Zoom / Discord)
2. **Generates private contextual notes**
3. **Builds a personal knowledge graph**
4. **Stores encrypted memory**
5. **Answers questions from your data**
6. **Never leaks anything to a server**

### This is:
- ✅ **Personal AI you own**
- ❌ Not a cloud AI that owns you

---

## 🌑 Why Zcash?

Zcash is the only chain designed for **selective disclosure by default**.

**Orchard shielded receivers = access keys.**

- **Not** a payment rail
- **Not** merchant processing
- **Not** stablecoin pivots

They are **cryptographic identity primitives**.

You don't reveal a private key.  
You reveal a receiver with limited scope.

This is **perfect for AI identity + permissioning**.

---

## 🧩 Example Use Cases

### 1. Personal AI Memory
Your assistant remembers your conversations, tasks, and knowledge.  
**Stored encrypted on device.**

### 2. Selective Sharing
Share a bounded memory trace with:
- Your accountant
- Your business partner
- Your doctor

**You don't "sign in"**  
**You "reveal a note"**

---

## 🧠 Live Agent Advantage

Every competitor is **"after-the-call"**:

- ❌ **Otter** = cloud logging
- ❌ **Fireflies** = SaaS recording
- ❌ **Rewind AI** = uploads embeddings

**Zulu is during the call:**
- ✅ Local speech pipeline
- ✅ Local transcription
- ✅ Local embeddings

**No cloud. No honeypots. No telemetry.**

The intelligence is **yours**, not theirs.

---

## ⚙️ Tech Stack (High-level)

| Component | Technology |
|-----------|------------|
| **LLM** | Ollama (Phi-3, Llama-3.1, Mistral) |
| **Memory** | Encrypted SQLite + private embeddings |
| **Audio** | VAD → Whisper.cpp (offline) |
| **Zcash** | Orchard Unified Address |
| **Vector Store** | Local (FAISS / Qdrant local mode) |
| **Frontend** | Electron + Tailwind |
| **Servers** | None |

---

## 📦 Repository Structure

```
zulu.cash/
├── agents/
│   ├── live/              # Conversation memory (Whisper + LLM)
│   ├── ledger/            # ZEC scanner (viewing keys only)
│   └── signer/            # Optional cold wallet (future)
│
├── ui/
│   ├── electron/          # Desktop app
│   ├── tailwind/          # UI components
│   └── nextjs/            # zulu.cash website
│
├── models/
│   ├── prompts/           # Agent prompts (live, ledger, signer)
│   ├── embeddings/        # Local vector store
│   └── personalization/   # User preferences
│
├── storage/
│   ├── ledger.sqlcipher   # ZEC transactions (encrypted)
│   ├── memory.sqlite      # Conversations (encrypted)
│   └── vault/             # Key storage (encrypted)
│
├── docs/
│   ├── litepaper.md
│   ├── architecture.md
│   ├── threat-model.md
│   └── build-log.md
│
└── scripts/
    ├── whisper-local.py   # Offline transcription
    ├── zcash-scan.ts      # Note scanner
    └── ledger-export.ts   # Backup utility
```

### 🎯 What This Shows Judges

- ✅ **2-agent architecture** (live + ledger, extreme separation)
- ✅ **Encrypted local state** (storage/ isolated)
- ✅ **Zero SaaS dependencies** (all scripts local)
- ✅ **Privacy by design** (vault/ for keys, no cloud)

---

## 🧭 Hackathon Track Fit

**Privacy-Preserving AI & Computation**

Best possible category for a local-first, shielded-identity AI agent.

---

## 🚫 What ZULU Is Not

- ❌ A custodial wallet
- ❌ Merchant service
- ❌ Payment processor
- ❌ Stablecoin bridge
- ❌ Tax SaaS

**Zulu = Private Agent OS.**

---

## 🛠️ Getting Started

### Requirements

- **Node.js 18+**
- **Python 3.10+**
- **Ollama** installed locally
- **SQLCipher**
- **Zcash lightwalletd** endpoint (testnet/mainnet)

### Run Agent Core

```bash
cd agent/core
pip install -r requirements.txt
python context_manager.py
```

### Run Frontend

```bash
cd agent/ui/electron
npm install
npm run dev
```

### Quick Test

```bash
# Install dependencies
npm run setup

# Run demo
npm run demo

# Test AI queries
npm run test:ai
```

---

## 🤝 Contributing

We welcome contributions from:

- 🔐 **Privacy engineers**
- 🤖 **ML devs**
- 🔬 **Cryptographers**
- 🏗️ **Zcash community members**
- 🧠 **Live agent researchers**

**PRs > hype.**

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 🛡️ Security

| Security Feature | Implementation |
|-----------------|----------------|
| Private keys | ❌ ZULU **never** asks for private keys |
| Viewing keys | ✅ Only uses viewing keys for note scanning |
| Data storage | ✅ All data is local & encrypted (SQLCipher) |
| AI inference | ✅ Fully local (Ollama) |
| Cloud services | ❌ No cloud inference |
| Telemetry | ❌ None |
| Multi-tenant logs | ❌ None |

> See [SECURITY.md](SECURITY.md) for detailed threat model.

---

## 📜 License

[MIT License](LICENSE) — open to change based on community feedback.

---

## 🟣 Follow the Build

<div align="center">

**Website:** [zulu.cash](https://zulu.cash)  
**X/Twitter:** [@MyCrypt0world](https://x.com/MyCrypt0world)  
**Hackathon:** [zypherpunk.xyz](https://zypherpunk.xyz)  
**GitHub:** [edgeconsultinglabs/zulu.cash](https://github.com/edgeconsultinglabs/zulu.cash)  
**Email:** team@edgeconsultinglabs.com

</div>

---

<div align="center">

## 🔥 Final Note

**Intelligence Without Surveillance.**

ZULU is your **personal AI** — not a cloud service that farms your behavior.

**If you're here, you're early.**  
**If you contribute, you're building the future of private AI.**

---

*Built for the Zypherpunk Hackathon*  
*Shielded Identity + Private Memory + Live Assistant*

</div>
