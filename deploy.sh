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
}

# Pull latest changes from git
pull_latest_changes() {
    print_status "Pulling latest changes from git..."
    
    if [ ! -d ".git" ]; then
        print_error "Not a git repository. Please clone the repository first."
        exit 1
    fi
    
    git fetch origin
    git reset --hard origin/main  # or origin/master depending on your default branch
    
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
      - OLLAMA_URL=http://ollama:11434
      - OLLAMA_MODEL=\${OLLAMA_MODEL:-llama2}
      - TTS_ENGINE=\${TTS_ENGINE:-coqui}
      - WHISPER_MODEL_SIZE=\${WHISPER_MODEL_SIZE:-base}
      - WHISPER_DEVICE=\${WHISPER_DEVICE:-cpu}
    volumes:
      - ./audio_output:/app/audio_output
      - ./logs:/app/logs
      - callbot_data:/app/data
    depends_on:
      - ollama
      - redis
    restart: unless-stopped
    networks:
      - callbot-network
    expose:
      - "5000"

  # Ollama AI service
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

# Build and deploy the application
deploy_application() {
    print_status "Building and deploying the application..."
    
    # Stop existing containers
    print_status "Stopping existing containers..."
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml down || true
    
    # Build and start the application
    print_status "Building Docker images..."
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml build --no-cache
    
    print_status "Starting services..."
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check if services are running
    print_status "Checking service status..."
    $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml ps
    
    print_success "Application deployed successfully!"
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
    echo "  - Ollama AI: http://localhost:11434"
    echo "  - Redis: localhost:6379"
    echo
    echo "SSL Certificate:"
    echo "  - Certificate: $SSL_DIR/cert.crt"
    echo "  - Private Key: $SSL_DIR/private.key"
    echo "  - Valid for: $CERT_VALIDITY_DAYS days"
    echo
    echo "Useful commands:"
    echo "  - View logs: $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml logs -f"
    echo "  - Stop services: $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml down"
    echo "  - Restart services: $DOCKER_COMPOSE_CMD -f docker-compose.prod.yml restart"
    echo
    print_warning "Note: This uses a self-signed certificate. Browsers will show a security warning."
    print_warning "For production, replace with a proper SSL certificate from a trusted CA."
    echo
}

# Main deployment function
main() {
    echo "=========================================="
    echo "    A-Call-Bot-V2 Deployment Script"
    echo "=========================================="
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Pull latest changes
    pull_latest_changes
    
    # Generate SSL certificate
    generate_ssl_certificate
    
    # Create nginx configuration
    create_nginx_config
    
    # Update docker-compose for production
    update_docker_compose
    
    # Deploy the application
    deploy_application
    
    # Show deployment information
    show_deployment_info
}

# Run the main function
main "$@" 