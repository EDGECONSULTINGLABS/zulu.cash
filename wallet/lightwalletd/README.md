# wallet/lightwalletd

Lightwalletd integration for ZULU.

## Overview

ZULU connects to a lightwalletd server to scan the Zcash blockchain for shielded transactions.

## Design

- **View-only**: Uses viewing keys, not spend keys
- **Privacy-preserving**: Minimal data exposure to lightwalletd
- **User-controlled**: User chooses which lightwalletd server to use

## Configuration

Users can:
- Use default lightwalletd (e.g., Zcash Foundation)
- Run their own lightwalletd instance
- Switch servers at any time

## Future

- Tor support for enhanced privacy
- Multi-server scanning for redundancy
- Compact block filters
