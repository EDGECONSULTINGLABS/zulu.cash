# Contributing to ZULU.CASH

Thank you for building privacy-first AI. 🛡️

ZULU is a local-first AI agent that respects user privacy. Every contribution should maintain this core principle.

---

## How to Contribute

### 1. Fork the Repository
```bash
git clone https://github.com/edgeconsultinglabs/zulu.cash.git
cd zulu.cash
```

### 2. Set Up Development Environment
```bash
# Install dependencies
cd agents/zulu-mpc-agent
pip install -r requirements.txt

# Set up encryption key
export ZULU_DB_KEY="your-development-key-here"

# Test the agent
python cli.py live-whisperx --model-size medium
```

### 3. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 4. Make Your Changes
- Follow existing code style
- Add tests for new features
- Update documentation

### 5. Test Locally
```bash
# Run the live agent
python cli.py live-whisperx --model-size medium

# Process a test file
python cli.py process test_audio.wav --title "Test"

# Check database integrity
python cli.py health
```

### 6. Submit a Pull Request
- Clear description of changes
- Reference any related issues
- Include screenshots/demos if applicable

---

## Code Guidelines

### ✅ DO:
- **Keep everything local-first** — no external API calls for core functionality
- **Preserve privacy** — never transmit raw text or audio to external services
- **Use dependency pinning** — specify exact versions in `requirements.txt`
- **Document new modules** — add README files to new directories
- **Follow existing patterns** — match the style of nearby code
- **Test on CPU** — ensure features work without GPU

### ❌ DON'T:
- Add cloud dependencies for core features
- Introduce telemetry or analytics
- Include large binary files in the repo
- Break backward compatibility without discussion
- Add dependencies without justification

---

## What We're Looking For

### High-Priority Contributions
- 🎤 **Audio processing improvements** (VAD, noise reduction)
- 🧠 **LLM integration** (support for new models)
- 🔍 **Search & retrieval** (semantic search, memory queries)
- 🔒 **Security enhancements** (encryption, key management)
- 📱 **Platform support** (macOS, Linux optimizations)
- 📚 **Documentation** (tutorials, examples, API docs)

### Feature Requests
- MPC computation improvements (Nillion integration)
- Zcash identity integration (Orchard receivers)
- Plugin/extension system
- Multi-language support
- Alternative embedding models
- Voice activity detection improvements

### Bug Reports
Please include:
- ZULU version (`git rev-parse HEAD`)
- Operating system (Windows, macOS, Linux)
- Python version (`python --version`)
- Error message or unexpected behavior
- Steps to reproduce
- Expected vs actual behavior

---

## Pull Request Expectations

### Required Checklist
- [ ] Code follows project style
- [ ] Tested locally using `cli.py`
- [ ] No large binary files added
- [ ] Documentation updated (if applicable)
- [ ] New features degrade gracefully without GPU
- [ ] No external API dependencies for core features
- [ ] Privacy principles maintained

### PR Description Template
```markdown
## What does this PR do?
Brief description of changes.

## Why is this needed?
Explain the problem this solves.

## How was it tested?
Steps you took to verify the changes.

## Screenshots (if applicable)
Visual proof of functionality.

## Related Issues
Closes #123
```

---

## Development Setup

### Requirements
- Python 3.10+
- FFmpeg installed
- Ollama running locally
- SQLCipher-enabled Python build
- 8GB+ RAM recommended

### Optional (for full features)
- GPU with CUDA (for faster inference)
- Hugging Face token (for diarization)
- Nillion testnet access (for MPC features)

### Environment Variables
```bash
export ZULU_DB_KEY="your-32-char-encryption-key"
export HF_TOKEN="your-huggingface-token"  # optional
export NILLION_ENDPOINT="https://nillion-testnet.example.com"  # optional
```

---

## Project Structure

```
zulu.cash/
├── agents/
│   └── zulu-mpc-agent/         # Main agent implementation
│       ├── cli.py              # Command-line interface
│       ├── live_whisperx_agent.py  # Live recording agent
│       └── agent_core/
│           ├── inference/      # ASR, diarization, embeddings
│           ├── llm/           # LLM clients, summarization
│           ├── memory/        # SQLCipher storage
│           └── mpc/           # Nillion MPC client
│
├── docs/                       # Documentation
├── examples/                   # Example integrations
└── scripts/                    # Utility scripts
```

---

## Testing

### Manual Testing
```bash
# Test live recording
python cli.py live-whisperx --model-size medium

# Test file processing
python cli.py process sample.wav --title "Test Meeting"

# Test memory retrieval
python cli.py show <session-id>
```

### Automated Testing
```bash
# Run test suite
python -m pytest tests/

# Run specific test
python -m pytest tests/test_summarizer.py
```

---

## Code Style

### Python
- Follow PEP 8
- Use type hints where practical
- Docstrings for public functions
- Meaningful variable names
- Comments for complex logic

### Example
```python
def summarize_call(
    segments: List[DiarizedSegment],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Summarize a call from diarized segments.
    
    Args:
        segments: List of diarized segments with text and timing
        metadata: Optional call metadata (duration, speakers, etc.)
        
    Returns:
        Summary dict with keys: summary, key_points, action_items, sentiment
    """
    # Implementation
    pass
```

---

## Documentation

### Adding Documentation
- Use clear, concise language
- Include code examples
- Add diagrams for complex concepts
- Keep docs up-to-date with code changes

### Documentation Locations
- **README.md** — Project overview, quick start
- **docs/** — Detailed technical documentation
- **Code comments** — Inline documentation
- **Docstrings** — Function/class documentation

---

## Community

### Communication
- **GitHub Issues** — Bug reports, feature requests
- **GitHub Discussions** — General questions, ideas
- **Pull Requests** — Code contributions

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers get started
- Maintain a welcoming environment

---

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- Project README

Thank you for helping build privacy-first AI! 🚀

---

## Questions?

- Open an issue on GitHub
- Check existing documentation in `docs/`
- Review example implementations in `examples/`

---

**Remember:** ZULU is sacred. Every contribution should maintain our privacy-first principles.

*Local AI • Encrypted Memory • Zero Surveillance*
