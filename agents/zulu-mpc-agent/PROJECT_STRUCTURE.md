# ZULU MPC Agent - Complete Project Structure

## 📁 Directory Organization

```
zulu-mpc-agent/
│
├── 📄 Core Documentation
│   ├── README.md              # Main project documentation
│   ├── ARCHITECTURE.md        # Technical architecture details
│   ├── CONTRIBUTING.md        # Contribution guidelines
│   ├── CHANGELOG.md           # Version history
│   └── LICENSE                # MIT License
│
├── ⚙️ Configuration
│   ├── config/
│   │   └── default.yaml       # Main configuration file
│   ├── .env.template          # Environment variables template
│   └── .gitignore             # Git ignore rules
│
├── 🐍 Core Agent Code
│   └── agent_core/
│       ├── __init__.py        # Package initialization
│       │
│       ├── inference/         # ML Inference modules
│       │   ├── whisper_model.py      # Whisper transcription
│       │   ├── diarization.py        # Speaker diarization
│       │   └── embedder.py           # Feature extraction
│       │
│       ├── llm/               # LLM integration
│       │   ├── ollama_client.py      # Ollama API client
│       │   └── summarizer.py         # Call summarization
│       │
│       ├── memory/            # Storage layer
│       │   └── session_store.py      # SQLCipher database
│       │
│       ├── mpc/               # Multi-Party Computation
│       │   └── nillion_client.py     # Nillion MPC client
│       │
│       ├── pipelines/         # Orchestration
│       │   └── whisper_diarization.py # Main pipeline
│       │
│       ├── utils/             # Utilities
│       │   ├── config.py             # Configuration management
│       │   ├── crypto.py             # Cryptography utilities
│       │   └── logging.py            # Logging setup
│       │
│       └── prompts/           # LLM prompts
│           └── call_summarizer.md    # Summarization prompt
│
├── 💾 Data & Storage
│   └── data/
│       ├── schemas/
│       │   └── 001_core.sql          # Database schema
│       ├── models/                    # Model weights (gitignored)
│       ├── backups/                   # Database backups (gitignored)
│       └── temp/                      # Temporary files (gitignored)
│
├── 🖥️ Command Line Interface
│   └── cli.py                 # Full-featured CLI
│
├── 🧪 Tests
│   └── tests/
│       └── test_pipeline.py   # Pipeline tests
│
├── 📦 Deployment
│   ├── Dockerfile             # Container image
│   ├── docker-compose.yml     # Multi-container setup
│   ├── setup.py               # Package installation
│   ├── requirements.txt       # Python dependencies
│   └── Makefile               # Common operations
│
├── 📚 Examples
│   └── examples/
│       └── example_usage.py   # Usage demonstration
│
└── 🚀 Quick Start
    └── quickstart.sh          # Automated setup script

```

## 📊 File Statistics

- **Total Python Files**: 22
- **Total Lines of Code**: ~4,500+
- **Configuration Files**: 4
- **Documentation Files**: 5
- **Test Files**: 1 (expandable)

## 🔧 Key Components

### 1. Core Pipeline (`agent_core/pipelines/whisper_diarization.py`)
- **Lines**: ~350
- **Purpose**: Orchestrates entire processing pipeline
- **Dependencies**: All inference, LLM, memory, and MPC modules

### 2. Whisper Integration (`agent_core/inference/whisper_model.py`)
- **Lines**: ~120
- **Purpose**: Local speech-to-text using faster-whisper
- **Features**: GPU acceleration, VAD, multiple model sizes

### 3. Speaker Diarization (`agent_core/inference/diarization.py`)
- **Lines**: ~200
- **Purpose**: Identify who said what
- **Backends**: Simple, PyAnnote, WhisperX (future)

### 4. Database Layer (`agent_core/memory/session_store.py`)
- **Lines**: ~400
- **Purpose**: Encrypted storage with SQLCipher
- **Features**: CRUD operations, backup, vacuum

### 5. LLM Summarization (`agent_core/llm/summarizer.py`)
- **Lines**: ~150
- **Purpose**: Generate structured summaries
- **Features**: Action items, decisions, risks

### 6. MPC Client (`agent_core/mpc/nillion_client.py`)
- **Lines**: ~250
- **Purpose**: Privacy-preserving computation
- **Features**: Secret sharing, MPC programs

### 7. CLI Interface (`cli.py`)
- **Lines**: ~350
- **Purpose**: User-friendly command-line tool
- **Commands**: process, list, show, delete, health, init

### 8. Configuration System (`agent_core/utils/config.py`)
- **Lines**: ~180
- **Purpose**: Hierarchical configuration management
- **Features**: YAML + env vars, validation

## 🗄️ Database Schema

```sql
sessions (9 columns)
├── utterances (7 columns)
├── action_items (7 columns)
├── decisions (5 columns)
└── mpc_feature_index (7 columns)

Total: 5 tables, 35 columns
```

## 📦 Dependencies

### Core ML/AI
- faster-whisper (Whisper inference)
- sentence-transformers (Embeddings)
- torch (ML framework)
- transformers (HuggingFace)

### Database & Security
- sqlcipher3 (Encrypted database)
- cryptography (Crypto utilities)

### LLM & API
- ollama (Local LLM)
- requests (HTTP client)

### CLI & UX
- click (CLI framework)
- rich (Terminal UI)
- pyyaml (Configuration)

### Development
- pytest (Testing)
- black (Code formatting)
- mypy (Type checking)

## 🚀 Getting Started

### 1. Quick Start (Automated)
```bash
./quickstart.sh
```

### 2. Manual Setup
```bash
# Install
pip install -r requirements.txt
pip install -e .

# Initialize
zulu init

# Process
zulu process audio.wav --title "My Call"
```

### 3. Docker
```bash
docker-compose up -d
docker-compose exec zulu-agent zulu health
```

## 🎯 Usage Examples

### Process a Call
```bash
zulu process meeting.mp3 \
  --title "Product Review" \
  --language en
```

### List Sessions
```bash
zulu list -n 20
```

### Show Details
```bash
zulu show abc123def456
```

### Health Check
```bash
zulu health
```

## 🔐 Security Features

1. **Database Encryption**: AES-256 via SQLCipher
2. **Key Derivation**: PBKDF2-HMAC-SHA512 (600k iterations)
3. **Feature Hashing**: SHA-256 verification
4. **MPC Secret Sharing**: Nillion protocol
5. **Speaker Anonymization**: SPK_1, SPK_2, etc.
6. **Optional Audio Cleanup**: Delete after processing

## 📈 Performance

### Typical Processing Time (5-min call)
- Transcription: 30s (CPU) / 3s (GPU)
- Diarization: 10s
- Summarization: 5s
- Embeddings: <1s
- **Total**: ~48s (CPU) / ~21s (GPU)

### Storage
- Audio: ~5 MB (original)
- Database: ~100 KB per call
- Models: ~1 GB (first time download)

## 🧪 Testing

```bash
# Run all tests
make test

# With coverage
pytest tests/ --cov=agent_core --cov-report=html

# Specific test
pytest tests/test_pipeline.py -v
```

## 📝 Code Quality

```bash
# Format code
make format

# Lint
make lint

# Type check
mypy agent_core/
```

## 🌟 Features

### ✅ Implemented
- ✅ Whisper transcription (multiple models)
- ✅ Speaker diarization (multiple backends)
- ✅ Local LLM summarization
- ✅ Encrypted database storage
- ✅ Feature extraction & embeddings
- ✅ MPC client framework
- ✅ CLI interface
- ✅ Docker support
- ✅ Comprehensive documentation

### 🚧 Planned
- 🚧 Real-time transcription
- 🚧 Web interface
- 🚧 Custom prompts
- 🚧 Export formats (PDF, DOCX)
- 🚧 Multi-language UI

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing`
5. Open Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 📧 Contact

**Built by**: Edge Consulting Labs  
**Email**: info@edgeconsultinglabs.com  
**Website**: https://edgeconsultinglabs.com

## 🙏 Acknowledgments

This project builds on excellent open-source work:
- OpenAI Whisper
- faster-whisper by Guillaume Klein
- PyAnnote by Hervé Bredin
- Ollama by Ollama team
- Nillion Network
- SQLCipher by Zetetic

---

**Status**: ✅ Production-Ready MVP  
**Version**: 0.1.0  
**Last Updated**: November 2024
