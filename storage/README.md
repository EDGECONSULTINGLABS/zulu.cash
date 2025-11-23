# Storage — Encrypted Local Data

## Structure
```
storage/
├── ledger.sqlcipher      # ZEC transactions (encrypted)
├── memory.sqlite         # Conversations (encrypted)
└── vault/                # Sensitive keys (encrypted)
```

## Encryption
- **SQLCipher** → 256-bit AES encryption
- **Key derivation** → From device characteristics
- **Zero plaintext** → Always encrypted at rest

## Data Separation
- **Live Agent** → memory.sqlite
- **Ledger Agent** → ledger.sqlcipher
- **No cross-contamination** → Isolated storage

## Backup
- User-controlled export
- Encrypted backups only
- No cloud sync

## Privacy Guarantee
**Nothing leaves this directory unencrypted.**

---

> **Encrypted vault. Your data only.**
