# Orchard Receivers — Identity Primitives

## Overview

ZULU uses **Orchard receivers** as **cryptographic identity primitives**.

## What is an Orchard Receiver?

An **Orchard receiver** is part of a Zcash Unified Address (UA).

### Structure
```
u1...   (Unified Address)
  ├── Orchard receiver
  ├── Sapling receiver (optional)
  └── Transparent receiver (optional)
```

### In ZULU
We use **only the Orchard receiver** as an identity slot.

## Why Orchard?

| Feature | Benefit |
|---------|---------|
| **Shielded** | Privacy by default |
| **Selective disclosure** | Viewing keys enable scoped access |
| **No linkability** | Each receiver is independent |
| **Cryptographically strong** | Halo 2 proofs |

## Identity Architecture

### Concept
Each Orchard receiver = **isolated memory shard**

```
┌─────────────────┐
│  User Identity  │
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
  Work    Personal  Medical   Tax
    │         │        │        │
receiver1 receiver2 receiver3 receiver4
    │         │        │        │
memory1   memory2   memory3   memory4
```

### Benefits
- ✅ **No global identity** — Each context is isolated
- ✅ **Selective disclosure** — Share specific memories only
- ✅ **No linkability** — Cannot link receivers together
- ✅ **User control** — Create/delete receivers at will

## Example Usage

### 1. Create Work Identity
```python
work_receiver = identity.create_receiver(label="work")
# Returns: u1abc...work
```

### 2. Use for Work Conversations
All work-related conversations use this receiver as the identity key.

### 3. Share with Colleague
```python
viewing_key = identity.get_viewing_key(work_receiver)
# Share viewing_key with colleague
# They can ONLY decrypt work-related memory
```

### 4. Personal Memory Stays Private
Your personal, medical, and tax memories remain **completely isolated**.

## Technical Details

### Receiver Generation
```python
from zcash import UnifiedAddress

# Generate new UA with Orchard receiver
ua = UnifiedAddress.generate(orchard=True)
orchard_receiver = ua.orchard_receiver()
```

### Viewing Key Derivation
```python
viewing_key = orchard_receiver.derive_viewing_key()
# Can decrypt notes sent to this receiver
# Cannot spend notes (no private key)
```

### Note Scanning
```python
notes = scanner.scan_notes(
    viewing_key=viewing_key,
    start_height=1000000
)

for note in notes:
    print(f"Received at block {note.height}")
    print(f"Memo: {note.memo}")
```

## Privacy Model

### What Receiver Reveals
- ⚠️ That a payment was received (if viewing key shared)
- ⚠️ Amount and memo (if viewing key shared)

### What Receiver Never Reveals
- ✅ Your other receivers
- ✅ Your global identity
- ✅ Your other memories
- ✅ Your private keys

## Selective Disclosure Pattern

### Scenario: Tax Audit
1. Create "tax" receiver
2. Use for all tax-related conversations
3. Generate viewing key for this receiver only
4. Share viewing key with accountant
5. Accountant can decrypt tax memories only
6. All other memories remain private

### Scenario: Medical Records
1. Create "medical" receiver
2. Use for all medical conversations
3. Generate viewing key for this receiver only
4. Share viewing key with doctor
5. Doctor can access medical history only
6. Work, personal, tax memories remain private

## Implementation Status

- [ ] Orchard receiver generation
- [ ] Viewing key derivation
- [ ] Memory partitioning by receiver
- [ ] Note scanning integration
- [ ] Selective disclosure API

## Next Steps

- Implement receiver management
- Add viewing key system
- Build memory partitioning
- Test selective disclosure

---

> **Orchard Receivers = Identity Without Surveillance**
