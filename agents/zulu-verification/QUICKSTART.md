# Zulu Verification System - Quick Start Guide

## Installation

```bash
cd agents/zulu-verification
npm install
npm run build
```

## First Run: Generate Seed Phrase

```typescript
import { generateMnemonic } from '@zulu/verification';

const seed = await generateMnemonic(12);
console.log('🔑 Your seed phrase:', seed.mnemonic);
console.log('⚠️  Store this securely! This is your master key.');
```

**Critical**: Write down your seed phrase on paper and store it securely. This cannot be recovered if lost.

## Basic Usage

### 1. Initialize System

```typescript
import { VerificationSystem, TrustPolicy } from '@zulu/verification';

const verifier = new VerificationSystem({
  dbPath: './data/verification.db',
  encryptionKey: process.env.ZULU_DB_KEY,
  tempDir: './temp',
  trustConfig: {
    policy: TrustPolicy.STRICT,
    teamKeyring: [
      '8f3e...', // Zulu team public keys
    ],
    userApprovedKeys: [],
    revokedKeys: [],
    expiryWarningDays: 30,
  },
});

await verifier.initialize();
```

### 2. Verify Artifact

```typescript
import { loadManifestFromFile } from '@zulu/verification';

// Load manifest
const manifest = await loadManifestFromFile('./model.manifest.json');

// Verify artifact
const result = await verifier.verifyArtifact(
  './model.gguf',
  manifest,
  './model-verified.gguf'
);

if (result.success) {
  console.log('✅ Artifact verified!');
} else {
  console.log('❌ Verification failed:', result.error);
}
```

### 3. Export Session (Memory)

```typescript
import { exportSession } from '@zulu/verification';

const bundle = await exportSession(
  {
    sessionId: 'session-123',
    transcript: { /* ... */ },
    summary: 'Meeting summary...',
    entities: [],
    embeddings: new Float32Array(384),
    metadata: {
      duration: 3600,
      modelId: 'gpt-4',
      tokenCount: 1000,
    },
  },
  privateKey,
  publicKey
);

// Save bundle
await saveExportBundle(bundle, './session-123.bundle.json');
```

### 4. Import Session

```typescript
import { loadExportBundle, importSession } from '@zulu/verification';

const bundle = await loadExportBundle('./session-123.bundle.json');
const result = await importSession(bundle);

if (result.success) {
  console.log('✅ Session imported and verified!');
}
```

## Python Integration

```python
from bridge.python.verification import VerificationBridge

# Initialize
bridge = VerificationBridge()

# Generate seed
seed = bridge.generate_seed_phrase(12)
print(f"Seed: {seed}")

# Verify model
result = bridge.verify_artifact(
    artifact_path="model.gguf",
    manifest_path="model.manifest.json"
)

if result.success:
    print(f"✅ Verified: {result.artifact_id}")
else:
    print(f"❌ Failed: {result.error}")
```

## Running Examples

```bash
# Basic usage
npm run build
node dist/examples/basic-usage.js

# Whisper model verification (full workflow)
node dist/examples/whisper-model-example.js
```

## Running Tests

```bash
# Unit tests
npm test

# Watch mode
npm run test:watch

# Performance benchmarks
npm run benchmark
```

## Trust Policies

### STRICT (Production)
- Only team keyring is trusted
- Best for production deployments
- Highest security

```typescript
policy: TrustPolicy.STRICT
```

### WARN (Default)
- Team keyring + user-approved keys
- Shows warnings for unknown keys
- Balanced security and flexibility

```typescript
policy: TrustPolicy.WARN
```

### BEST_EFFORT (Development Only)
- All keys accepted
- Shows warnings for everything
- **Never use in production**

```typescript
policy: TrustPolicy.BEST_EFFORT
```

## Key Management

### Store Seed Phrase

```typescript
const keychain = verifier.getKeychain();
await keychain.storeSeedPhrase('user-id', mnemonic);
```

### Derive Device Keys

```typescript
import { deriveKeyPair, mnemonicToSeed } from '@zulu/verification';

const seed = await mnemonicToSeed(mnemonic);
const device0 = await deriveKeyPair(seed, 0, 0); // m/44'/1337'/0'/0/0
const device1 = await deriveKeyPair(seed, 0, 1); // m/44'/1337'/0'/0/1
```

### Approve Key

```typescript
await verifier.approveKey(pubkeyHex);
```

### Revoke Key

```typescript
await verifier.revokeKey(pubkeyHex, 'Key compromised');
```

## Environment Variables

```bash
# Required
export ZULU_DB_KEY="your-secure-encryption-key-here"

# Optional
export NODE_ENV="production"
export ZULU_TRUST_POLICY="STRICT"
```

## File Structure

```
your-project/
├── data/
│   ├── verification.db        # SQLCipher database
│   └── models/
│       ├── model.gguf
│       ├── model.manifest.json
│       └── model.receipt.json
├── temp/                       # Download temp files
└── exports/
    └── session-*.bundle.json
```

## Security Checklist

- [ ] Generated seed phrase and stored securely offline
- [ ] Changed `encryptionKey` from default
- [ ] Set `ZULU_DB_KEY` environment variable
- [ ] Using STRICT or WARN trust policy (not BEST_EFFORT)
- [ ] Initialized team keyring with Zulu public keys
- [ ] Verified all models before loading
- [ ] Exported session receipts to secure storage
- [ ] Tested key revocation workflow

## Common Issues

### "Cannot find module 'blake3'"
Run: `npm install`

### "Keychain not available"
- On Windows: Ensure Credential Manager is accessible
- On macOS: Check Keychain access permissions
- On Linux: Install `libsecret-1-dev`
- Fallback: Uses SQLCipher automatically

### "Verification failed: UntrustedSignerError"
- Check trust policy setting
- Approve key: `verifier.approveKey(pubkeyHex)`
- Or add to team keyring

### Performance Issues
- Run benchmarks: `npm run benchmark`
- Check chunk sizes match artifact type
- Ensure SSD for temp directory
- Verify BLAKE3 optimizations are active

## Next Steps

1. **Production Setup**
   - Generate production seed phrase
   - Initialize team keyring
   - Deploy with STRICT policy

2. **Integration**
   - Integrate with Zulu MPC agent
   - Add verification to model loading
   - Export sessions after processing

3. **Monitoring**
   - Set up key expiry alerts (30 days)
   - Monitor verification logs
   - Track receipt generation

## Support

- Documentation: `README.md`, `IMPLEMENTATION.md`
- Examples: `examples/` directory
- Tests: `src/__tests__/` directory
- Issues: https://github.com/edgeconsultinglabs/zulu.cash

## License

MIT License - See LICENSE file
