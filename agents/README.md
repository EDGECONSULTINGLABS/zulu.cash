# ZULU Agents

This directory contains the core execution engines for ZULU.

## Production Agents

### `zulu-mpc-agent/`
**Production local-first AI agent** (Python)

- ~4,500 LOC Python
- Local Whisper transcription (GPU)
- Speaker diarization (WhisperX / PyAnnote)
- Encrypted SQLCipher memory (AES-256)
- Local LLM summarization (Ollama)
- Episodic memory architecture
- MPC-ready (Nillion framework)
- Full CLI + Docker support

**Quick start**:
```bash
cd zulu-mpc-agent
./quickstart.sh
zulu process audio.wav --title "Meeting"
```

**Documentation**: [`docs/zulu-mpc-agent.md`](../docs/zulu-mpc-agent.md)

### `zulu-verification/`
**Cryptographic integrity & verification engine** (TypeScript)

- BLAKE3 hashing with Bao verified streaming
- BIP-39 seed phrase generation
- Ed25519 key infrastructure (BIP-44)
- Deterministic chunking (MODEL = 1 MiB)
- Per-chunk verification
- Root commitments (SimpleConcatV1)
- Adversarial tamper detection

**Quick start**:
```bash
cd zulu-verification
npm run demo:attack    # See tamper detection in action
npm run demo:keys      # Test key derivation
```

**Documentation**: [`PRODUCTION_READY.md`](zulu-verification/PRODUCTION_READY.md)

## Runtime Data

All runtime data is **local** and **ignored by git**:
- `/agents/*/data/` - Session data
- `/agents/*/storage/` - Encrypted vaults
- `/agents/*/models/` - Downloaded models
- `/agents/*/logs/` - Execution logs

**No user data, transcripts, or keys are ever committed.**

## Architecture

```
agents/
├── zulu-mpc-agent/          # Production AI agent
│   ├── agent_core/
│   │   ├── inference/       # Whisper, diarization
│   │   ├── llm/             # Ollama, summarization
│   │   ├── memory/          # SQLCipher vault
│   │   ├── mpc/             # Nillion MPC
│   │   └── pipelines/       # Orchestration
│   └── data/                # (gitignored)
│
└── zulu-verification/       # Integrity engine
    ├── src/
    │   ├── crypto/          # BLAKE3, Ed25519
    │   ├── chunking/        # Deterministic splitting
    │   ├── storage/         # SQLCipher, keychain
    │   └── trust/           # Policy engine
    ├── examples/            # Executable proofs
    └── dist/                # (generated)
```

## For Contributors

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) for guidelines.

**We welcome**:
- Inference speedups
- Memory research
- MPC experiments
- UI improvements

**We reject**:
- Cloud SaaS designs
- Surveillance analytics
- Data extraction shortcuts

**ZULU is sacred. Not negotiable.**
