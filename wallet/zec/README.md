# wallet/zec

Zcash-specific primitives for ZULU.

## Overview

ZULU uses **view-only** Zcash keys to detect shielded transactions without custody.

## Components

- Viewing key extraction
- Transaction note scanning
- Orchard receiver support
- Selective disclosure proofs

## Non-Custodial Design

ZULU never:
- Holds spend keys
- Signs transactions
- Processes payments

ZULU only:
- Detects incoming shielded transactions
- Displays transaction metadata
- Enables selective disclosure (user-controlled)

## Future

- Multi-wallet support
- Unified address handling
- Memo field parsing
