# Zulu Verification System

Verified streaming architecture with BLAKE3 (using official npm `blake3` package v2.1.7) for secure artifact distribution, memory export/import, and plugin sandboxing.

## Features

### Phase 0: Integrity + Key Management
- **Deterministic Chunking**: Adaptive chunk sizes per artifact type (MODEL 1MiB, MEMORY 64KiB, PLUGIN 256KiB, UI 512KiB)
- **Root Commitment**: SimpleConcatV1 implementation, API compatible with future BaoMerkleV2
- **Key Management**: BIP-39 seed phrases with deterministic Ed25519 key derivation (BIP-44 paths)
- **Secure Storage**: OS keychain integration (macOS/Windows/Linux) with SQLCipher fallback
- **Signed Receipts**: Chain-of-custody with content-addressed storage
- **Trust Model**: Key expiration, revocation lists, team keyring

### Phase 1: Artifact System
- **Manifest Schema**: Publisher Ed25519 signatures
- **Trust Policies**: STRICT (default), WARN (user-approved), BEST_EFFORT (dev mode)
- **Resume Integrity**: Poisoned resume attack prevention
- **Streaming Downloader**: Per-chunk verification, atomic finalization
- **Error Taxonomy**: Typed verification errors for precise diagnostics

### Phase 2: Memory Export/Import
- **Session Commitments**: Verifiable transcript + summary + entities + embeddings
- **Import Validation**: Shard-level verification with rollback
- **Integrity Badges**: UI status indicators

### Phase 3: Plugin Sandbox
- **Fine-grained Permissions**: Filesystem, network, vault, compute limits
- **Sandbox Enforcement**: Worker thread isolation
- **Verified Updates**: Semantic versioning checks

## Installation

```bash
npm install
npm run build
```

## Usage

### TypeScript/JavaScript

```typescript
import { VerificationSystem } from '@zulu/verification';

const verifier = new VerificationSystem();
await verifier.initialize();

// Verify artifact
const result = await verifier.verifyArtifact('model.gguf', manifest);
```

### Python Bridge

```python
from zulu_verification import VerificationBridge

bridge = VerificationBridge()
result = bridge.verify_artifact('model.gguf', manifest)
```

## Testing

```bash
npm test              # Run all tests
npm run test:watch    # Watch mode
npm run benchmark     # Performance benchmarks
```

## Architecture

```
zulu-verification/
├── src/
│   ├── core/          # Core verification logic
│   ├── crypto/        # BLAKE3, Ed25519, BIP-39
│   ├── storage/       # SQLCipher, OS keychain
│   ├── chunking/      # Deterministic chunking
│   ├── artifacts/     # Artifact system
│   ├── memory/        # Memory export/import
│   ├── plugins/       # Plugin sandbox
│   └── bridge/        # Python integration
├── tests/
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── adversarial/   # Security tests
└── benchmarks/        # Performance tests
```

## Security

All verification operations are constant-time where applicable. Keys are stored in OS-native secure storage with encrypted fallback. See [SECURITY.md](SECURITY.md) for threat model.

## License

MIT License - See LICENSE file for details
