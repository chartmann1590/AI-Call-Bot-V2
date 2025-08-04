# Use Python 3.9 slim image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies in a single RUN command to reduce layers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    git \
    wget \
    curl \
    espeak-ng \
    libespeak-ng-dev \
    portaudio19-dev \
    libasound2-dev \
    ffmpeg \
    # PJSIP dependencies - only available packages
    libspeex-dev \
    libspeexdsp-dev \
    libgsm1-dev \
    libsrtp2-dev \
    libsamplerate0-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavcodec-extra \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with PJSIP fallback
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt || \
    (echo "PJSIP pip install failed, trying alternative..." && \
     pip install --no-cache-dir pjsua2==2.12 || \
     (echo "Installing PJSIP from source with setup.py fix..." && \
      cd /tmp && \
      git clone https://github.com/pjsip/pjproject.git && \
      cd pjproject && \
      ./configure --enable-shared --disable-sound --disable-resample --disable-video --disable-opencore-amr --disable-g7221-codec --disable-gsm-codec && \
      make dep && make && \
      cd pjsip-apps/src/python && \
      # Fix the setup.py indentation issue by replacing tabs with spaces
      sed -i 's/\t/    /g' setup.py && \
      # Also fix any other potential indentation issues
      sed -i 's/^    /\t/g' setup.py && \
      sed -i 's/\t/    /g' setup.py && \
      python setup.py build && \
      python setup.py install && \
      cd /app && \
      rm -rf /tmp/pjproject)) || \
    (echo "All PJSIP installation methods failed, installing without PJSIP..." && \
     pip install --no-cache-dir -r requirements.txt --no-deps && \
     pip install --no-cache-dir Flask==2.3.3 Flask-SQLAlchemy==3.0.5 Flask-Admin==1.6.1 Werkzeug==2.3.7 faster-whisper==0.9.0 requests==2.31.0 python-dotenv==1.0.0 gunicorn==21.2.0 coqui-tts==0.20.0 espeak-ng==0.1.0 soundfile==0.12.1 numpy==1.24.3 librosa==0.10.1 pydub==0.25.1 redis==5.0.1 celery==5.3.4) && \
    pip cache purge

# Copy application code
COPY . .

# Ensure src directory is properly set up
RUN python -c "import src; print('src package imported successfully')"

# Create necessary directories
RUN mkdir -p audio_output logs

# Create non-root user
RUN useradd -m -u 1000 callbot && \
    chown -R callbot:callbot /app

# Switch to non-root user
USER callbot

# Expose ports
EXPOSE 5000 5060

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application
CMD ["python", "callbot.py"] 