# Selective Disclosure — Privacy Without Secrecy

## Concept

**Selective disclosure** = Share specific information without revealing everything.

## Traditional Problem

In traditional systems:
- Either **all private** (no sharing possible)
- Or **all public** (no privacy)

## ZULU Solution

**Share bounded memory traces** using Zcash viewing keys.

### How It Works

```
┌──────────────┐
│   User has   │
│  4 receivers │
└──────┬───────┘
       │
   ┌───┴───┬────────┬────────┐
   │       │        │        │
 Work  Personal  Medical   Tax
   │       │        │        │
Share VK1  Keep   Keep    Share VK4
   │     Private Private     │
   │                         │
   ▼                         ▼
Colleague                Accountant
(sees work only)      (sees tax only)
```

## Use Cases

### 1. Work Collaboration
**Goal:** Share work context with team, keep personal life private

```python
# Create work receiver
work_receiver = identity.create_receiver("work")

# Use for all work calls
# ...

# Share with colleague
work_vk = identity.get_viewing_key(work_receiver)
send_to_colleague(work_vk)

# Colleague can:
# ✅ See work meeting notes
# ✅ Access work action items
# ✅ Query work context

# Colleague cannot:
# ❌ See personal conversations
# ❌ Access medical records
# ❌ View tax information
```

### 2. Medical Records
**Goal:** Share health history with doctor, keep finances private

```python
# Create medical receiver
medical_receiver = identity.create_receiver("medical")

# Use for health-related calls
# ...

# Share with doctor
medical_vk = identity.get_viewing_key(medical_receiver)
send_to_doctor(medical_vk)

# Doctor can:
# ✅ See medical history
# ✅ Review symptoms
# ✅ Access treatment notes

# Doctor cannot:
# ❌ See work conversations
# ❌ Access bank statements
# ❌ View personal messages
```

### 3. Tax Audit
**Goal:** Prove financial history to accountant, keep personal details private

```python
# Create tax receiver
tax_receiver = identity.create_receiver("tax")

# Use for financial discussions
# ...

# Share with accountant
tax_vk = identity.get_viewing_key(tax_receiver)
send_to_accountant(tax_vk)

# Accountant can:
# ✅ See financial discussions
# ✅ Access tax-related notes
# ✅ Verify business expenses

# Accountant cannot:
# ❌ See medical records
# ❌ Access personal messages
# ❌ View work meetings
```

## Technical Implementation

### 1. Receiver Creation
```python
receiver = identity.create_receiver(label)
# Creates isolated memory partition
```

### 2. Memory Partitioning
```python
memory.set_active_receiver(receiver)
# All subsequent data tagged with this receiver
```

### 3. Viewing Key Generation
```python
vk = identity.get_viewing_key(receiver)
# Viewing key for this receiver only
```

### 4. Selective Access
```python
# Recipient uses viewing key
memory.decrypt_partition(viewing_key)
# Can only access notes for this receiver
```

## Privacy Properties

### Strong Isolation
- Each receiver has **independent memory**
- No cross-contamination
- No global identity

### Cryptographic Guarantees
- Viewing key cannot derive private key
- Cannot link receivers together
- Cannot access other partitions

### User Control
- Create receivers at will
- Delete partitions
- Revoke viewing keys (by creating new receiver)

## Comparison

| System | Disclosure Model |
|--------|------------------|
| **Traditional** | All or nothing |
| **Cloud AI** | Everything to provider |
| **Local AI** | Nothing shared |
| **ZULU** | **Selective by receiver** |

## Advantages Over Alternatives

### vs. Cloud AI (Otter, Fireflies)
- ❌ Cloud: Everything visible to provider
- ✅ ZULU: Share only what you want

### vs. Fully Private (no sharing)
- ❌ Fully private: Cannot share anything
- ✅ ZULU: Share bounded memory traces

### vs. Access Control Lists (ACLs)
- ❌ ACLs: Server-side enforcement
- ✅ ZULU: Cryptographic enforcement

## Implementation Status

- [ ] Receiver-based partitioning
- [ ] Viewing key system
- [ ] Selective decryption API
- [ ] Partition management UI

## Next Steps

- Build receiver management
- Implement viewing key derivation
- Create partition UI
- Test sharing workflows

---

> **Selective Disclosure = Privacy + Collaboration**
