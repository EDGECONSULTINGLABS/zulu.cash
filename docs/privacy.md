# Privacy Model

ZULU is designed with privacy-first principles:

## Core Guarantees

1. **Local-First Processing**
   - All AI inference happens on-device
   - No cloud uploads of audio, transcripts, or analysis
   - No external API calls for core functionality

2. **Encrypted Storage**
   - SQLCipher for all persistent data
   - Separate encryption keys for memory and ledger
   - Keys stored in OS keychain, never hardcoded

3. **Zero Telemetry**
   - No analytics
   - No crash reporting to external servers
   - No usage tracking

4. **Shielded Identity**
   - View-only Zcash keys (no spend capability)
   - Transaction detection without custody
   - No correlation between identity and payments

## Threat Model

See `threat-model.md` for detailed adversary analysis.

## Data Minimization

ZULU only stores:
- Session transcripts (encrypted, local)
- User-approved notes and tasks
- ZEC transaction metadata (amounts, timestamps)

ZULU never stores:
- Raw audio files (deleted after transcription)
- Cloud credentials
- Contact lists
- Biometric data

## User Control

- Users can delete any session or note
- Export functionality for data portability
- No vendor lock-in
