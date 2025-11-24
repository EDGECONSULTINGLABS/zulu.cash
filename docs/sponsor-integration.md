# Sponsor Integration Guide

ZULU is designed to integrate with privacy-preserving infrastructure sponsors.

## Supported Integrations

### Zcash Ecosystem

- **Lightwalletd**: For shielded transaction scanning
- **Orchard Protocol**: For latest ZEC privacy features
- **Viewing Keys**: Non-custodial transaction detection

### Privacy Infrastructure

- **Nillion**: MPC for collaborative computation without data exposure
- **Fhenix**: FHE for encrypted computation
- **Mina**: ZK proofs for identity bridging

## Integration Principles

All sponsor integrations must:

1. **Preserve Privacy**
   - No user data leakage to sponsor services
   - Local-first processing where possible
   - Encrypted communication channels

2. **Maintain Sovereignty**
   - User controls when/if to use sponsor services
   - No forced dependencies
   - Graceful degradation if sponsor unavailable

3. **Open Standards**
   - Use public APIs and protocols
   - Document integration points
   - Enable alternative implementations

## How to Integrate

### For Infrastructure Sponsors

1. Review `docs/architecture.md` for system design
2. Identify integration points (inference, storage, identity)
3. Submit proposal via GitHub issue
4. Implement privacy-preserving adapter
5. Add integration tests
6. Document usage in this file

### For Zcash Ecosystem

ZULU uses:
- Viewing keys (not spend keys)
- Lightwalletd for chain scanning
- Orchard receivers for latest privacy features

See `wallet/` directory for implementation details.

## Current Sponsors

- **Zcash Foundation**: Core protocol support
- **[Add sponsors as they join]**

## Sponsorship Opportunities

Interested in sponsoring ZULU development?

- Privacy infrastructure (MPC, FHE, ZK)
- Zcash ecosystem tooling
- UI/UX improvements
- Security audits

Contact: [Add contact method]
