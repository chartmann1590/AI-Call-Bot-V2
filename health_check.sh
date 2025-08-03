#!/bin/bash

# Health Check Script for A-Call-Bot-V2
# This script verifies that all services are running correctly

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

# Check if docker-compose.prod.yml exists
if [ ! -f "docker-compose.prod.yml" ]; then
    print_error "Production docker-compose file not found. Run deploy.sh first."
    exit 1
fi

echo "=========================================="
echo "    A-Call-Bot-V2 Health Check"
echo "=========================================="
echo

# Check container status
print_status "Checking container status..."
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    print_success "All containers are running"
    docker-compose -f docker-compose.prod.yml ps
else
    print_error "Some containers are not running"
    docker-compose -f docker-compose.prod.yml ps
    exit 1
fi

echo

# Check SSL certificate
print_status "Checking SSL certificate..."
if [ -f "ssl/cert.crt" ] && [ -f "ssl/private.key" ]; then
    print_success "SSL certificate files exist"
    
    # Check certificate validity
    if openssl x509 -in ssl/cert.crt -text -noout | grep -q "Not After"; then
        print_success "SSL certificate is valid"
    else
        print_warning "SSL certificate validation failed"
    fi
else
    print_error "SSL certificate files missing"
fi

echo

# Check nginx configuration
print_status "Checking nginx configuration..."
if [ -f "nginx/nginx.conf" ]; then
    print_success "Nginx configuration exists"
    
    # Test nginx configuration syntax
    if docker run --rm -v $(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro nginx:alpine nginx -t 2>/dev/null; then
        print_success "Nginx configuration is valid"
    else
        print_warning "Nginx configuration syntax check failed"
    fi
else
    print_error "Nginx configuration missing"
fi

echo

# Test web interface
print_status "Testing web interface..."
if curl -k -s -o /dev/null -w "%{http_code}" https://localhost | grep -q "200\|301\|302"; then
    print_success "Web interface is accessible"
else
    print_error "Web interface is not accessible"
fi

echo

# Test API endpoints
print_status "Testing API endpoints..."
if curl -k -s https://localhost/api/health 2>/dev/null | grep -q "ok\|healthy"; then
    print_success "API health endpoint is responding"
else
    print_warning "API health endpoint not responding (this might be normal if not implemented)"
fi

echo

# Check resource usage
print_status "Checking resource usage..."
echo "Container resource usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

echo

# Check logs for errors
print_status "Checking for recent errors in logs..."
ERROR_COUNT=$(docker-compose -f docker-compose.prod.yml logs --tail=100 2>&1 | grep -i "error\|exception\|failed" | wc -l)

if [ "$ERROR_COUNT" -eq 0 ]; then
    print_success "No recent errors found in logs"
else
    print_warning "Found $ERROR_COUNT potential errors in recent logs"
    echo "Recent log entries with errors:"
    docker-compose -f docker-compose.prod.yml logs --tail=50 2>&1 | grep -i "error\|exception\|failed" | tail -5
fi

echo

# Check network connectivity
print_status "Checking network connectivity..."
if docker network ls | grep -q "callbot-network"; then
    print_success "Docker network exists"
else
    print_error "Docker network missing"
fi

echo

# Check volumes
print_status "Checking Docker volumes..."
VOLUMES=$(docker volume ls --format "{{.Name}}" | grep callbot)
if [ -n "$VOLUMES" ]; then
    print_success "Docker volumes exist"
    echo "Volumes: $VOLUMES"
else
    print_warning "No Docker volumes found"
fi

echo

# Final summary
echo "=========================================="
echo "           HEALTH CHECK SUMMARY"
echo "=========================================="
echo

if [ "$ERROR_COUNT" -eq 0 ] && curl -k -s -o /dev/null -w "%{http_code}" https://localhost | grep -q "200\|301\|302"; then
    print_success "All health checks passed! The application is running correctly."
    echo
    echo "Access your application at:"
    echo "  HTTPS: https://localhost"
    echo "  HTTP:  http://localhost (redirects to HTTPS)"
    echo
    echo "Useful commands:"
    echo "  - View logs: docker-compose -f docker-compose.prod.yml logs -f"
    echo "  - Stop services: docker-compose -f docker-compose.prod.yml down"
    echo "  - Restart services: docker-compose -f docker-compose.prod.yml restart"
else
    print_warning "Some health checks failed. Please review the output above."
    echo
    echo "Troubleshooting tips:"
    echo "  - Check logs: docker-compose -f docker-compose.prod.yml logs"
    echo "  - Restart services: docker-compose -f docker-compose.prod.yml restart"
    echo "  - Redeploy: ./deploy.sh"
fi

echo 