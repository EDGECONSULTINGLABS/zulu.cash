# ZULU FAQ — Private Agent OS for Zcash

---

## General Questions

### What is ZULU?
ZULU is a **local-first AI agent** that joins calls, creates private memory, and performs contextual reasoning **without sending data to the cloud**.

It uses **Zcash shielded identities** for selective disclosure and **local encrypted storage** for all knowledge.

### Is ZULU a payment app?
**No.** ZULU is a **Private Agent OS**, not a payment processor or merchant service.

It uses Zcash shielded receivers as **cryptographic identity primitives**, not for payments.

### What does "Private Agent OS" mean?
It's an operating system for personal AI that:
- Runs on your device
- Stores memory encrypted
- Uses shielded identity for access control
- Never uploads data to the cloud

---

## Privacy & Security

### Does ZULU upload my data to the cloud?
**No.** ZULU runs entirely on your device. Nothing is uploaded to external servers.

### What data does ZULU store?
- ✅ **Transcripts** (encrypted, local)
- ✅ **Embeddings** (local vector store)
- ✅ **Context summaries** (encrypted, local)
- ✅ **Memory graph** (local only)

All stored in an **encrypted SQLite database (SQLCipher)**.

### Can ZULU see my private keys?
**No.** ZULU never asks for or stores private keys.

It only uses **shielded receivers** as identity slots and **viewing keys** for selective disclosure.

### How is ZULU different from Otter.ai, Fireflies, or Rewind AI?
| Feature | ZULU | Otter.ai | Fireflies | Rewind AI |
|---------|------|----------|-----------|-----------|
| **Cloud uploads** | ❌ | ✅ | ✅ | ✅ |
| **Local inference** | ✅ | ❌ | ❌ | ❌ |
| **Encrypted storage** | ✅ | ❌ | ❌ | ❌ |
| **Shielded identity** | ✅ | ❌ | ❌ | ❌ |
| **Selective disclosure** | ✅ | ❌ | ❌ | ❌ |
| **No telemetry** | ✅ | ❌ | ❌ | ❌ |

---

## Technical Questions

### What AI models does ZULU use?
ZULU runs **local LLMs** via **Ollama**:
- Phi-3 Mini
- Llama-3.1
- Mistral

All inference happens **on your device**.

### Does ZULU require an internet connection?
**Minimal.** ZULU only connects to:
- **lightwalletd** → For Zcash note scanning

All AI inference, transcription, and memory storage happen **offline**.

### What is a "shielded receiver"?
A **shielded receiver** is part of a Zcash Unified Address.

ZULU uses receivers as **identity slots** to partition memory.

- Each receiver = isolated memory shard
- No linkability between receivers
- Selective disclosure via viewing keys

### What is a "viewing key"?
A **viewing key** allows someone to decrypt notes sent to a specific receiver.

In ZULU, viewing keys enable **selective disclosure**:
- You can share a viewing key for a specific memory partition
- The recipient can only decrypt that partition
- Other memory remains private

---

## Use Cases

### Can ZULU join live calls?
**Yes (in development).** ZULU will join:
- Google Meet
- Zoom
- Discord

And generate **private contextual notes** without uploading data.

### What can I ask ZULU?
Examples:
- "What did I discuss with my accountant last week?"
- "Summarize all medical conversations"
- "What tasks did I commit to in recent calls?"

All queries processed **on-device**.

### Can I share my ZULU memory with someone?
**Yes, selectively.** You can:
1. Create a **receiver** for a specific context (e.g., "tax")
2. Generate a **viewing key** for that receiver
3. Share the viewing key with your accountant

They can only decrypt notes from that context, nothing else.

---

## Zcash Integration

### Why Zcash?
Zcash is the only chain designed for **selective disclosure by default**.

**Orchard shielded receivers = access keys.**

They are **cryptographic identity primitives**, not payment rails.

### Does ZULU hold ZEC?
**No.** ZULU is **non-custodial**.

It only uses shielded receivers as **identity slots**, not for storing or transmitting funds.

### What is an "Orchard receiver"?
An **Orchard receiver** is part of a Zcash Unified Address.

It's a **shielded address** that enables private transactions.

ZULU uses Orchard receivers as **identity keys** for memory partitioning.

---

## Development & Roadmap

### What's the current status?
**Phase 1 — Core Agent (Current)**
- ✅ Local LLM (Ollama)
- ✅ Encrypted memory (SQLCipher)
- ✅ Zcash identity stubs
- 🔄 Audio pipeline (Whisper.cpp)
- 🔄 Vector store integration

See [roadmap.md](roadmap.md) for full details.

### Can I contribute?
**Absolutely!** We welcome contributions from:
- 🔐 Privacy engineers
- 🤖 ML devs
- 🔬 Cryptographers
- 🏗️ Zcash community members
- 🧠 Live agent researchers

**PRs > hype.**

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

### Is ZULU open source?
**Yes.** ZULU is licensed under [MIT License](../LICENSE).

---

## Hackathon

### What hackathon track is ZULU in?
**Privacy-Preserving AI & Computation**

Best possible category for a local-first, shielded-identity AI agent.

### Why "Zypherpunk"?
The **Zypherpunk Hackathon** is focused on privacy, cryptography, and decentralization.

ZULU embodies these principles:
- Privacy-first architecture
- Cryptographic identity (Zcash)
- Zero cloud surveillance

---

## Comparison

### ZULU vs. Traditional AI Assistants

**Traditional AI (Otter, Fireflies, Rewind):**
- ❌ Cloud-based
- ❌ Telemetry farming
- ❌ Multi-tenant databases
- ❌ Behavioral profiling
- ❌ No user control

**ZULU:**
- ✅ On-device
- ✅ Zero telemetry
- ✅ Local-only storage
- ✅ No profiling
- ✅ User-owned data

---

## Support

### Where can I get help?
- **Email:** team@edgeconsultinglabs.com
- **X/Twitter:** [@MyCrypt0world](https://x.com/MyCrypt0world)
- **GitHub Issues:** [github.com/edgeconsultinglabs/zulu.cash](https://github.com/edgeconsultinglabs/zulu.cash)

### Where can I learn more?
- **Website:** [zulu.cash](https://zulu.cash)
- **Lite Paper:** [docs/litepaper.md](litepaper.md)
- **Architecture:** [docs/architecture.md](architecture.md)
- **Roadmap:** [docs/roadmap.md](roadmap.md)

---

> **Intelligence Without Surveillance.**  
> Built for the Zypherpunk Hackathon.
