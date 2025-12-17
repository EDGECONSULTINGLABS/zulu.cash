# Examples

This directory contains **synthetic, non-sensitive examples** used to demonstrate ZULU behavior.

## What's Here

- Sample audio files (synthetic, not real conversations)
- Test transcripts (generated, not user data)
- Demo configurations (safe defaults)
- Integration examples (how to use ZULU APIs)

## What's NOT Here

❌ No real user data  
❌ No actual transcripts  
❌ No private keys  
❌ No session recordings  
❌ No personal information  

## Privacy Guarantee

All examples are:
- **Synthetic** - Generated for demonstration
- **Non-sensitive** - Safe to commit to git
- **Auditable** - Open for review

Real user data lives in:
- `/data/` (gitignored)
- `/storage/` (gitignored)
- `/agents/*/data/` (gitignored)

And is **never** committed to version control.

## For Contributors

When adding examples:
1. ✅ Use synthetic data only
2. ✅ Document what the example demonstrates
3. ✅ Keep examples minimal and focused
4. ❌ Never commit real user data

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) for full guidelines.
