# Zcash lightwalletd Integration

## Overview

ZULU connects to **lightwalletd** to scan for shielded notes.

## What is lightwalletd?

lightwalletd is a **Zcash light client server** that:
- Provides access to blockchain data
- Enables light clients to sync quickly
- Supports shielded transactions
- No custody of funds

## ZULU Usage

ZULU uses lightwalletd **only** for:
- ✅ Scanning incoming shielded notes
- ✅ Checking transaction status
- ✅ Getting block height

ZULU **never** uses lightwalletd for:
- ❌ Storing private keys
- ❌ Signing transactions
- ❌ Holding custody

## Architecture

```
ZULU → lightwalletd → Zcash Node
  ↓
Viewing Key Only
  ↓
Encrypted Local Storage
```

## Connection

### Testnet
```
lightwalletd.testnet.z.cash:9067
```

### Mainnet
```
mainnet.lightwalletd.com:9067
```

## API Calls

### 1. GetLatestBlock
Get current blockchain height.

```python
block = client.get_latest_block()
print(f"Current height: {block.height}")
```

### 2. GetTransaction
Get transaction details.

```python
tx = client.get_transaction(txid)
print(f"Status: {tx.status}")
```

### 3. GetTaddressTxids
Scan for transactions (transparent).

```python
txids = client.get_taddress_txids(address, start, end)
```

### 4. GetShieldedBalance
Get shielded balance (requires viewing key).

```python
balance = client.get_shielded_balance(viewing_key)
print(f"Balance: {balance}")
```

## Privacy Considerations

### What lightwalletd Sees
- ⚠️ Your IP address
- ⚠️ Which addresses you query
- ⚠️ When you make requests

### What lightwalletd Never Sees
- ✅ Your private keys
- ✅ Transaction contents (shielded)
- ✅ Your identity

### Mitigation
- Use Tor for additional privacy
- Run your own lightwalletd node
- Use trusted endpoints only

## Example Integration

```python
from zcash_client import LightwalletdClient

# Connect
client = LightwalletdClient("lightwalletd.testnet.z.cash:9067")

# Get latest block
block = client.get_latest_block()
print(f"Synced to block: {block.height}")

# Scan for notes (requires viewing key)
viewing_key = "..."
notes = client.scan_notes(viewing_key, start_height=1000000)

for note in notes:
    print(f"Note: {note.value} ZEC at block {note.height}")
```

## Next Steps

- [ ] Implement lightwalletd client
- [ ] Add viewing key scanning
- [ ] Add Tor support
- [ ] Add connection health checks

---

> **Minimal External Dependency. Maximum Privacy.**
