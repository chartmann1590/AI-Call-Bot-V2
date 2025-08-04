# Use Python 3.10 slim image
FROM python:3.10-slim

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
    # Audio processing dependencies
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavcodec-extra \
    # Additional dependencies for new audio libraries
    libpulse-dev \
    libjack-jackd2-dev \
    libsndfile1-dev \
    libsamplerate0-dev \
    libfftw3-dev \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
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