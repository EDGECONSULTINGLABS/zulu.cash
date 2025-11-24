# ZULU MPC Agent

**Privacy-Preserving Voice AI Agent with Multi-Party Computation**

ZULU is a local-first AI agent that transcribes, analyzes, and summarizes voice calls while maintaining strict privacy through encrypted local storage and optional MPC-based feature analysis.

## 🌟 Key Features

### 🔒 Privacy-First Architecture
- **Local Processing**: All transcription and analysis happens on your device
- **Encrypted Storage**: SQLCipher database with AES-256 encryption
- **MPC Integration**: Optional Nillion network for privacy-preserving computation
- **No Cloud Dependencies**: Works completely offline (except optional MPC)

### 🎯 Core Capabilities
- **Whisper Transcription**: State-of-the-art speech recognition using faster-whisper
- **Speaker Diarization**: Identify and label different speakers (PyAnnote, WhisperX)
- **LLM Summarization**: Local Ollama-powered call summaries with action items
- **Feature Extraction**: Generate embeddings for semantic search and analysis
- **MPC Computation**: Secret-share features for confidential computation

### 🛡️ Security & Privacy
- No user data leaves your device (local mode)
- Speaker anonymization (SPK_1, SPK_2, etc.)
- Automatic PII detection and removal
- Optional audio file deletion after processing
- Cryptographic feature hashing for verification

## 📋 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         ZULU Agent                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Whisper   │───▶│ Diarization  │───▶│   Ollama     │   │
│  │ (Local GPU) │    │  (PyAnnote)  │    │  (Summary)   │   │
│  └─────────────┘    └──────────────┘    └──────────────┘   │
│         │                    │                    │          │
│         └────────────────────┼────────────────────┘          │
│                              ▼                               │
│                    ┌──────────────────┐                      │
│                    │   SQLCipher DB   │                      │
│                    │  (Encrypted)     │                      │
│                    └──────────────────┘                      │
│                              │                               │
│                              ▼                               │
│                    ┌──────────────────┐                      │
│                    │  Embeddings      │                      │
│                    │  (Local Model)   │                      │
│                    └──────────────────┘                      │
│                              │                               │
│         ┌────────────────────┴────────────────────┐         │
│         ▼                                          ▼         │
│  ┌──────────────┐                         ┌──────────────┐  │
│  │ Local Only   │                         │   Nillion    │  │
│  │   Storage    │                         │  MPC Network │  │
│  └──────────────┘                         └──────────────┘  │
│                                            (Optional)        │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.9+
python --version

# Ollama (for LLM summarization)
ollama serve
ollama pull llama3.1:8b

# CUDA (optional, for GPU acceleration)
nvidia-smi
```

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/zulu-mpc-agent.git
cd zulu-mpc-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .
```

### Configuration

```bash
# Copy environment template
cp .env.template .env

# Generate encryption key
python -c "import secrets; print(secrets.token_hex(32))"

# Add to .env file
echo "ZULU_DB_KEY=your_generated_key_here" >> .env
```

### Initialize

```bash
# Initialize directories and check setup
zulu init
```

### Process Your First Call

```bash
# Process an audio file
zulu process path/to/call.wav --title "Team Standup"

# List all sessions
zulu list

# Show detailed session info
zulu show <session_id>
```

## 📖 Usage Guide

### Command Line Interface

```bash
# Process a call
zulu process recording.mp3 \
  --title "Product Review Meeting" \
  --language en

# List recent sessions
zulu list -n 20

# Show session details
zulu show abc123def456

# Delete a session
zulu delete abc123def456 --confirm

# Check system health
zulu health
```

### Python API

```python
from agent_core import WhisperDiarizationAgent, load_config

# Load configuration
config = load_config()

# Initialize agent
agent = WhisperDiarizationAgent(
    db_path="./data/zulu_agent.db",
    whisper_config=config.whisper.model_dump(),
    diarization_config=config.diarization.model_dump(),
    ollama_config=config.ollama.model_dump(),
    embeddings_config=config.embeddings.model_dump(),
)

# Process a call
session_id = agent.process_call(
    audio_path="meeting.wav",
    meta={"title": "Team Meeting", "language": "en"}
)

# Get summary
summary = agent.get_session_summary(session_id)
print(summary['session']['summary'])

# List action items
for item in summary['action_items']:
    print(f"- [{item['owner_speaker']}] {item['item']}")
```

## ⚙️ Configuration

Edit `config/default.yaml` to customize:

### Whisper Settings
```yaml
whisper:
  model_size: "medium"  # tiny, base, small, medium, large-v2, large-v3
  device: "auto"        # auto, cuda, cpu
  compute_type: "auto"  # auto, float16, int8
  language: "en"
```

### Diarization
```yaml
diarization:
  enabled: true
  backend: "simple"     # simple, pyannote, whisperx
  min_speakers: 1
  max_speakers: 10
```

### Ollama LLM
```yaml
ollama:
  base_url: "http://localhost:11434"
  model: "llama3.1:8b"
  temperature: 0.1
```

### Nillion MPC (Optional)
```yaml
nillion:
  enabled: false        # Enable for MPC features
  network_url: "https://nillion-testnet.example.com"
  api_key_env: "NILLION_API_KEY"
```

## 🔐 Privacy & Security

### What Stays Local
- ✅ Audio files (optionally deleted after processing)
- ✅ Full transcripts with timestamps
- ✅ Speaker utterances
- ✅ Call summaries and action items
- ✅ Raw feature vectors

### What Goes to MPC (Optional)
- ❌ NO raw transcripts
- ❌ NO audio files
- ❌ NO speaker identities
- ✅ Only: Anonymized feature vectors (embeddings)
- ✅ Returns: Scalar scores and cluster IDs

### Encryption
- Database: AES-256 via SQLCipher
- Key derivation: PBKDF2-HMAC-SHA512 (600k iterations)
- Feature hashing: SHA-256
- Secret sharing: Nillion's MPC protocol

## 🧪 Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
# Format code
black agent_core/ cli.py

# Type checking
mypy agent_core/

# Linting
ruff check agent_core/
```

## 📊 Database Schema

```sql
sessions          -- Call metadata and summaries
  ├── utterances  -- Speaker segments with text
  ├── action_items -- Extracted tasks
  ├── decisions   -- Key decisions made
  └── mpc_feature_index -- MPC feature mappings
```

## 🔧 Troubleshooting

### Ollama Connection Error
```bash
# Ensure Ollama is running
ollama serve

# Pull required model
ollama pull llama3.1:8b
```

### CUDA Out of Memory
```yaml
# Use smaller model or CPU
whisper:
  model_size: "small"
  device: "cpu"
```

### Diarization Not Working
```bash
# For PyAnnote, you need HuggingFace token
export HF_TOKEN=your_token_here

# Or use simple mode (alternating speakers)
diarization:
  backend: "simple"
```

## 🎯 Roadmap

- [x] Core transcription pipeline
- [x] Local LLM summarization
- [x] Encrypted storage
- [x] Speaker diarization
- [x] Feature extraction
- [ ] Nillion MPC integration (SDK in development)
- [ ] Real-time transcription
- [ ] Web interface
- [ ] Multi-language support
- [ ] Custom LLM prompts
- [ ] Export to various formats

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📧 Contact

Built by [Edge Consulting Labs](https://edgeconsultinglabs.com)

- Email: info@edgeconsultinglabs.com
- Twitter: [@EdgeConsultingLabs](https://twitter.com/EdgeConsultingLabs)

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Optimized inference
- [PyAnnote](https://github.com/pyannote/pyannote-audio) - Speaker diarization
- [Ollama](https://ollama.ai/) - Local LLM inference
- [Nillion](https://nillion.com/) - MPC network
- [SQLCipher](https://www.zetetic.net/sqlcipher/) - Encrypted database

---

**Note**: This is an open-source project for privacy-preserving AI. Use responsibly and in compliance with applicable laws and regulations.
