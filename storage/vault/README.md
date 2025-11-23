# Vault — Sensitive Key Storage

## Purpose
Secure storage for encryption keys and sensitive data.

## Contents
- Encryption keys
- Device-derived secrets
- Viewing keys (if stored)
- User authentication tokens

## Security
- **Platform keychain integration**
  - Windows: Credential Manager
  - macOS: Keychain
  - Linux: Secret Service API
- **Hardware-backed** where available
- **Never in plaintext**

## Privacy
- ✅ OS-level security
- ✅ Hardware-backed
- ✅ Never exported
- ❌ No cloud backup

---

> **Fort Knox for your keys.**
