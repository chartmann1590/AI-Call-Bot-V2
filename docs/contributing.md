# Contributing to CallBot

Thank you for your interest in contributing to CallBot! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Docker (optional, for testing)
- Basic knowledge of Flask, SIP, and AI technologies

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/callbot.git
   cd callbot
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Setup Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/amazing-feature
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Follow the coding standards below
- Add tests for new features
- Update documentation as needed
- Keep commits atomic and well-described

### 3. Test Your Changes

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_sip_client.py

# Run with coverage
python -m pytest --cov=src tests/

# Run linting
flake8 src/
black src/
isort src/
```

### 4. Submit a Pull Request

1. Push your branch to your fork
2. Create a Pull Request against the main branch
3. Fill out the PR template
4. Wait for review and address feedback

## Coding Standards

### Python Code Style

We follow PEP 8 with some modifications:

```python
# Good
def process_call(call_id: str, transcript: str) -> dict:
    """Process a call with the given transcript.
    
    Args:
        call_id: The unique identifier for the call
        transcript: The speech transcript to process
        
    Returns:
        A dictionary containing the processed call data
    """
    result = {
        'call_id': call_id,
        'transcript': transcript,
        'processed_at': datetime.utcnow()
    }
    return result

# Bad
def processCall(callId,transcript):
    result={'call_id':callId,'transcript':transcript}
    return result
```

### Documentation

- Use docstrings for all functions and classes
- Follow Google docstring format
- Include type hints
- Update README and docs for new features

### Testing

- Write tests for all new functionality
- Aim for at least 80% code coverage
- Use descriptive test names
- Mock external dependencies

```python
def test_sip_client_registration():
    """Test that SIP client can register successfully."""
    client = SIPClient("test.com", "user", "pass")
    assert client.register() is True
```

### Commit Messages

Use conventional commit format:

```
feat: add new TTS engine support
fix: resolve SIP registration timeout issue
docs: update installation instructions
test: add unit tests for call processing
refactor: improve error handling in whisper module
```

## Project Structure

```
callbot/
├── src/                    # Source code
│   ├── __init__.py
│   ├── app.py             # Main Flask application
│   ├── config.py          # Configuration management
│   ├── models.py          # Database models
│   ├── sip_client.py      # SIP/VoIP client
│   ├── whisper_transcriber.py # Speech transcription
│   ├── ollama_client.py   # AI integration
│   └── tts_engines.py     # Text-to-speech engines
├── tests/                 # Test files
│   ├── __init__.py
│   ├── test_app.py
│   ├── test_sip_client.py
│   └── test_whisper.py
├── docs/                  # Documentation
├── templates/             # HTML templates
├── static/               # Static assets
└── requirements.txt      # Dependencies
```

## Areas for Contribution

### High Priority

- **Bug Fixes**: Fix issues reported in GitHub issues
- **Documentation**: Improve existing docs or add new ones
- **Tests**: Add missing test coverage
- **Security**: Report and fix security vulnerabilities

### Medium Priority

- **New TTS Engines**: Add support for additional TTS engines
- **AI Model Integration**: Support for additional AI models
- **Web Interface**: Improve UI/UX features
- **Performance**: Optimize existing functionality

### Low Priority

- **New Features**: Propose and implement new features
- **Translations**: Add multi-language support
- **Mobile App**: Create mobile companion app
- **Integrations**: Connect with CRM systems

## Testing Guidelines

### Unit Tests

```python
import pytest
from src.sip_client import SIPClient

class TestSIPClient:
    def test_registration_success(self):
        """Test successful SIP registration."""
        client = SIPClient("test.com", "user", "pass")
        assert client.register() is True
    
    def test_registration_failure(self):
        """Test failed SIP registration."""
        client = SIPClient("invalid.com", "user", "pass")
        assert client.register() is False
```

### Integration Tests

```python
def test_full_call_flow():
    """Test complete call handling flow."""
    # Setup
    app = create_test_app()
    client = app.test_client()
    
    # Simulate incoming call
    response = client.post('/api/call', json={
        'caller_id': '+1234567890',
        'audio_data': b'fake_audio_data'
    })
    
    # Verify response
    assert response.status_code == 200
    assert 'call_id' in response.json
```

### Performance Tests

```python
def test_transcription_performance():
    """Test that transcription completes within time limit."""
    import time
    
    start_time = time.time()
    result = transcribe_audio(test_audio_file)
    duration = time.time() - start_time
    
    assert duration < 5.0  # Should complete within 5 seconds
    assert result is not None
```

## Code Review Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] No sensitive data in commits
- [ ] Commit messages are descriptive

### Review Checklist

- [ ] Code is readable and well-documented
- [ ] Tests are comprehensive
- [ ] No security vulnerabilities
- [ ] Performance impact is acceptable
- [ ] Backward compatibility maintained

## Reporting Issues

### Bug Reports

Use the bug report template and include:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: Detailed steps to reproduce
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python version, dependencies
- **Logs**: Relevant error messages and logs

### Feature Requests

Include:

- **Description**: What the feature should do
- **Use Case**: Why this feature is needed
- **Implementation Ideas**: How it might be implemented
- **Priority**: High/Medium/Low priority

## Security

### Reporting Security Issues

- **DO NOT** create public issues for security vulnerabilities
- Email security@callbot.com (if applicable)
- Include detailed description and steps to reproduce
- Allow time for response before public disclosure

### Security Guidelines

- Never commit secrets or credentials
- Use environment variables for configuration
- Validate all user inputs
- Follow secure coding practices

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):

- **Major**: Breaking changes
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes, backward compatible

### Release Checklist

- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Changelog is updated
- [ ] Version number is incremented
- [ ] Release notes are written
- [ ] Docker images are built and tested

## Community Guidelines

### Be Respectful

- Be kind and respectful in all interactions
- Welcome newcomers and help them learn
- Give constructive feedback
- Respect different opinions and approaches

### Communication

- Use clear, concise language
- Ask questions when unsure
- Provide context when reporting issues
- Be patient with responses

### Recognition

Contributors will be recognized in:

- Project README
- Release notes
- Contributor hall of fame
- GitHub contributors page

## Getting Help

### Resources

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Search existing issues for similar problems
- **Discussions**: Use GitHub Discussions for questions
- **Code**: Review existing code for examples

### Contact

- **General Questions**: GitHub Discussions
- **Bug Reports**: GitHub Issues
- **Feature Requests**: GitHub Issues
- **Security Issues**: Email security@callbot.com

## License

By contributing to CallBot, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to CallBot! 🚀 