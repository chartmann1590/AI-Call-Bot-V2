#!/bin/bash

# CallBot Startup Script
# This script helps you start CallBot in different modes

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if Docker is available
check_docker() {
    if command_exists docker && command_exists docker-compose; then
        return 0
    else
        return 1
    fi
}

# Function to check if Python is available
check_python() {
    if command_exists python3; then
        return 0
    else
        return 1
    fi
}

# Function to run setup test
run_setup_test() {
    print_status "Running setup test..."
    if python3 test_setup.py; then
        print_success "Setup test passed!"
        return 0
    else
        print_error "Setup test failed!"
        return 1
    fi
}

# Function to start with Docker
start_docker() {
    print_status "Starting CallBot with Docker..."
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found!"
        exit 1
    fi
    
    # Check if .env file exists, create from example if not
    if [ ! -f ".env" ]; then
        if [ -f "env.example" ]; then
            print_warning ".env file not found, creating from example..."
            cp env.example .env
            print_warning "Please edit .env file with your settings before continuing!"
            read -p "Press Enter to continue or Ctrl+C to abort..."
        else
            print_error "No .env file or env.example found!"
            exit 1
        fi
    fi
    
    # Start services
    docker-compose up -d
    
    print_success "CallBot started with Docker!"
    print_status "Web interface: http://localhost:5000"
    print_status "Admin interface: http://localhost:5000/admin"
    print_status "To view logs: docker-compose logs -f callbot"
    print_status "To stop: docker-compose down"
}

# Function to start with Python
start_python() {
    print_status "Starting CallBot with Python..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_warning "Virtual environment not found, creating one..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing dependencies..."
    pip install -r requirements.txt
    
    # Run setup test
    if ! run_setup_test; then
        print_error "Setup test failed! Please fix the issues and try again."
        exit 1
    fi
    
    # Start the application
    print_status "Starting CallBot..."
    python callbot.py
}

# Function to show help
show_help() {
    echo "CallBot Startup Script"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  docker    Start CallBot using Docker (recommended)"
    echo "  python    Start CallBot using Python directly"
    echo "  test      Run setup test only"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 docker    # Start with Docker"
    echo "  $0 python    # Start with Python"
    echo "  $0 test      # Run setup test"
}

# Main script logic
case "${1:-}" in
    "docker")
        if check_docker; then
            start_docker
        else
            print_error "Docker not found! Please install Docker and Docker Compose."
            exit 1
        fi
        ;;
    "python")
        if check_python; then
            start_python
        else
            print_error "Python 3 not found! Please install Python 3.8+."
            exit 1
        fi
        ;;
    "test")
        if check_python; then
            run_setup_test
        else
            print_error "Python 3 not found! Please install Python 3.8+."
            exit 1
        fi
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    "")
        # No argument provided, try to auto-detect
        print_status "No mode specified, auto-detecting..."
        
        if check_docker; then
            print_status "Docker detected, starting with Docker..."
            start_docker
        elif check_python; then
            print_status "Python detected, starting with Python..."
            start_python
        else
            print_error "Neither Docker nor Python found!"
            echo ""
            show_help
            exit 1
        fi
        ;;
    *)
        print_error "Unknown option: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 