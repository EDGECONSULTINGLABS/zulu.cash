# ZULU

Zulu is a **local-first execution harness for AI systems**.

It sits *below agents and applications* and *above the operating system*,
enforcing privacy, integrity, and control for AI running on-device.

Zulu is not an agent framework.

It is the environment agents run inside.

📄 [Lite Paper](docs/litepaper.md) · 🏗 [Architecture](docs/architecture.md) · ❓ [FAQ](docs/faq.md) · 🗺 [Roadmap](ROADMAP.md)

---

## Why Zulu exists

Most AI systems assume:
- cloud execution
- loose data boundaries
- trust-by-brand
- non-reproducible runs

Zulu replaces assumptions with enforcement.

If an AI system runs inside Zulu, you can prove:
- what data it accessed
- what it was allowed to do
- that memory stayed local
- that the system was not tampered with

---

## Where Zulu fits

```
Applications
↑
Agents / AI logic
↑
🔒 ZULU — Execution Harness
   • policy enforcement
   • encrypted local memory
   • deterministic installs
   • integrity verification
↑
OS / Hardware
```

---

## Harness capabilities

✔ Local-only execution by default  
✔ Encrypted, structured memory (not prompt stuffing)  
✔ Deterministic installs and runs  
✔ Integrity verification (detects single-bit tampering)  
✔ Explicit data and tool permissions  
✔ Model-agnostic (Ollama, llama.cpp, vLLM, etc.)  
✔ Agent-agnostic (any framework or custom logic)

---

## What Zulu is not

✗ Not an agent framework  
✗ Not a cloud AI service  
✗ Not a model provider  
✗ Not a blockchain  
✗ Not a SaaS platform

---

## Who Zulu is for

- Builders shipping local-first AI
- Enterprises handling sensitive data
- Regulated workflows (finance, tax, healthcare)
- Teams that need reproducibility and auditability
- Anyone who wants AI without data leakage

---

## Proof: integrity enforcement

Zulu verifies the integrity of models and execution artifacts.

Single-bit tampering is detected and execution fails by design.

### Verification capabilities

- BLAKE3 hashing with verified streaming
- BIP-39 seed phrase generation
- Ed25519 key infrastructure (BIP-44)
- Deterministic chunking (1 MiB blocks)
- Per-chunk verification
- Root commitments

### Try it

```bash
cd agents/zulu-verification
npm run build
npm run demo:attack    # See tamper detection in action
```

If any chunk is modified, verification fails immediately.

---

## Example agents

The `agents/` directory contains reference implementations that run inside Zulu.

These are **examples**, not the product. Zulu does not require or enforce a specific agent framework.

See [`agents/README.md`](agents/README.md) for details.

---

## Tech stack

| Component | Technology |
|-----------|------------|
| **Inference** | Ollama, llama.cpp, vLLM |
| **Memory** | SQLCipher (AES-256) |
| **Integrity** | BLAKE3 |
| **Identity** | Zcash Orchard (selective disclosure) |
| **Audio** | Whisper (local) |

---

## Repository structure

```
zulu/
├── agents/                  # Example agent implementations
│   ├── zulu-mpc-agent/      # Production reference agent
│   └── zulu-verification/   # Integrity verification engine
├── agent-core/              # Core harness libraries
├── src/                     # Harness source
├── docs/                    # Documentation
└── scripts/                 # Tooling
```

---

## Getting started

### Requirements

- Node.js 18+
- Python 3.10+
- Ollama
- SQLCipher

### Quick start

```bash
npm run setup
npm run demo
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

We welcome contributions that strengthen execution guarantees, memory isolation, and determinism.

We do not accept cloud-dependent or data-extractive designs.

---

## License

MIT License
