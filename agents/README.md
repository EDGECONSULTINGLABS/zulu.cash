# Agents

Agents in this directory are examples.

Zulu does not require or enforce a specific agent framework.
Any AI logic that respects Zulu's execution policies can run here.

---

## Reference implementations

### `zulu-mpc-agent/`

Production reference agent (Python)

- Local Whisper transcription
- Speaker diarization
- Encrypted SQLCipher memory
- Local LLM summarization (Ollama)
- MPC-ready architecture

```bash
cd zulu-mpc-agent
./quickstart.sh
```

### `zulu-verification/`

Integrity verification engine (TypeScript)

- BLAKE3 hashing
- BIP-39 seed generation
- Ed25519 key infrastructure
- Deterministic chunking
- Tamper detection

```bash
cd zulu-verification
npm run demo:attack
```

---

## Runtime data

All runtime data is local and gitignored:

- `*/data/` — Session data
- `*/storage/` — Encrypted vaults
- `*/models/` — Downloaded models
- `*/logs/` — Execution logs

No user data, transcripts, or keys are committed.

---

## Adding new agents

Any agent can run inside Zulu if it:

1. Respects execution policies
2. Uses local-only storage
3. Does not exfiltrate data
4. Passes integrity verification

See the reference implementations for patterns.
