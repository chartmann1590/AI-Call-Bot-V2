#!/bin/bash

# A-Call-Bot-V2 Deploy Script
# This script pulls the latest code, sets up SSL certificates, and deploys the application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="localhost"  # Change this to your domain
SSL_DIR="./ssl"
NGINX_CONF_DIR="./nginx"
CERT_VALIDITY_DAYS=365

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to determine docker compose command
get_docker_compose_cmd() {
    if command_exists "docker"; then
        # Check if docker compose (V2) is available
        if docker compose version >/dev/null 2>&1; then
            echo "docker compose"
        elif command_exists "docker-compose"; then
            echo "docker-compose"
        else
            print_error "Neither 'docker compose' nor 'docker-compose' is available"
            exit 1
        fi
    else
        print_error "Docker is not installed"
        exit 1
    fi
}

# Check Docker daemon settings
check_docker_settings() {
    print_status "Checking Docker daemon settings..."
    
    # Check if BuildKit is available
    if docker info | grep -q "BuildKit"; then
        print_success "BuildKit is available for optimized builds"
    else
        print_warning "BuildKit not detected - builds may use more disk space"
    fi
    
    # Check Docker daemon memory (if on macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_status "On macOS - consider increasing Docker Desktop memory to 8GB+"
        print_status "Go to Docker Desktop > Settings > Resources > Advanced"
    fi
    
    # Check available Docker disk space
    local docker_space=$(docker system df | grep "Total Space" | awk '{print $3}')
    if [ -n "$docker_space" ]; then
        print_status "Docker disk usage: $docker_space"
    fi
}

# Configure Ollama deployment
configure_ollama_deployment() {
    print_status "Configuring Ollama deployment..."
    
    echo
    echo "Ollama Deployment Options:"
    echo "1. Use remote Ollama (recommended for production)"
    echo "2. Use local Ollama (requires more resources)"
    echo "3. Skip Ollama configuration"
    echo
    
    read -p "Choose an option (1-3): " ollama_choice
    
    case $ollama_choice in
        1)
            print_status "Configuring remote Ollama..."
            
            read -p "Enter your remote Ollama URL (e.g., https://your-ollama-server.com:11434): " ollama_url
            
            if [ -z "$ollama_url" ]; then
                print_error "Ollama URL cannot be empty"
                exit 1
            fi
            
            read -p "Enter the model name (default: llama2): " ollama_model
            ollama_model=${ollama_model:-llama2}
            
            # Set environment variables
            export OLLAMA_URL="$ollama_url"
            export OLLAMA_MODEL="$ollama_model"
            
            print_success "Remote Ollama configured:"
            print_success "  URL: $ollama_url"
            print_success "  Model: $ollama_model"
            print_success "  Deployment: docker-compose up -d (without local Ollama)"
            ;;
            
        2)
            print_status "Configuring local Ollama..."
            
            read -p "Enter the model name (default: llama2): " ollama_model
            ollama_model=${ollama_model:-llama2}
            
            # Set environment variables for local Ollama
            export OLLAMA_URL="http://ollama:11434"
            export OLLAMA_MODEL="$ollama_model"
            
            print_success "Local Ollama configured:"
            print_success "  Model: $ollama_model"
            print_success "  Deployment: docker-compose --profile local-ollama up -d"
            ;;
            
        3)
            print_status "Skipping Ollama configuration"
            print_warning "You'll need to configure Ollama manually later"
            ;;
            
        *)
            print_error "Invalid option"
            exit 1
            ;;
    esac
}

# Check Python version compatibility
check_python_compatibility() {
    print_status "Checking Python version compatibility..."
    
    # Check if we're using Python 3.9 in Docker
    if grep -q "FROM python:3.9" Dockerfile; then
        print_warning "Detected Python 3.9 in Dockerfile"
        print_warning "The TTS package requires Python 3.10+ for compatibility"
        
        echo
        echo "Python Version Compatibility Options:"
        echo "1. Upgrade to Python 3.10+ (recommended)"
        echo "2. Use alternative TTS engines (Python 3.9 compatible)"
        echo "3. Continue with current setup (may fail)"
        echo
        
        read -p "Choose an option (1-3): " python_choice
        
        case $python_choice in
            1)
                print_status "Upgrading to Python 3.10..."
                
                # Update Dockerfile
                sed -i.bak 's/FROM python:3.9/FROM python:3.10/g' Dockerfile
                sed -i.bak 's/FROM python:3.9/FROM python:3.10/g' Dockerfile.optimized
                
                # Update Python path in Dockerfile.optimized
                sed -i.bak 's/python3.9\/site-packages/python3.10\/site-packages/g' Dockerfile.optimized
                
                print_success "Dockerfiles updated to Python 3.10"
                print_success "This allows full TTS functionality including Coqui TTS"
                ;;
                
            2)
                print_status "Using alternative TTS engines..."
                
                # Use the Python 3.9 compatible requirements
                if [ -f "requirements-python39.txt" ]; then
                    cp requirements-python39.txt requirements.txt
                    print_success "Updated requirements.txt to use alternative TTS engines"
                    print_warning "This excludes Coqui TTS but keeps pyttsx3 and espeak-ng"
                else
                    print_error "requirements-python39.txt not found"
                    exit 1
                fi
                ;;
                
            3)
                print_warning "Continuing with Python 3.9 - build may fail"
                print_warning "If build fails, run: ./fix-python-version.sh"
                ;;
                
            *)
                print_error "Invalid option"
                exit 1
                ;;
        esac
    else
        print_success "Python version compatibility check passed"
    fi
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_deps=()
    
    if ! command_exists docker; then
        missing_deps+=("docker")
    fi
    
    # Check for either docker-compose or docker compose
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    print_status "Using Docker Compose command: $DOCKER_COMPOSE_CMD"
    
    if ! command_exists openssl; then
        missing_deps+=("openssl")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        print_error "Please install the missing dependencies and try again."
        exit 1
    fi
    
    print_success "All prerequisites are installed"
    
    # Check Docker settings
    check_docker_settings
    
    # Check Python version compatibility
    check_python_compatibility
    
    # Ensure fix script is executable
    if [ -f "fix-python-version.sh" ]; then
        chmod +x fix-python-version.sh
        print_status "Fix script is ready: ./fix-python-version.sh"
    fi
}

# Pull latest changes from git
pull_latest_changes() {
    print_status "Pulling latest changes from git..."
    
    if [ ! -d ".git" ]; then
        print_error "Not a git repository. Please clone the repository first."
        exit 1
    fi
    
    # Stash any local changes to avoid conflicts
    print_status "Stashing any local changes..."
    git stash || true
    
    # Fetch all changes from remote
    print_status "Fetching latest changes from remote..."
    git fetch --all
    
    # Get the current branch name
    CURRENT_BRANCH=$(git branch --show-current)
    print_status "Current branch: $CURRENT_BRANCH"
    
    # Reset to match the remote branch exactly
    print_status "Resetting to match remote branch..."
    git reset --hard "origin/$CURRENT_BRANCH"
    
    # Clean any untracked files
    print_status "Cleaning untracked files..."
    git clean -fd
    
    print_success "Latest changes pulled successfully"
}

# Generate self-signed SSL certificate
generate_ssl_certificate() {
    print_status "Generating self-signed SSL certificate..."
    
    # Create SSL directory if it doesn't exist
    mkdir -p "$SSL_DIR"
    
    # Generate private key
    openssl genrsa -out "$SSL_DIR/private.key" 2048
    
    # Generate certificate signing request
    openssl req -new -key "$SSL_DIR/private.key" -out "$SSL_DIR/cert.csr" -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"
    
    # Generate self-signed certificate
    openssl x509 -req -in "$SSL_DIR/cert.csr" -signkey "$SSL_DIR/private.key" -out "$SSL_DIR/cert.crt" -days $CERT_VALIDITY_DAYS
    
    # Set proper permissions
    chmod 600 "$SSL_DIR/private.key"
    chmod 644 "$SSL_DIR/cert.crt"
    
    # Clean up CSR file
    rm "$SSL_DIR/cert.csr"
    
    print_success "SSL certificate generated successfully"
    print_warning "This is a self-signed certificate. Browsers will show a security warning."
}

# Create nginx configuration
create_nginx_config() {
    print_status "Creating nginx configuration..."
    
    mkdir -p "$NGINX_CONF_DIR"
    
    cat > "$NGINX_CONF_DIR/nginx.conf" << EOF
events {
    worker_connections 1024;
}

http {
    upstream callbot_backend {
        server callbot:5000;
    }
    
    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
    
    server {
        listen 80;
        server_name $DOMAIN;
        
        # Redirect HTTP to HTTPS
        return 301 https://\$server_name\$request_uri;
    }
    
    server {
        listen 443 ssl http2;
        server_name $DOMAIN;
        
        # SSL configuration
        ssl_certificate /etc/nginx/ssl/cert.crt;
        ssl_certificate_key /etc/nginx/ssl/private.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        
        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        
        # Client max body size
        client_max_body_size 10M;
        
        # Static files
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
        
        # API endpoints with rate limiting
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://callbot_backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }
        
        # WebSocket support for real-time features
        location /ws {
            proxy_pass http://callbot_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
        
        # Main application
        location / {
            proxy_pass http://callbot_backend;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }
    }
}
EOF
    
    print_success "Nginx configuration created successfully"
}

# Update docker-compose for production
update_docker_compose() {
    print_status "Updating docker-compose configuration for production..."
    
    # Create a production docker-compose file
    cat > "docker-compose.prod.yml" << EOF
version: '3.8'

services:
  # CallBot main application
  callbot:
    build: .
    container_name: callbot-app
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=\${SECRET_KEY:-your-secret-key-change-in-production}
      - DATABASE_URL=\${DATABASE_URL:-sqlite:///callbot.db}
      - SIP_DOMAIN=\${SIP_DOMAIN:-pbx.example.com}
      - SIP_USERNAME=\${SIP_USERNAME:-1001}
      - SIP_PASSWORD=\${SIP_PASSWORD:-password}
      # Ollama configuration - supports both remote and local
      - OLLAMA_URL=\${OLLAMA_URL:-http://ollama:11434}
      - OLLAMA_MODEL=\${OLLAMA_MODEL:-llama2}
      - TTS_ENGINE=\${TTS_ENGINE:-coqui}
      - WHISPER_MODEL_SIZE=\${WHISPER_MODEL_SIZE:-base}
      - WHISPER_DEVICE=\${WHISPER_DEVICE:-cpu}
    volumes:
      - ./audio_output:/app/audio_output
      - ./logs:/app/logs
      - callbot_data:/app/data
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - callbot-network
    expose:
      - "5000"

  # Ollama AI service (optional - for local Ollama)
  ollama:
    image: ollama/ollama:latest
    container_name: callbot-ollama
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    networks:
      - callbot-network
    expose:
      - "11434"
    profiles:
      - local-ollama

  # Redis for caching and background tasks
  redis:
    image: redis:7-alpine
    container_name: callbot-redis
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - callbot-network
    expose:
      - "6379"

  # Nginx reverse proxy with SSL
  nginx:
    image: nginx:alpine
    container_name: callbot-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - callbot
    restart: unless-stopped
    networks:
      - callbot-network

volumes:
  callbot_data:
    driver: local
  ollama_data:
    driver: local
  redis_data:
    driver: local

networks:
  callbot-network:
    driver: bridge
EOF
    
    print_success "Production docker-compose configuration created"
}

# Clean Docker system to free up space
clean_docker_system() {
    print_status "Cleaning Docker system to free up disk space..."
    
    # Clean up unused containers, networks, and images
    docker system prune -f || true
    
    # Clean up build cache
    docker builder prune -f || true
    
    # Clean up unused volumes (be careful with this in production)
    docker volume prune -f || true
    
    print_success "Docker system cleaned"
}

# Check available disk space
check_disk_space() {
    print_status "Checking available disk space..."
    
    # Get available disk space in GB
    local available_space=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    
    if [ "$available_space" -lt 5 ]; then
        print_warning "Low disk space detected: ${available_space}GB available"
        print_warning "Consider freeing up disk space before continuing"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Deployment cancelled by user"
            exit 1
        fi
    else
        print_success "Sufficient disk space available: ${available_space}GB"
    fi
}

# Show troubleshooting information
show_troubleshooting_info() {
    echo
    echo "=========================================="
    echo "         TROUBLESHOOTING GUIDE"
    echo "=========================================="
    echo
    echo "DEPLOYMENT OPTIONS:"
    echo "The script now offers three deployment types:"
    echo "1. Full Rebuild - Rebuilds everything from scratch (slowest)"
    echo "2. Fast Update - Uses existing images, only updates code (fastest)"
    echo "3. Smart Deploy - Automatically chooses based on requirements.txt changes"
    echo
    echo "PYTHON VERSION COMPATIBILITY ISSUES:"
    echo "If you see 'TypeError: unsupported operand type(s) for |':"
    echo "1. Run the fix script: ./fix-python-version.sh"
    echo "2. Or manually update Dockerfiles to Python 3.10"
    echo "3. Or use alternative TTS engines with requirements-python39.txt"
    echo
    echo "DOCKER BUILD FAILURES:"
    echo "If Docker build fails with 'No space left on device':"
    echo
    echo "1. Clean Docker system:"
    echo "   docker system prune -f"
    echo "   docker builder prune -f"
    echo
    echo "2. Check disk space:"
    echo "   df -h /"
    echo
    echo "3. Free up disk space:"
    echo "   - Remove old Docker images: docker image prune -a"
    echo "   - Remove unused volumes: docker volume prune"
    echo "   - Clean system cache: sudo apt-get clean (Ubuntu/Debian)"
    echo
    echo "4. Increase Docker Desktop resources (macOS):"
    echo "   - Go to Docker Desktop > Settings > Resources"
    echo "   - Increase memory limit to 8GB+"
    echo "   - Increase disk image size"
    echo
    echo "5. Use optimized Dockerfile:"
    echo "   - The Dockerfile has been optimized with --no-install-recommends"
    echo "   - Consider using multi-stage builds for complex applications"
    echo
    echo "6. Alternative build commands:"
    echo "   - Build with no cache: docker build --no-cache ."
    echo "   - Build with BuildKit: DOCKER_BUILDKIT=1 docker build ."
    echo
    echo "FAST UPDATE ISSUES:"
    echo "If fast update doesn't work as expected:"
    echo "1. Try a full rebuild to ensure all dependencies are up to date"
    echo "2. Check if requirements.txt has changed (requires full rebuild)"
    echo "3. Clear the .requirements_hash file to force a full rebuild"
    echo
    echo "TTS ENGINE ISSUES:"
    echo "If TTS engines fail to initialize:"
    echo "1. Check Python version compatibility"
    echo "2. Ensure required system dependencies are installed"
    echo "3. Try alternative TTS engines (pyttsx3, espeak-ng)"
    echo
}

# Build Docker images with retry logic
build_with_retry() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_status "Build attempt $attempt of $max_attempts..."
        
        if docker info | grep -q "BuildKit"; then
            print_status "Using BuildKit for optimized builds..."
            export DOCKER_BUILDKIT=1
            if $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml build --no-cache --build-arg BUILDKIT_INLINE_CACHE=1; then
                print_success "Build completed successfully on attempt $attempt"
                return 0
            fi
        else
            print_status "Using standard Docker build..."
            if $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml build --no-cache; then
                print_success "Build completed successfully on attempt $attempt"
                return 0
            fi
        fi
        
        print_warning "Build attempt $attempt failed"
        
        # Check for Python version related errors
        if $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml logs callbot 2>/dev/null | grep -q "TypeError: unsupported operand type(s) for |"; then
            print_error "Python version compatibility error detected!"
            print_error "The TTS package requires Python 3.10+ but you're using Python 3.9"
            echo
            echo "Quick fix options:"
            echo "1. Run: ./fix-python-version.sh"
            echo "2. Or manually:"
            echo "   - Option A: Update Dockerfiles to Python 3.10"
            echo "   - Option B: Use requirements-python39.txt"
            echo
            return 1
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            print_status "Cleaning Docker system and retrying..."
            clean_docker_system
            sleep 10
        fi
        
        attempt=$((attempt + 1))
    done
    
    print_error "All build attempts failed"
    return 1
}



# Display deployment information
show_deployment_info() {
    echo
    echo "=========================================="
    echo "           DEPLOYMENT COMPLETE"
    echo "=========================================="
    echo
    echo "Application URLs:"
    echo "  HTTP:  http://$DOMAIN (redirects to HTTPS)"
    echo "  HTTPS: https://$DOMAIN"
    echo
    echo "Services:"
    echo "  - CallBot App: http://localhost:5000"
    if [ "$OLLAMA_URL" = "http://ollama:11434" ]; then
        echo "  - Local Ollama AI: http://localhost:11434"
    else
        echo "  - Remote Ollama AI: $OLLAMA_URL"
    fi
    echo "  - Redis: localhost:6379"
    echo
    echo "SSL Certificate:"
    echo "  - Certificate: $SSL_DIR/cert.crt"
    echo "  - Private Key: $SSL_DIR/private.key"
    echo "  - Valid for: $CERT_VALIDITY_DAYS days"
    echo
    echo "Useful commands:"
    if [ "$OLLAMA_URL" = "http://ollama:11434" ]; then
        echo "  - View logs: $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml --profile local-ollama logs -f"
        echo "  - Stop services: $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml --profile local-ollama down"
        echo "  - Restart services: $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml --profile local-ollama restart"
    else
        echo "  - View logs: $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml logs -f"
        echo "  - Stop services: $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml down"
        echo "  - Restart services: $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml restart"
    fi
    echo
    print_warning "Note: This uses a self-signed certificate. Browsers will show a security warning."
    print_warning "For production, replace with a proper SSL certificate from a trusted CA."
    echo
    echo "Python Version Compatibility:"
    if grep -q "FROM python:3.10" Dockerfile; then
        print_success "Using Python 3.10 - Full TTS functionality available"
    else
        print_warning "Using Python 3.9 - Limited TTS functionality"
        print_warning "Run ./fix-python-version.sh to upgrade to Python 3.10"
    fi
    echo
}

# Check if requirements.txt has changed
check_requirements_changed() {
    print_status "Checking if requirements.txt has changed..."
    
    if [ ! -f ".requirements_hash" ]; then
        print_status "No previous requirements hash found - will do full rebuild"
        return 0  # Changed
    fi
    
    local current_hash=$(sha256sum requirements.txt | cut -d' ' -f1)
    local stored_hash=$(cat .requirements_hash 2>/dev/null || echo "")
    
    if [ "$current_hash" != "$stored_hash" ]; then
        print_warning "requirements.txt has changed - full rebuild required"
        return 0  # Changed
    else
        print_success "requirements.txt unchanged - can use fast update"
        return 1  # Not changed
    fi
}

# Save requirements hash
save_requirements_hash() {
    sha256sum requirements.txt > .requirements_hash
    print_status "Saved requirements hash for future comparisons"
}

# Fast update deployment
fast_update() {
    print_status "Performing fast update deployment..."
    
    # Stop existing containers
    print_status "Stopping existing containers..."
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml down || true
    
    # Pull latest changes
    pull_latest_changes
    
    # Start services with existing images (no rebuild)
    print_status "Starting services with existing images..."
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 15
    
    # Check if services are running
    print_status "Checking service status..."
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml ps
    
    print_success "Fast update completed successfully!"
}

# Full rebuild deployment
full_rebuild() {
    print_status "Performing full rebuild deployment..."
    
    # Check disk space first
    check_disk_space
    
    # Clean Docker system to free up space
    clean_docker_system
    
    # Stop existing containers
    print_status "Stopping existing containers..."
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml down || true
    
    # Build and start the application with retry logic
    print_status "Building Docker images with optimized settings..."
    
    if ! build_with_retry; then
        print_error "Failed to build Docker images after multiple attempts"
        print_error "Please check disk space and Docker configuration"
        exit 1
    fi
    
    print_status "Starting services..."
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check if services are running
    print_status "Checking service status..."
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml ps
    
    # Save requirements hash for future comparisons
    save_requirements_hash
    
    print_success "Full rebuild completed successfully!"
}

# Main deployment function
main() {
    echo "=========================================="
    echo "    A-Call-Bot-V2 Deployment Script"
    echo "=========================================="
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Check deployment type
    echo "Deployment Options:"
    echo "1. Full Rebuild (no cache, rebuilds everything)"
    echo "2. Fast Update (uses existing images, only updates code)"
    echo "3. Smart Deploy (automatically chooses based on changes)"
    echo
    
    read -p "Choose deployment type (1-3): " deploy_choice
    
    case $deploy_choice in
        1)
            print_status "Selected: Full Rebuild"
            DEPLOY_TYPE="full"
            ;;
        2)
            print_status "Selected: Fast Update"
            DEPLOY_TYPE="fast"
            ;;
        3)
            print_status "Selected: Smart Deploy"
            if check_requirements_changed; then
                print_status "Requirements changed - will do full rebuild"
                DEPLOY_TYPE="full"
            else
                print_status "No requirements changes - will do fast update"
                DEPLOY_TYPE="fast"
            fi
            ;;
        *)
            print_error "Invalid option"
            exit 1
            ;;
    esac
    
    # Configure Ollama deployment
    configure_ollama_deployment
    
    # Generate SSL certificate
    generate_ssl_certificate
    
    # Create nginx configuration
    create_nginx_config
    
    # Update docker-compose for production
    update_docker_compose
    
    # Deploy based on type
    if [ "$DEPLOY_TYPE" = "fast" ]; then
        fast_update
    else
        full_rebuild
    fi
    
    # Show deployment information
    show_deployment_info
}

# Run the main function
main "$@" 