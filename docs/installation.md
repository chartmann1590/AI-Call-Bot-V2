# Installation Guide

This guide covers all installation methods for CallBot, from quick Docker deployment to manual setup.

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.8 or higher
- **Memory**: 2GB RAM minimum (4GB recommended)
- **Storage**: 1GB free space minimum
- **Network**: Internet access for model downloads

### Required System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv espeak-ng ffmpeg
```

#### macOS
```bash
brew install espeak ffmpeg
```

#### Windows
- Install [eSpeak NG](http://espeak.sourceforge.net/download.html)
- Install [FFmpeg](https://ffmpeg.org/download.html)

## Installation Methods

### Method 1: Docker (Recommended)

The easiest way to get CallBot running is with Docker.

#### Quick Start
```bash
# Clone the repository
git clone https://github.com/your-org/callbot.git
cd callbot

# Start with Docker
docker-compose up -d

# Access the web interface
open http://localhost:5000
```

#### Manual Docker Setup
```bash
# Build the image
docker build -t callbot .

# Run with custom configuration
docker run -d \
  --name callbot \
  -p 5000:5000 \
  -p 5060:5060/udp \
  -e SIP_DOMAIN=your-pbx.com \
  -e SIP_USERNAME=1001 \
  -e SIP_PASSWORD=your-password \
  callbot
```

### Method 2: Python Virtual Environment

For development or custom deployments.

#### Step 1: Clone Repository
```bash
git clone https://github.com/your-org/callbot.git
cd callbot
```

#### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Configure Environment
```bash
cp env.example .env
# Edit .env with your settings
```

#### Step 5: Run Application
```bash
python callbot.py
```

### Method 3: System-wide Installation

For production servers.

#### Step 1: Install System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv espeak-ng ffmpeg

# Create callbot user
sudo useradd -m -s /bin/bash callbot
sudo usermod -aG audio callbot
```

#### Step 2: Install CallBot
```bash
sudo -u callbot git clone https://github.com/your-org/callbot.git /opt/callbot
cd /opt/callbot
sudo -u callbot python3 -m venv venv
sudo -u callbot venv/bin/pip install -r requirements.txt
```

#### Step 3: Create Systemd Service
```bash
sudo tee /etc/systemd/system/callbot.service << EOF
[Unit]
Description=CallBot AI Phone Assistant
After=network.target

[Service]
Type=simple
User=callbot
WorkingDirectory=/opt/callbot
Environment=PATH=/opt/callbot/venv/bin
ExecStart=/opt/callbot/venv/bin/python callbot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable callbot
sudo systemctl start callbot
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=sqlite:///callbot.db

# SIP Configuration
SIP_DOMAIN=your-pbx-domain.com
SIP_USERNAME=1001
SIP_PASSWORD=your-password
SIP_PORT=5060

# AI Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# TTS Configuration
TTS_ENGINE=coqui
TTS_VOICE=en_0

# Whisper Configuration
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=cpu
```

### Database Setup

CallBot uses SQLite by default. For production, consider PostgreSQL:

```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb callbot
sudo -u postgres createuser callbot

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://callbot:password@localhost/callbot
```

## Verification

### Test Installation

Run the startup script to verify everything works:

```bash
./start.sh test
```

### Check Services

#### Docker
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f callbot
```

#### System Service
```bash
# Check service status
sudo systemctl status callbot

# View logs
sudo journalctl -u callbot -f
```

### Web Interface

1. Open http://localhost:5000
2. Navigate to Settings
3. Configure your SIP and AI settings
4. Test connections

## Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
sudo netstat -tulpn | grep :5000

# Kill the process or change port in .env
WEB_PORT=5001
```

#### Permission Denied
```bash
# Fix file permissions
sudo chown -R callbot:callbot /opt/callbot
sudo chmod +x /opt/callbot/callbot.py
```

#### Missing Dependencies
```bash
# Reinstall dependencies
pip install -r requirements.txt

# For system dependencies
sudo apt-get install espeak-ng ffmpeg
```

### Getting Help

- Check the [Troubleshooting Guide](troubleshooting.md)
- Review application logs
- Open an issue on GitHub

## Next Steps

After installation:

1. [Configure SIP settings](sip-configuration.md)
2. [Set up AI integration](ai-integration.md)
3. [Test your first call](quick-start.md)
4. [Review security settings](security.md) 