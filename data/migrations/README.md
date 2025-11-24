# data/migrations

Schema migrations for ZULU databases.

## Overview

As ZULU evolves, database schemas may need updates. Migrations ensure:
- Forward compatibility
- Data preservation
- Safe upgrades

## Migration Strategy

- **Forward-only**: No rollbacks (simplifies logic)
- **Versioned**: Each migration has a version number
- **Idempotent**: Safe to run multiple times

## Future

Migration scripts will be added here as schemas evolve.

## Current Status

Initial schemas (v1) are in `data/schemas/`:
- `schema_memory.sql`
- `schema_ledger.sql`

No migrations yet (v1 is baseline).
