# Ledger Agent — ZEC Transaction Scanner

## Purpose
Scans Zcash shielded notes using viewing keys only.

## Features
- **lightwalletd** → Minimal external dependency
- **Viewing keys only** → Never touches private keys
- **Local classification** → AI categorizes transactions
- **Encrypted ledger** → SQLCipher storage

## Architecture
```
lightwalletd → View Key → Note Scanner → Classifier → Encrypted Ledger
```

## Privacy
- ✅ View-only access
- ✅ Local AI classification
- ✅ Encrypted storage
- ❌ No custody

---

> **Scans your chain, not your keys.**
