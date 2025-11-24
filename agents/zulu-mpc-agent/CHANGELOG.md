# Changelog

All notable changes to ZULU MPC Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Real-time transcription support
- Web interface for session management
- Custom LLM prompt templates
- Multi-language support improvements
- Advanced speaker identification
- Export to multiple formats (PDF, DOCX, etc.)

## [0.1.0] - 2024-11-24

### Added
- Initial release of ZULU MPC Agent
- Whisper-based transcription using faster-whisper
- Speaker diarization (simple, PyAnnote support)
- Local LLM summarization with Ollama
- SQLCipher encrypted database storage
- Feature embedding extraction
- Nillion MPC integration framework (client-side ready)
- CLI interface for call processing
- Session management (list, show, delete)
- Action item and decision extraction
- Speaker anonymization
- Privacy-preserving architecture
- Comprehensive configuration system
- Docker support
- Full test suite
- Documentation and examples

### Security
- AES-256 encryption for local database
- PBKDF2-HMAC-SHA512 key derivation
- SHA-256 feature hashing
- Optional audio file cleanup
- No cloud dependencies in local mode
- PII detection framework

### Technical Details
- Python 3.9+ support
- CUDA acceleration support
- CPU fallback for all models
- Modular architecture
- Type hints throughout
- Comprehensive logging
- Error handling and recovery

## [0.0.1] - 2024-11-01

### Added
- Project structure
- Basic Whisper integration
- Proof of concept

---

## Version Numbering

- MAJOR version for incompatible API changes
- MINOR version for new functionality (backwards compatible)
- PATCH version for bug fixes (backwards compatible)

## Categories

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes
