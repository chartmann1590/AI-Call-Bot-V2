# CallBot - AI-Powered Phone Assistant

A complete Flask web application that acts as a SIP/VoIP client, automatically answering calls, transcribing speech, generating AI responses, and playing them back to callers.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Development](#development)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Documentation](#documentation)

## Overview

CallBot is an intelligent phone assistant that automatically handles incoming calls using AI. It transcribes speech in real-time, generates contextual responses, and plays them back to callers using natural-sounding speech synthesis.

## Features

- **Automatic Call Handling**: Registers to SIP PBX and auto-answers incoming calls
- **Real-time Speech Transcription**: Uses Faster Whisper for accurate speech-to-text
- **AI-Powered Responses**: Integrates with Ollama for intelligent conversation
- **Text-to-Speech**: Multiple free TTS engines (Coqui TTS, eSpeak NG, pyttsx3)
- **Web Interface**: Modern dashboard for call history, settings, and monitoring
- **Docker Support**: Complete containerized deployment
- **Database Storage**: SQLite/PostgreSQL for call history and settings

## Architecture

CallBot integrates multiple technologies to create a seamless AI phone experience:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   SIP PBX   │◄──►│  CallBot    │◄──►│   Ollama    │
│             │    │             │    │   (AI)      │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                    ┌─────────────┐
                    │   Whisper   │
                    │(Transcribe) │
                    └─────────────┘
                           │
                    ┌─────────────┐
                    │    TTS      │
                    │(Speech)     │
                    └─────────────┘
```

### Components

- **SIP Client**: Handles VoIP communication with PBX systems
- **Whisper Transcriber**: Real-time speech-to-text conversion
- **Ollama Integration**: AI-powered response generation
- **TTS Engines**: Text-to-speech synthesis
- **Web Interface**: Dashboard for monitoring and configuration
- **Database**: Call history and settings storage

## Quick Start

### Production Deployment (Recommended)

For production deployment with SSL encryption:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/chartmann1590/AI-Call-Bot-V2.git
   cd A-Call-Bot-V2
   ```

2. **Run the deployment script**:
   ```bash
   ./deploy.sh
   ```

3. **Access the application**:
   - HTTPS: https://localhost (with SSL)
   - HTTP: http://localhost (redirects to HTTPS)

The deployment script automatically:
- Pulls latest changes from git
- Generates self-signed SSL certificates
- Configures nginx with SSL
- Builds and deploys Docker containers
- Starts all services

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/chartmann1590/AI-Call-Bot-V2.git
   cd A-Call-Bot-V2
   ```

2. **Configure environment variables**:
   ```bash
   cp docs/env.production.example .env
   # Edit .env with your settings
   ```

3. **Start the services**:
   ```bash
   docker-compose up -d
   ```

4. **Access the web interface**:
   - Open http://localhost:5000
   - Configure SIP settings in the Settings page
   - Test AI connection

### Manual Installation

1. **Install system dependencies**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-venv espeak-ng ffmpeg
   
   # macOS
   brew install espeak ffmpeg
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   export FLASK_ENV=development
   export SECRET_KEY=your-secret-key
   export SIP_DOMAIN=your-pbx-domain
   export SIP_USERNAME=your-extension
   export SIP_PASSWORD=your-password
   export OLLAMA_URL=http://localhost:11434
   ```

5. **Run the application**:
    ```bash
    python callbot.py
    # or
    python -m src.app
    # or
    python run.py
    ```

## Configuration

### SIP Settings

Configure your SIP PBX connection in the Settings page:

- **SIP Domain**: Your PBX server domain
- **SIP Username**: Your extension username
- **SIP Password**: Your extension password
- **SIP Port**: Usually 5060

### AI Configuration

- **Ollama URL**: Ollama server address (default: http://localhost:11434)
- **Ollama Model**: AI model to use (e.g., llama2, mistral, codellama)

### TTS Configuration

Choose from available TTS engines:

- **Coqui TTS**: High-quality neural TTS
- **eSpeak NG**: Fast, lightweight TTS
- **pyttsx3**: Cross-platform TTS

### Whisper Configuration

- **Model Size**: tiny, base, small, medium, large
- **Device**: cpu or cuda (GPU)

## Usage

### Web Interface

1. **Dashboard**: View system status and recent activity
2. **Conversations**: Browse call history with search and filtering
3. **Settings**: Configure all system parameters
4. **Admin**: Direct database access via Flask-Admin

### API Endpoints

- `GET /api/calls` - List calls with pagination
- `GET /api/active_calls` - Get currently active calls
- `GET /api/test_ollama` - Test Ollama connection
- `GET /api/audio/<call_id>` - Download call audio

### Call Flow

1. **Incoming Call**: SIP client auto-answers
2. **Audio Recording**: Captures caller audio in chunks
3. **Transcription**: Whisper processes audio to text
4. **AI Response**: Ollama generates intelligent response
5. **TTS Synthesis**: Converts response to speech
6. **Audio Playback**: Plays response to caller
7. **Call Logging**: Stores all data in database

## Development

### Project Structure

```
A-Call-Bot-V2/
├── src/                  # Python source code
│   ├── __init__.py
│   ├── app.py            # Main Flask application
│   ├── config.py         # Configuration management
│   ├── models.py         # Database models
│   ├── sip_client.py     # SIP/VoIP client
│   ├── whisper_transcriber.py # Speech transcription
│   ├── ollama_client.py  # AI integration
│   └── tts_engines.py    # Text-to-speech engines
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container definition
├── docker-compose.yml   # Multi-service setup
├── templates/           # HTML templates
│   ├── layout.html
│   ├── index.html
│   ├── conversations.html
│   └── settings.html
├── static/              # Static assets
│   ├── css/style.css
│   └── js/app.js
├── callbot.py           # Main entry point
├── run.py               # Development server entry point
├── start.sh             # Easy startup script
└── test_setup.py        # Installation test
```

### Adding New TTS Engines

1. Create a new class in `tts_engines.py`:
   ```python
   class NewTTSEngine(TTSEngine):
       def synthesize(self, text, output_path):
           # Implementation
           pass
   ```

2. Register in `TTSManager`:
   ```python
   self.engines['new_engine'] = NewTTSEngine()
   ```

### Adding New AI Models

1. Ensure the model is available in Ollama
2. Update the model selection in Settings
3. Test the connection via the web interface

## Troubleshooting

### Common Issues

1. **SIP Registration Fails**:
   - Check SIP credentials in Settings
   - Verify PBX server is reachable
   - Check firewall settings

2. **Whisper Not Working**:
   - Ensure sufficient RAM (2GB+ for base model)
   - Check CUDA installation for GPU support
   - Try smaller model size

3. **Ollama Connection Issues**:
   - Verify Ollama service is running
   - Check model is downloaded: `ollama list`
   - Test connection in Settings page

4. **TTS Not Working**:
   - Install system dependencies (espeak-ng)
   - Check TTS engine availability
   - Verify audio output directory permissions

### Logs

Check application logs:
```bash
# Docker
docker-compose logs callbot

# Manual installation
tail -f logs/app.log
```

### Performance Tuning

- **Whisper**: Use smaller models for faster transcription
- **Ollama**: Use quantized models for faster inference
- **TTS**: Use eSpeak for fastest synthesis
- **Database**: Use PostgreSQL for production

## Security

CallBot handles sensitive information including call data, audio recordings, and AI conversations. See our comprehensive [Security Guide](docs/security.md) for detailed security best practices.

### Key Security Features

- **Encrypted Communication**: HTTPS for web interface, SRTP for audio
- **Access Control**: User authentication and authorization
- **Data Protection**: Encrypted storage for sensitive data
- **Audit Logging**: Comprehensive security event logging
- **Compliance**: GDPR, HIPAA, and SOX compliance support

### Security Checklist

- [ ] Change default passwords and secrets
- [ ] Configure firewall and network security
- [ ] Set up HTTPS with valid certificates
- [ ] Implement access controls and monitoring
- [ ] Regular security updates and patches
- [ ] Backup and disaster recovery procedures

## Contributing

We welcome contributions to CallBot! Please see our [Contributing Guide](docs/contributing.md) for detailed information.

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to the branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/chartmann1590/AI-Call-Bot-V2.git
cd A-Call-Bot-V2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Start development server
python callbot.py
```

### Code Style

- Follow PEP 8 for Python code
- Use meaningful commit messages
- Add tests for new features
- Update documentation as needed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### License Summary

- **MIT License**: Permits commercial use, modification, distribution, and private use
- **Attribution**: Requires preservation of copyright and license notices
- **No Warranty**: Software is provided "as is" without warranty
- **Liability**: Authors are not liable for any damages

For full license terms, see [LICENSE](LICENSE).

## Deployment Scripts

The project includes several scripts for easy deployment and management:

### Production Deployment
- **`deploy.sh`**: Complete production deployment with SSL
  - Pulls latest git changes
  - Generates self-signed SSL certificates
  - Configures nginx with SSL encryption
  - Builds and deploys Docker containers
  - Starts all services

### Health Monitoring
- **`health_check.sh`**: Verifies deployment health
  - Checks container status
  - Validates SSL certificates
  - Tests web interface accessibility
  - Monitors resource usage
  - Reports any errors

### Backup and Recovery
- **`backup.sh`**: Creates application backups
  - Backs up Docker volumes
  - Archives configuration files
  - Creates backup manifests
  - Automatically cleans old backups

### Usage Examples
```bash
# Deploy to production
./deploy.sh

# Check system health
./health_check.sh

# Create backup
./backup.sh

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

For detailed deployment instructions, see [docs/deployment.md](docs/deployment.md).

## Documentation

Comprehensive documentation is available in the [docs/](docs/) directory:

- **[Deployment Guide](docs/deployment.md)** - Complete deployment instructions
- **[Installation Guide](docs/installation.md)** - Complete setup instructions
- **[Security Guide](docs/security.md)** - Security best practices
- **[API Reference](docs/api-reference.md)** - REST API documentation
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

### Quick Links

- [📚 Getting Started](docs/README.md#getting-started)
- [🔧 User Guide](docs/README.md#user-guide)
- [🛠️ Development](docs/README.md#development)
- [🔒 Security & Compliance](docs/README.md#security--compliance)

## Support

For issues and questions:

- **Documentation**: Check the [docs/](docs/) directory
- **Bug Reports**: Use the [GitHub issue tracker](https://github.com/chartmann1590/AI-Call-Bot-V2/issues)
- **Feature Requests**: Submit via [GitHub issues](https://github.com/chartmann1590/AI-Call-Bot-V2/issues)
- **Security Issues**: Email security@callbot.com (if applicable)
- **Community**: Join our [Discord server](https://discord.gg/callbot) (if applicable)

## Roadmap

- [ ] WebRTC support
- [ ] Multi-language support
- [ ] Advanced call routing
- [ ] Integration with CRM systems
- [ ] Real-time call analytics
- [ ] Mobile app
- [ ] API rate limiting
- [ ] Advanced TTS voices 