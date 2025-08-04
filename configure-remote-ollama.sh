#!/bin/bash

# Configure Remote Ollama Script
# This script helps you configure CallBot to use a remote Ollama instance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

echo "=========================================="
echo "    Remote Ollama Configuration"
echo "=========================================="
echo

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_status "Creating .env file from template..."
    cp env.example .env
    print_success ".env file created"
else
    print_status ".env file already exists"
fi

echo
echo "Remote Ollama Configuration Options:"
echo "1. Use remote Ollama (recommended for production)"
echo "2. Use local Ollama (default)"
echo "3. Skip configuration"
echo

read -p "Choose an option (1-3): " choice

case $choice in
    1)
        echo
        print_status "Configuring remote Ollama..."
        
        read -p "Enter your remote Ollama URL (e.g., https://your-ollama-server.com:11434): " ollama_url
        
        if [ -z "$ollama_url" ]; then
            print_error "Ollama URL cannot be empty"
            exit 1
        fi
        
        read -p "Enter the model name (default: llama2): " ollama_model
        ollama_model=${ollama_model:-llama2}
        
        # Update .env file
        sed -i.bak "s|# OLLAMA_URL=https://your-ollama-server.com:11434|OLLAMA_URL=$ollama_url|" .env
        sed -i.bak "s|# OLLAMA_MODEL=llama2|OLLAMA_MODEL=$ollama_model|" .env
        
        print_success "Remote Ollama configured:"
        print_success "  URL: $ollama_url"
        print_success "  Model: $ollama_model"
        
        echo
        print_warning "To use remote Ollama, run:"
        print_warning "  docker-compose up -d"
        print_warning "  (This will NOT start local Ollama)"
        ;;
        
    2)
        echo
        print_status "Configuring local Ollama..."
        
        # Update .env file to use local Ollama
        sed -i.bak "s|# OLLAMA_URL=https://your-ollama-server.com:11434|OLLAMA_URL=http://ollama:11434|" .env
        sed -i.bak "s|# OLLAMA_MODEL=llama2|OLLAMA_MODEL=llama2|" .env
        
        print_success "Local Ollama configured"
        
        echo
        print_warning "To use local Ollama, run:"
        print_warning "  docker-compose --profile local-ollama up -d"
        print_warning "  (This will start local Ollama container)"
        ;;
        
    3)
        print_status "Skipping configuration"
        ;;
        
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

echo
print_success "Configuration complete!"
echo
print_status "Next steps:"
echo "1. Edit .env file to customize other settings"
echo "2. Run: docker-compose up -d (for remote Ollama)"
echo "3. Run: docker-compose --profile local-ollama up -d (for local Ollama)"
echo 