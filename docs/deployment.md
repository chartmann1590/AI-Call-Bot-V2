# A-Call-Bot-V2 Deployment Guide

This guide explains how to deploy the A-Call-Bot-V2 application with SSL encryption using the provided deploy script.

## Prerequisites

Before running the deployment script, ensure you have the following installed:

- **Docker** (version 20.10 or later)
- **Docker Compose** (version 2.0 or later)
- **OpenSSL** (for SSL certificate generation)
- **Git** (for pulling latest changes)

### Installing Prerequisites

#### On macOS:
```bash
# Install Docker Desktop
brew install --cask docker

# Install OpenSSL (if not already installed)
brew install openssl
```

#### On Ubuntu/Debian:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install OpenSSL
sudo apt-get update
sudo apt-get install openssl
```

#### On CentOS/RHEL:
```bash
# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install OpenSSL
sudo yum install openssl
```

## Quick Deployment

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd A-Call-Bot-V2
   ```

2. **Configure environment variables** (optional):
   ```bash
   cp docs/env.production.example .env
   # Edit .env with your actual values
   ```

3. **Run the deployment script**:
   ```bash
   ./deploy.sh
   ```

The script will automatically:
- Pull the latest changes from git
- Generate a self-signed SSL certificate
- Create nginx configuration with SSL
- Build and deploy the Docker containers
- Start all services

## Manual Deployment Steps

If you prefer to deploy manually or need to customize the process:

### 1. Pull Latest Changes
```bash
git fetch origin
git reset --hard origin/main
```

### 2. Generate SSL Certificate
```bash
mkdir -p ssl
openssl genrsa -out ssl/private.key 2048
openssl req -new -key ssl/private.key -out ssl/cert.csr -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"
openssl x509 -req -in ssl/cert.csr -signkey ssl/private.key -out ssl/cert.crt -days 365
chmod 600 ssl/private.key
chmod 644 ssl/cert.crt
rm ssl/cert.csr
```

### 3. Deploy with Docker Compose
```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d --build
```

## Configuration

### Environment Variables

The application uses environment variables for configuration. Copy `docs/env.production.example` to `.env` and update the values:

```bash
cp docs/env.production.example .env
```

Key configuration options:

- **SECRET_KEY**: Flask secret key (change in production)
- **SIP_DOMAIN**: Your SIP server domain
- **SIP_USERNAME**: SIP username
- **SIP_PASSWORD**: SIP password
- **OLLAMA_MODEL**: AI model to use (default: llama2)
- **DOMAIN**: Your domain name for SSL certificate

### SSL Certificate

The deployment script generates a self-signed SSL certificate. For production use:

1. **Replace with a proper certificate**:
   - Obtain a certificate from a trusted CA (Let's Encrypt, etc.)
   - Replace `ssl/cert.crt` and `ssl/private.key`
   - Update the domain in nginx configuration

2. **Using Let's Encrypt**:
   ```bash
   # Install certbot
   sudo apt-get install certbot

   # Generate certificate
   sudo certbot certonly --standalone -d your-domain.com

   # Copy certificates
   sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.crt
   sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/private.key
   ```

### Nginx Configuration

The nginx configuration includes:
- SSL/TLS encryption
- HTTP to HTTPS redirect
- Rate limiting
- Security headers
- WebSocket support
- Static file serving

Customize `nginx/nginx.conf` as needed.

## Service Management

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f callbot
```

### Stop Services
```bash
docker-compose -f docker-compose.prod.yml down
```

### Restart Services
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Update Application
```bash
# Pull latest changes and redeploy
./deploy.sh
```

## Troubleshooting

### Common Issues

1. **Port conflicts**:
   - Ensure ports 80, 443, 5000, 5060 are available
   - Check for existing services using these ports

2. **SSL certificate issues**:
   - Verify certificate files exist in `ssl/` directory
   - Check file permissions (600 for key, 644 for cert)
   - Ensure domain matches certificate

3. **Container startup failures**:
   - Check logs: `docker-compose -f docker-compose.prod.yml logs`
   - Verify environment variables are set correctly
   - Ensure Docker has sufficient resources

4. **Permission issues**:
   - Ensure the deploy script is executable: `chmod +x deploy.sh`
   - Check file permissions for SSL certificates

### Health Checks

Verify services are running:
```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# Test web interface
curl -k https://localhost

# Test API endpoints
curl -k https://localhost/api/health
```

### Resource Requirements

Minimum recommended resources:
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 10GB free space
- **Network**: Stable internet connection for AI model downloads

## Security Considerations

1. **Change default passwords**:
   - Update SIP credentials
   - Change Flask secret key
   - Use strong passwords

2. **SSL/TLS**:
   - Use proper certificates for production
   - Regularly renew certificates
   - Monitor certificate expiration

3. **Network security**:
   - Configure firewall rules
   - Use VPN for remote access
   - Limit access to management ports

4. **Updates**:
   - Regularly update Docker images
   - Monitor for security patches
   - Keep system packages updated

## Monitoring

### Log Monitoring
```bash
# Real-time log monitoring
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

### Resource Monitoring
```bash
# Container resource usage
docker stats

# Disk usage
df -h

# Memory usage
free -h
```

### Health Monitoring
Set up monitoring for:
- Container health status
- Application response times
- Error rates
- Resource utilization

## Backup and Recovery

### Backup Strategy
1. **Application data**:
   ```bash
   docker run --rm -v callbot_data:/data -v $(pwd):/backup alpine tar czf /backup/callbot-data.tar.gz -C /data .
   ```

2. **Configuration files**:
   ```bash
   tar czf config-backup.tar.gz ssl/ nginx/ .env
   ```

3. **SSL certificates**:
   ```bash
   cp -r ssl/ ssl-backup/
   ```

### Recovery
1. **Restore data**:
   ```bash
   docker run --rm -v callbot_data:/data -v $(pwd):/backup alpine tar xzf /backup/callbot-data.tar.gz -C /data
   ```

2. **Restore configuration**:
   ```bash
   tar xzf config-backup.tar.gz
   ```

3. **Redeploy**:
   ```bash
   ./deploy.sh
   ```

## Support

For issues and questions:
1. Check the logs for error messages
2. Review this deployment guide
3. Check the main project README
4. Open an issue on the project repository

## License

This deployment guide is part of the A-Call-Bot-V2 project and follows the same license terms. 