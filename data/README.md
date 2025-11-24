# data

Encrypted, local-first data layer for ZULU.

- SQLCipher schemas for memory and ledger
- Migrations for schema evolution
- No external databases or cloud storage.

Subfolders:
- `schemas/` – canonical SQLCipher schemas (memory, ledger, etc.)
- `migrations/` – forward-only migrations for versioned upgrades
