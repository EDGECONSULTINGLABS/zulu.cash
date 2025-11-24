# Contributing to ZULU MPC Agent

Thank you for your interest in contributing to ZULU! This document provides guidelines and instructions for contributing.

## 🤝 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Prioritize privacy and security in all contributions

## 🎯 Ways to Contribute

### Bug Reports
- Use GitHub Issues
- Include system info (OS, Python version)
- Provide minimal reproducible example
- Include logs (with sensitive data removed)

### Feature Requests
- Open a GitHub Issue with "Feature Request" label
- Describe the use case
- Explain how it improves privacy/security
- Consider implementation complexity

### Code Contributions
- Fork the repository
- Create a feature branch
- Write tests for new functionality
- Update documentation
- Submit a pull request

## 🔧 Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/zulu-mpc-agent.git
cd zulu-mpc-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -r requirements.txt
pip install -e .

# Install development dependencies
pip install pytest pytest-cov black mypy ruff

# Run tests
make test

# Format code
make format

# Lint code
make lint
```

## 📝 Coding Standards

### Python Style
- Follow PEP 8
- Use Black for formatting (line length: 88)
- Use type hints where possible
- Write docstrings for all public functions

### Code Quality
- Maintain test coverage above 80%
- No unused imports or variables
- Handle errors gracefully with logging
- Avoid sensitive data in logs

### Git Commits
- Use descriptive commit messages
- Reference issues in commits
- Keep commits focused and atomic

Example:
```
feat: Add real-time transcription support (#123)

- Implement streaming Whisper transcription
- Add WebSocket server for real-time updates
- Update docs with streaming examples

Closes #123
```

## 🧪 Testing

### Running Tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=agent_core --cov-report=html

# Specific test
pytest tests/test_pipeline.py::test_agent_initialization -v
```

### Writing Tests
- One test file per module
- Use descriptive test names
- Mock external dependencies
- Test edge cases and error handling

## 📚 Documentation

### Code Documentation
- Docstrings for all public APIs
- Type hints for function signatures
- Inline comments for complex logic

### User Documentation
- Update README.md for new features
- Add examples to `examples/` directory
- Update configuration guide

## 🔐 Security Considerations

### Privacy First
- Never log sensitive data
- Always use encrypted storage
- Minimize data retention
- Document privacy implications

### Code Review Focus
- Check for potential data leaks
- Verify encryption usage
- Review error messages for info disclosure
- Ensure proper key management

## 🚀 Pull Request Process

1. **Before Submitting**
   - Run tests locally
   - Format code with Black
   - Update relevant documentation
   - Add entry to CHANGELOG.md

2. **PR Template**
   ```markdown
   ## Description
   Brief description of changes
   
   ## Motivation
   Why is this change needed?
   
   ## Changes
   - Change 1
   - Change 2
   
   ## Testing
   How was this tested?
   
   ## Checklist
   - [ ] Tests pass
   - [ ] Code formatted
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated
   ```

3. **Review Process**
   - At least one approval required
   - Address review comments
   - Keep PR scope focused
   - Squash commits before merge

## 🐛 Debugging Tips

### Enable Debug Logging
```bash
zulu --verbose process audio.wav
```

### Check Component Health
```bash
zulu health
```

### Database Inspection
```bash
# Install sqlite3
sqlite3 data/zulu_agent.db

# List tables
.tables

# Query sessions
SELECT id, title, created_at FROM sessions LIMIT 5;
```

## 📦 Release Process

1. Update version in `setup.py` and `agent_core/__init__.py`
2. Update `CHANGELOG.md`
3. Create release branch: `release/v0.x.x`
4. Tag release: `git tag v0.x.x`
5. Push tag: `git push origin v0.x.x`
6. Create GitHub release
7. Merge to main

## 💡 Architecture Guidelines

### Core Principles
- **Local First**: All processing happens locally by default
- **Privacy Preserving**: Never expose raw data to network
- **Modular**: Each component should be independently testable
- **Configurable**: All behavior controlled via configuration

### Adding New Features

#### New Inference Model
1. Create module in `agent_core/inference/`
2. Implement base interface
3. Add configuration to `config.yaml`
4. Update pipeline integration
5. Add tests

#### New MPC Program
1. Define program specification
2. Implement client-side integration
3. Add feature extraction
4. Update schema if needed
5. Document privacy implications

## 🌟 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Invited to contributor discussions

## 📧 Questions?

- GitHub Discussions for general questions
- GitHub Issues for bug reports
- Email: dev@edgeconsultinglabs.com

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
