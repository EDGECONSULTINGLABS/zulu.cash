# SQLCipher — Encrypted Local Storage

## Overview

ZULU uses **SQLCipher** for encrypted local database storage.

## What is SQLCipher?

SQLCipher is:
- ✅ **Full database encryption** — 256-bit AES
- ✅ **SQLite-compatible** — Drop-in replacement
- ✅ **Cross-platform** — Windows, macOS, Linux
- ✅ **Zero-knowledge** — No cloud, no telemetry

## Why SQLCipher?

| Feature | Benefit |
|---------|---------|
| **Encryption at rest** | All data encrypted on disk |
| **Page-level encryption** | Every database page encrypted |
| **No plaintext** | Never written unencrypted |
| **Fast** | Minimal performance overhead |

## Setup

### Install SQLCipher

#### Windows
```bash
pip install pysqlcipher3
```

#### macOS
```bash
brew install sqlcipher
pip install pysqlcipher3
```

#### Linux
```bash
sudo apt install sqlcipher libsqlcipher-dev
pip install pysqlcipher3
```

## Usage

### 1. Create Encrypted Database

```python
from pysqlcipher3 import dbapi2 as sqlite

# Connect and set encryption key
conn = sqlite.connect('zulu_memory.db')
conn.execute("PRAGMA key='your-encryption-key'")

# Create tables
conn.execute(open('schema.sql').read())
conn.commit()
```

### 2. Insert Data (Encrypted Automatically)

```python
conn.execute("""
    INSERT INTO conversations (receiver_id, partition_id, title)
    VALUES (?, ?, ?)
""", (1, 1, "Team standup"))
conn.commit()
```

### 3. Query Data

```python
cursor = conn.execute("""
    SELECT * FROM conversations 
    WHERE receiver_id = ?
""", (1,))

for row in cursor:
    print(row)
```

### 4. Close Connection

```python
conn.close()
```

## Key Management

### Deriving Key from Device

```python
import hashlib
import platform
import os

def derive_key():
    """
    Derive encryption key from device characteristics.
    WARNING: This is a simple example. Use proper key derivation.
    """
    machine_id = platform.node()
    user_home = os.path.expanduser('~')
    
    # Combine with user-specific salt
    salt = f"{machine_id}{user_home}"
    
    # Derive key
    key = hashlib.sha256(salt.encode()).hexdigest()
    return key
```

### Secure Key Storage

For production, consider:
- **Windows:** Windows Credential Manager
- **macOS:** Keychain
- **Linux:** Secret Service API / gnome-keyring

## Encryption Strength

| Property | Value |
|----------|-------|
| **Algorithm** | AES-256-CBC |
| **Key size** | 256 bits |
| **Page size** | 4096 bytes (default) |
| **PBKDF2 iterations** | 256,000 |

## Performance

### Benchmarks
- **Overhead:** ~5-15% compared to SQLite
- **Read speed:** Minimal impact
- **Write speed:** Slight overhead (encryption)

### Optimization
```python
# Increase page size for better performance
conn.execute("PRAGMA page_size = 8192")

# Increase cache size
conn.execute("PRAGMA cache_size = 10000")
```

## Security Properties

### What SQLCipher Protects
- ✅ **Data at rest** — Encrypted on disk
- ✅ **Cold boot attacks** — Data encrypted in storage
- ✅ **Disk forensics** — Cannot recover without key

### What SQLCipher Doesn't Protect
- ❌ **Data in memory** — Decrypted when queried
- ❌ **Compromised device** — Malware can access
- ❌ **Weak passwords** — Use strong keys

## Backup & Export

### Export Encrypted Database
```bash
# Copy encrypted database
cp zulu_memory.db zulu_backup.db
```

### Export to Plaintext (for migration)
```python
# Connect to encrypted DB
conn = sqlite.connect('zulu_memory.db')
conn.execute("PRAGMA key='your-key'")

# Export to plaintext
conn.execute("ATTACH DATABASE 'plaintext.db' AS plaintext KEY ''")
conn.execute("SELECT sqlcipher_export('plaintext')")
conn.execute("DETACH DATABASE plaintext")
```

### Re-encrypt with New Key
```python
# Connect with old key
conn = sqlite.connect('zulu_memory.db')
conn.execute("PRAGMA key='old-key'")

# Re-key to new key
conn.execute("PRAGMA rekey='new-key'")
conn.commit()
```

## Integration with ZULU

### Context Manager Example

```python
from pysqlcipher3 import dbapi2 as sqlite
from memory_encryption import MemoryEncryption

class ZuluDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.encryptor = MemoryEncryption()
        self.key = self.encryptor.derive_key()
        
    def connect(self):
        conn = sqlite.connect(self.db_path)
        conn.execute(f"PRAGMA key='{self.key}'")
        return conn
        
    def store_conversation(self, receiver_id, title, messages):
        conn = self.connect()
        
        # Create conversation
        cursor = conn.execute("""
            INSERT INTO conversations (receiver_id, partition_id, title)
            VALUES (?, ?, ?)
        """, (receiver_id, 1, title))
        
        conversation_id = cursor.lastrowid
        
        # Store messages
        for msg in messages:
            # Encrypt content
            content_encrypted = self.encryptor.encrypt(msg['content'])
            
            conn.execute("""
                INSERT INTO messages (conversation_id, role, content_encrypted)
                VALUES (?, ?, ?)
            """, (conversation_id, msg['role'], content_encrypted))
        
        conn.commit()
        conn.close()
```

## Best Practices

### DO:
- ✅ Use strong encryption keys (256-bit)
- ✅ Derive keys from secure sources
- ✅ Use OS keychain for key storage
- ✅ Backup encrypted databases
- ✅ Test key recovery process

### DON'T:
- ❌ Hardcode encryption keys
- ❌ Store keys in plaintext
- ❌ Use weak passwords as keys
- ❌ Export to plaintext unnecessarily
- ❌ Share encryption keys

## Troubleshooting

### "file is not a database" Error
This usually means wrong encryption key.

```python
# Verify key
conn = sqlite.connect('zulu_memory.db')
try:
    conn.execute("PRAGMA key='your-key'")
    conn.execute("SELECT * FROM sqlite_master LIMIT 1")
    print("Key is correct")
except:
    print("Wrong key or corrupted database")
```

### Performance Issues
```python
# Increase cache and page size
conn.execute("PRAGMA cache_size = 10000")
conn.execute("PRAGMA page_size = 8192")
conn.execute("VACUUM")
```

## References

- **SQLCipher:** https://www.zetetic.net/sqlcipher/
- **Documentation:** https://www.zetetic.net/sqlcipher/documentation/
- **Python bindings:** https://github.com/rigglemania/pysqlcipher3

---

> **Encrypted Storage = Zero Data Leakage**
