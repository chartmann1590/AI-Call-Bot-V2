#!/bin/bash

# A-Call-Bot-V2 Complete Deployment Script with SIP Fix
# This script ensures your bot is REACHABLE and can receive calls

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="localhost"  # Change this to your domain if needed
SSL_DIR="./ssl"
NGINX_CONF_DIR="./nginx"
CERT_VALIDITY_DAYS=365
LOG_FILE="deployment.log"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a $LOG_FILE
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a $LOG_FILE
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a $LOG_FILE
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a $LOG_FILE
}

print_section() {
    echo -e "\n${CYAN}========================================${NC}" | tee -a $LOG_FILE
    echo -e "${CYAN}$1${NC}" | tee -a $LOG_FILE
    echo -e "${CYAN}========================================${NC}\n" | tee -a $LOG_FILE
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to determine docker compose command
get_docker_compose_cmd() {
    if command_exists "docker"; then
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

# Get host IP address
get_host_ip() {
    # Try multiple methods to get the host IP
    local host_ip=""
    
    # Method 1: Get default route IP
    host_ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K[^ ]+' || true)
    
    if [ -z "$host_ip" ]; then
        # Method 2: Get first non-loopback IP
        host_ip=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
    fi
    
    if [ -z "$host_ip" ]; then
        # Method 3: Use hostname
        host_ip=$(hostname -i 2>/dev/null | grep -v '127.0.0.1' | head -1 || true)
    fi
    
    if [ -z "$host_ip" ]; then
        host_ip="127.0.0.1"
        print_warning "Could not detect host IP, using localhost"
    fi
    
    echo "$host_ip"
}

# Check system requirements
check_system_requirements() {
    print_section "CHECKING SYSTEM REQUIREMENTS"
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_success "Operating System: Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        print_warning "Operating System: macOS (some features may vary)"
    else
        print_warning "Operating System: $OSTYPE (untested)"
    fi
    
    # Check memory
    local total_mem=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}' || echo "0")
    if [ "$total_mem" -lt 2048 ]; then
        print_warning "Low memory detected: ${total_mem}MB (minimum 2GB recommended)"
    else
        print_success "Memory: ${total_mem}MB"
    fi
    
    # Check disk space
    local available_space=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt 5 ]; then
        print_warning "Low disk space: ${available_space}GB available (minimum 5GB recommended)"
    else
        print_success "Disk space: ${available_space}GB available"
    fi
}

# Check prerequisites
check_prerequisites() {
    print_section "CHECKING PREREQUISITES"
    
    local missing_deps=()
    
    # Check Docker
    if ! command_exists docker; then
        missing_deps+=("docker")
    else
        local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+')
        print_success "Docker installed: version $docker_version"
    fi
    
    # Check Docker Compose
    DOCKER_COMPOSE_CMD=$(get_docker_compose_cmd)
    print_success "Docker Compose command: $DOCKER_COMPOSE_CMD"
    
    # Check other tools
    if ! command_exists openssl; then
        missing_deps+=("openssl")
    else
        print_success "OpenSSL installed"
    fi
    
    if ! command_exists git; then
        missing_deps+=("git")
    else
        print_success "Git installed"
    fi
    
    # Report missing dependencies
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        print_error "Please install the missing dependencies and try again."
        
        # Provide installation instructions
        echo
        print_status "Installation instructions:"
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            print_status "  sudo apt-get update && sudo apt-get install -y ${missing_deps[*]}"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            print_status "  brew install ${missing_deps[*]}"
        fi
        exit 1
    fi
    
    print_success "All prerequisites are installed"
}

# Check Docker daemon
check_docker_daemon() {
    print_section "CHECKING DOCKER DAEMON"
    
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running"
        print_status "Starting Docker daemon..."
        
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo systemctl start docker || true
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            open -a Docker || true
            sleep 5
        fi
        
        if ! docker info >/dev/null 2>&1; then
            print_error "Failed to start Docker daemon"
            exit 1
        fi
    fi
    
    print_success "Docker daemon is running"
    
    # Check Docker settings
    if docker info | grep -q "BuildKit"; then
        print_success "BuildKit is available for optimized builds"
        export DOCKER_BUILDKIT=1
    fi
}

# Setup environment configuration
setup_environment() {
    print_section "SETTING UP ENVIRONMENT"
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_warning ".env file not found, creating from template..."
        
        if [ -f "env.example" ]; then
            cp env.example .env
        else
            # Create a new .env file with defaults
            cat > .env << 'EOF'
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=sqlite:///callbot.db

# SIP Configuration - CHANGE THESE VALUES!
SIP_DOMAIN=your-pbx-server.com
SIP_USERNAME=9898
SIP_PASSWORD=your-sip-password
SIP_PORT=5060

# Network Configuration
DOCKER_HOST_NETWORK=true
DOCKER_NETWORK_MODE=host

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# TTS Configuration
TTS_ENGINE=espeak
TTS_VOICE=en-us

# Whisper Configuration
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=cpu

# Audio Configuration
AUDIO_SAMPLE_RATE=16000
AUDIO_CHUNK_DURATION=5
AUDIO_OUTPUT_DIR=audio_output

# Web Server Configuration
WEB_PORT=5000
WEB_HOST=0.0.0.0

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
EOF
        fi
        
        print_warning "Please edit .env file with your SIP settings!"
        print_warning "The bot WILL NOT WORK without correct SIP credentials!"
        
        # Interactive configuration
        echo
        read -p "Do you want to configure SIP settings now? (y/n): " configure_now
        if [[ "$configure_now" =~ ^[Yy]$ ]]; then
            configure_sip_interactive
        else
            print_error "You must configure SIP settings in .env before the bot can work!"
            print_status "Edit .env file and run this script again"
            exit 1
        fi
    else
        print_success ".env file exists"
        
        # Source environment variables
        source .env
        
        # Validate critical settings
        if [ "$SIP_DOMAIN" = "your-pbx-server.com" ] || [ -z "$SIP_DOMAIN" ]; then
            print_error "SIP_DOMAIN is not configured!"
            configure_sip_interactive
        fi
    fi
    
    # Get and display host IP
    HOST_IP=$(get_host_ip)
    print_success "Host IP detected: $HOST_IP"
    
    # Add host IP to environment
    echo "HOST_IP=$HOST_IP" >> .env
    
    # Ensure Docker host network mode is set
    if ! grep -q "DOCKER_HOST_NETWORK=true" .env; then
        echo "DOCKER_HOST_NETWORK=true" >> .env
        echo "DOCKER_NETWORK_MODE=host" >> .env
    fi
    
    print_success "Environment configuration complete"
}

# Interactive SIP configuration
configure_sip_interactive() {
    print_section "SIP CONFIGURATION"
    
    echo "Please enter your SIP/PBX settings:"
    echo
    
    read -p "SIP Domain (PBX server address): " sip_domain
    read -p "SIP Username (extension number, e.g., 9898): " sip_username
    read -s -p "SIP Password: " sip_password
    echo
    read -p "SIP Port (default 5060): " sip_port
    sip_port=${sip_port:-5060}
    
    # Update .env file
    sed -i.bak "s/SIP_DOMAIN=.*/SIP_DOMAIN=$sip_domain/" .env
    sed -i.bak "s/SIP_USERNAME=.*/SIP_USERNAME=$sip_username/" .env
    sed -i.bak "s/SIP_PASSWORD=.*/SIP_PASSWORD=$sip_password/" .env
    sed -i.bak "s/SIP_PORT=.*/SIP_PORT=$sip_port/" .env
    
    print_success "SIP configuration saved"
    
    # Reload environment
    source .env
}

# Configure Ollama
configure_ollama() {
    print_section "OLLAMA CONFIGURATION"
    
    echo "Choose Ollama deployment option:"
    echo "1. Use local Ollama (will be installed in Docker)"
    echo "2. Use remote Ollama server"
    echo "3. Skip Ollama (bot won't have AI responses)"
    echo
    
    read -p "Enter choice (1-3): " ollama_choice
    
    case $ollama_choice in
        1)
            print_status "Configuring local Ollama..."
            sed -i.bak "s|OLLAMA_URL=.*|OLLAMA_URL=http://localhost:11434|" .env
            USE_LOCAL_OLLAMA=true
            
            # Pull Ollama model
            print_status "Pulling Ollama model (this may take a while)..."
            docker pull ollama/ollama:latest || true
            ;;
        2)
            print_status "Configuring remote Ollama..."
            read -p "Enter Ollama server URL: " ollama_url
            sed -i.bak "s|OLLAMA_URL=.*|OLLAMA_URL=$ollama_url|" .env
            USE_LOCAL_OLLAMA=false
            ;;
        3)
            print_warning "Skipping Ollama - bot will have limited functionality"
            USE_LOCAL_OLLAMA=false
            ;;
        *)
            print_warning "Invalid choice, using default (local Ollama)"
            USE_LOCAL_OLLAMA=true
            ;;
    esac
}

# Clean Docker system
clean_docker_system() {
    print_section "CLEANING DOCKER SYSTEM"
    
    print_status "Stopping existing containers..."
    $DOCKER_COMPOSE_CMD down 2>/dev/null || true
    docker stop callbot-app 2>/dev/null || true
    docker stop callbot-ollama 2>/dev/null || true
    docker stop callbot-redis 2>/dev/null || true
    docker stop callbot-nginx 2>/dev/null || true
    
    print_status "Removing old containers..."
    docker rm callbot-app 2>/dev/null || true
    docker rm callbot-ollama 2>/dev/null || true
    docker rm callbot-redis 2>/dev/null || true
    docker rm callbot-nginx 2>/dev/null || true
    
    print_status "Cleaning Docker system..."
    docker system prune -f --volumes 2>/dev/null || true
    
    print_success "Docker system cleaned"
}

# Setup firewall rules
setup_firewall() {
    print_section "CONFIGURING FIREWALL"
    
    if command_exists ufw; then
        print_status "Configuring UFW firewall rules..."
        
        # SIP port
        sudo ufw allow 5070/udp comment 'CallBot SIP' 2>/dev/null || true
        
        # RTP ports for audio
        sudo ufw allow 10000:20000/udp comment 'CallBot RTP' 2>/dev/null || true
        
        # Web interface
        sudo ufw allow 5000/tcp comment 'CallBot Web' 2>/dev/null || true
        
        # HTTP/HTTPS if using nginx
        sudo ufw allow 80/tcp comment 'HTTP' 2>/dev/null || true
        sudo ufw allow 443/tcp comment 'HTTPS' 2>/dev/null || true
        
        print_success "Firewall rules configured"
    elif command_exists iptables; then
        print_status "Configuring iptables rules..."
        
        # Add iptables rules
        sudo iptables -A INPUT -p udp --dport 5070 -j ACCEPT 2>/dev/null || true
        sudo iptables -A INPUT -p udp --dport 10000:20000 -j ACCEPT 2>/dev/null || true
        sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT 2>/dev/null || true
        
        print_success "Firewall rules configured"
    else
        print_warning "No firewall detected, skipping firewall configuration"
        print_warning "Please manually open ports: 5070/udp, 10000-20000/udp, 5000/tcp"
    fi
}

# Create Docker Compose file
create_docker_compose() {
    print_section "CREATING DOCKER COMPOSE CONFIGURATION"
    
    # Create production docker-compose file with host networking
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # CallBot main application with HOST NETWORK for SIP
  callbot:
    build: 
      context: .
      dockerfile: Dockerfile
    container_name: callbot-app
    network_mode: "host"  # CRITICAL: Required for SIP to work properly
    env_file:
      - .env
    environment:
      - FLASK_ENV=production
      - DOCKER_HOST_NETWORK=true
      - DOCKER_NETWORK_MODE=host
    volumes:
      - ./audio_output:/app/audio_output
      - ./logs:/app/logs
      - ./src:/app/src:ro  # Mount source code
      - callbot_data:/app/data
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Optional: Local Ollama AI service
  ollama:
    image: ollama/ollama:latest
    container_name: callbot-ollama
    network_mode: "host"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    profiles:
      - local-ollama
    command: serve

  # Redis for caching
  redis:
    image: redis:7-alpine
    container_name: callbot-redis
    network_mode: "host"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --port 6379 --bind 127.0.0.1

volumes:
  callbot_data:
    driver: local
  ollama_data:
    driver: local
  redis_data:
    driver: local
EOF
    
    print_success "Docker Compose configuration created"
}

# Build Docker image
build_docker_image() {
    print_section "BUILDING DOCKER IMAGE"
    
    # Check if Dockerfile exists
    if [ ! -f "Dockerfile" ]; then
        print_error "Dockerfile not found!"
        exit 1
    fi
    
    # Ensure Python 3.10 is used (required for TTS)
    if grep -q "FROM python:3.9" Dockerfile; then
        print_warning "Updating Dockerfile to use Python 3.10..."
        sed -i.bak 's/FROM python:3.9/FROM python:3.10/g' Dockerfile
    fi
    
    print_status "Building Docker image (this may take several minutes)..."
    
    # Build with BuildKit if available
    if [ -n "${DOCKER_BUILDKIT}" ]; then
        $DOCKER_COMPOSE_CMD build --no-cache --progress=plain
    else
        $DOCKER_COMPOSE_CMD build --no-cache
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        print_status "Trying alternative build method..."
        docker build -t callbot-app . || exit 1
    fi
}

# Start services
start_services() {
    print_section "STARTING SERVICES"
    
    # Source environment to check Ollama setting
    source .env
    
    # Start services based on Ollama configuration
    if [ "$USE_LOCAL_OLLAMA" = true ]; then
        print_status "Starting CallBot with local Ollama..."
        $DOCKER_COMPOSE_CMD --profile local-ollama up -d
    else
        print_status "Starting CallBot without local Ollama..."
        $DOCKER_COMPOSE_CMD up -d
    fi
    
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check if services are running
    print_status "Checking service status..."
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    # Check if CallBot container is running
    if docker ps | grep -q "callbot-app"; then
        print_success "CallBot is running"
    else
        print_error "CallBot failed to start"
        print_status "Checking logs..."
        docker logs callbot-app --tail 50
        exit 1
    fi
}

# Verify SIP registration
verify_sip_registration() {
    print_section "VERIFYING SIP REGISTRATION"
    
    print_status "Checking SIP registration status..."
    sleep 5
    
    # Check logs for registration success
    if docker logs callbot-app 2>&1 | grep -q "REGISTRATION SUCCESSFUL"; then
        print_success "SIP registration successful!"
        
        # Show registration details
        docker logs callbot-app 2>&1 | grep -E "(Contact URI|Extension|REACHABLE)" | tail -5
        
        echo
        print_success "Your bot should now show as REACHABLE in your PBX!"
        print_success "SIP Contact: sip:${SIP_USERNAME}@${HOST_IP}:5070"
    else
        print_warning "SIP registration may still be in progress"
        print_status "Check the logs: docker logs -f callbot-app"
    fi
}

# Show deployment summary
show_deployment_summary() {
    print_section "DEPLOYMENT COMPLETE!"
    
    # Source environment for variables
    source .env
    
    echo -e "${GREEN}CallBot has been successfully deployed!${NC}"
    echo
    echo "Access Points:"
    echo "=============="
    echo -e "${CYAN}Web Interface:${NC} http://${HOST_IP}:5000"
    echo -e "${CYAN}SIP Extension:${NC} ${SIP_USERNAME}"
    echo -e "${CYAN}SIP Contact:${NC} sip:${SIP_USERNAME}@${HOST_IP}:5070"
    echo
    echo "Quick Commands:"
    echo "=============="
    echo -e "${YELLOW}View logs:${NC} docker logs -f callbot-app"
    echo -e "${YELLOW}Stop services:${NC} docker-compose down"
    echo -e "${YELLOW}Restart services:${NC} docker-compose restart"
    echo -e "${YELLOW}Check SIP status:${NC} docker logs callbot-app | grep -E '(REGISTER|REACHABLE)'"
    echo
    echo "Testing:"
    echo "========"
    echo "1. Check your PBX - Extension ${SIP_USERNAME} should show as 'OK' or 'Reachable'"
    echo "2. Call extension ${SIP_USERNAME} from another phone"
    echo "3. The bot should answer immediately (no voicemail)"
    echo "4. Check logs to see call handling: docker logs -f callbot-app"
    echo
    echo "Troubleshooting:"
    echo "==============="
    echo "If extension shows as 'Unreachable':"
    echo "  1. Check firewall: ports 5070/udp and 10000-20000/udp must be open"
    echo "  2. Verify PBX can reach ${HOST_IP}"
    echo "  3. Check PBX NAT settings for extension ${SIP_USERNAME}"
    echo "  4. Review logs: docker logs callbot-app | grep ERROR"
    echo
    print_success "Deployment completed successfully!"
}

# Main deployment function
main() {
    # Clear screen and show header
    clear
    echo -e "${MAGENTA}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║                                                          ║"
    echo "║            A-Call-Bot-V2 Deployment Script              ║"
    echo "║                                                          ║"
    echo "║         Automated SIP Bot with AI Integration           ║"
    echo "║                                                          ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Initialize log file
    echo "Deployment started at $(date)" > $LOG_FILE
    
    # Run deployment steps
    check_system_requirements
    check_prerequisites
    check_docker_daemon
    setup_environment
    configure_ollama
    setup_firewall
    clean_docker_system
    create_docker_compose
    build_docker_image
    start_services
    verify_sip_registration
    show_deployment_summary
    
    # Save deployment info
    echo "Deployment completed at $(date)" >> $LOG_FILE
}

# Run the main function
main "$@"