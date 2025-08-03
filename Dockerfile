# Use Python 3.9 slim image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
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
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

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