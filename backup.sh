#!/bin/bash

# Backup Script for A-Call-Bot-V2
# This script creates backups of application data and configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="callbot_backup_$TIMESTAMP"

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

# Create backup directory
create_backup_dir() {
    print_status "Creating backup directory..."
    mkdir -p "$BACKUP_DIR"
    print_success "Backup directory created: $BACKUP_DIR"
}

# Backup Docker volumes
backup_volumes() {
    print_status "Backing up Docker volumes..."
    
    # Check if volumes exist
    VOLUMES=$(docker volume ls --format "{{.Name}}" | grep callbot || true)
    
    if [ -n "$VOLUMES" ]; then
        for volume in $VOLUMES; do
            print_status "Backing up volume: $volume"
            docker run --rm -v "$volume:/data" -v "$(pwd)/$BACKUP_DIR:/backup" alpine tar czf "/backup/${volume}_${TIMESTAMP}.tar.gz" -C /data .
            print_success "Volume $volume backed up successfully"
        done
    else
        print_warning "No Docker volumes found to backup"
    fi
}

# Backup configuration files
backup_config() {
    print_status "Backing up configuration files..."
    
    CONFIG_FILES=()
    
    # Check for configuration files
    if [ -d "ssl" ]; then
        CONFIG_FILES+=("ssl")
    fi
    
    if [ -d "nginx" ]; then
        CONFIG_FILES+=("nginx")
    fi
    
    if [ -f ".env" ]; then
        CONFIG_FILES+=(".env")
    fi
    
    if [ -f "docker-compose.prod.yml" ]; then
        CONFIG_FILES+=("docker-compose.prod.yml")
    fi
    
    if [ ${#CONFIG_FILES[@]} -gt 0 ]; then
        tar czf "$BACKUP_DIR/config_${TIMESTAMP}.tar.gz" "${CONFIG_FILES[@]}"
        print_success "Configuration files backed up successfully"
    else
        print_warning "No configuration files found to backup"
    fi
}

# Backup application data
backup_app_data() {
    print_status "Backing up application data..."
    
    APP_DATA_DIRS=()
    
    # Check for application data directories
    if [ -d "audio_output" ]; then
        APP_DATA_DIRS+=("audio_output")
    fi
    
    if [ -d "logs" ]; then
        APP_DATA_DIRS+=("logs")
    fi
    
    if [ -d "data" ]; then
        APP_DATA_DIRS+=("data")
    fi
    
    if [ ${#APP_DATA_DIRS[@]} -gt 0 ]; then
        tar czf "$BACKUP_DIR/app_data_${TIMESTAMP}.tar.gz" "${APP_DATA_DIRS[@]}"
        print_success "Application data backed up successfully"
    else
        print_warning "No application data directories found to backup"
    fi
}

# Create backup manifest
create_manifest() {
    print_status "Creating backup manifest..."
    
    cat > "$BACKUP_DIR/manifest_${TIMESTAMP}.txt" << EOF
A-Call-Bot-V2 Backup Manifest
Generated: $(date)
Backup ID: $BACKUP_NAME

Files included in this backup:
$(ls -la "$BACKUP_DIR"/*"$TIMESTAMP"* 2>/dev/null || echo "No backup files found")

System Information:
- OS: $(uname -s)
- Architecture: $(uname -m)
- Docker Version: $(docker --version 2>/dev/null || echo "Docker not available")
- Docker Compose Version: $(docker-compose --version 2>/dev/null || echo "Docker Compose not available")

Container Status:
$(docker-compose -f docker-compose.prod.yml ps 2>/dev/null || echo "Production containers not running")

Volume Information:
$(docker volume ls | grep callbot || echo "No callbot volumes found")

Backup completed successfully!
EOF
    
    print_success "Backup manifest created"
}

# Clean up old backups
cleanup_old_backups() {
    print_status "Cleaning up old backups (keeping last 5)..."
    
    # Keep only the last 5 backups
    cd "$BACKUP_DIR"
    ls -t | tail -n +6 | xargs -r rm -rf
    cd - > /dev/null
    
    print_success "Old backups cleaned up"
}

# Main backup function
main() {
    echo "=========================================="
    echo "    A-Call-Bot-V2 Backup Script"
    echo "=========================================="
    echo
    
    # Create backup directory
    create_backup_dir
    
    # Backup volumes
    backup_volumes
    
    # Backup configuration
    backup_config
    
    # Backup application data
    backup_app_data
    
    # Create manifest
    create_manifest
    
    # Clean up old backups
    cleanup_old_backups
    
    # Show backup summary
    echo
    echo "=========================================="
    echo "           BACKUP COMPLETE"
    echo "=========================================="
    echo
    echo "Backup location: $BACKUP_DIR"
    echo "Backup name: $BACKUP_NAME"
    echo
    echo "Backup files created:"
    ls -la "$BACKUP_DIR"/*"$TIMESTAMP"* 2>/dev/null || echo "No backup files found"
    echo
    echo "To restore from this backup:"
    echo "  1. Stop the application: docker-compose -f docker-compose.prod.yml down"
    echo "  2. Extract configuration: tar xzf $BACKUP_DIR/config_${TIMESTAMP}.tar.gz"
    echo "  3. Restore volumes: See DEPLOYMENT.md for volume restoration"
    echo "  4. Restart: ./deploy.sh"
    echo
}

# Run the main function
main "$@" 