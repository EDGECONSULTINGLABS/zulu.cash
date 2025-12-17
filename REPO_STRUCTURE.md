# Repository Structure

Clean, privacy-first, production-grade structure.

## Root Level (Canonical)

```
zulu.cash/
├── README.md              # Single source of truth
├── SECURITY.md            # Threat model & security practices
├── CONTRIBUTING.md        # Contribution guidelines
├── QUICKSTART.md          # Fast integration guide
├── LICENSE                # MIT License
├── requirements.txt       # Python dependencies
└── .gitignore             # Runtime state exclusions
```

## Core Directories

### `agents/`
Production execution engines.

- `zulu-mpc-agent/` - Local-first AI agent (Python, ~4,500 LOC)
- `zulu-verification/` - Cryptographic integrity engine (TypeScript)

See [`agents/README.md`](agents/README.md)

### `docs/`
Technical documentation.

- `architecture/` - System design
- `releases/` - Version history
- `diagrams/` - Visual references

### `examples/`
Synthetic, non-sensitive demonstrations.

See [`examples/README.md`](examples/README.md)

### `scripts/`
Development utilities.

### `ui/`
Desktop UX (Electron + Tailwind).

### `wallet/`
ZEC lightwalletd + Orchard integration.

## Runtime State (Gitignored)

These directories contain **local runtime state** and are **never committed**:

```
/data/              # Session data
/storage/           # Encrypted vaults
/models/            # Downloaded models
/logs/              # Execution logs
/wallet/            # Wallet state
```

**Privacy guarantee**: No user data, transcripts, or keys are ever committed to git.

## Build Artifacts (Gitignored)

```
/dist/              # Compiled output
/build/             # Build artifacts
node_modules/       # Dependencies
__pycache__/        # Python cache
*.egg-info/         # Python packages
```

## Development Files (Gitignored)

```
.env                # Environment variables
*.db                # Local databases
*.log               # Log files
temp/               # Temporary files
```

## What This Structure Communicates

✅ **Source vs State** - Clear separation  
✅ **Privacy-First** - No user data in git  
✅ **Production-Grade** - Serious OSS structure  
✅ **Judge-Credible** - Easy to navigate  
✅ **Contributor-Ready** - Clear boundaries  

## For Judges & Reviewers

**What to look at**:
1. `agents/` - Core implementations
2. `README.md` - Project overview
3. `SECURITY.md` - Threat model
4. `docs/` - Technical details

**What's gitignored** (by design):
- All runtime state (`/data/`, `/storage/`, `/models/`, `/logs/`)
- All user data (transcripts, sessions, keys)
- All build artifacts (`/dist/`, `/build/`)

## For Contributors

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for:
- How to contribute
- What we accept
- What we reject
- Code standards

---

**This structure scales, signals seriousness, protects privacy, and makes judging easier.**
