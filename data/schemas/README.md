# data/schemas

Canonical SQLCipher schemas for ZULU.

## Schemas

### memory.db (Live Agent)

`schema_memory.sql`:
- `sessions`: Conversation sessions
- `notes`: User notes and highlights
- `tasks`: Action items
- `embeddings`: Vector embeddings for semantic search

### ledger.db (Ledger Agent)

`schema_ledger.sql`:
- `wallets`: Wallet metadata (viewing keys only)
- `transactions`: Detected shielded transactions
- `exports`: Selective disclosure exports

## Design Principles

- **Separation**: Two databases, two encryption keys
- **Zero correlation**: No cross-database queries
- **Privacy-first**: Minimal data retention

## Usage

Initialize databases with:
```bash
sqlite3 storage/memory.db
> PRAGMA key = 'your-passphrase';
> .read data/schemas/schema_memory.sql
> .quit
```

See `QUICKSTART.md` for full setup instructions.
