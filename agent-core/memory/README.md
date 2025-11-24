# agent-core/memory

Memory abstraction layer for ZULU.

## Overview

ZULU uses encrypted local storage (SQLCipher) with two separate databases:

1. **memory.db**: Session transcripts, notes, tasks, embeddings
2. **ledger.db**: Wallet metadata, transactions, exports

## Design

- **Separation**: Live agent and Ledger agent use different databases with different encryption keys
- **Zero correlation**: No cross-database queries or joins
- **Local-first**: All data stays on device

## Schemas

See `data/schemas/` for canonical SQLCipher schemas:
- `schema_memory.sql`
- `schema_ledger.sql`

## Future

- Vector embeddings for semantic search
- Incremental backups
- Selective sync (user-controlled)
