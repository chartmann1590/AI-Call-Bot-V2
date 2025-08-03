# Security Guide

This document outlines security best practices for CallBot deployment and operation.

## Security Overview

CallBot handles sensitive information including:
- SIP credentials and call data
- Audio recordings and transcripts
- AI conversation logs
- User configuration data

## Security Architecture

### Network Security

#### Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 5000/tcp  # Web interface (HTTPS in production)
sudo ufw allow 5060/udp  # SIP
sudo ufw enable
```

#### Reverse Proxy Setup
```nginx
# nginx configuration for HTTPS
server {
    listen 443 ssl;
    server_name callbot.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Application Security

#### Environment Variables
```bash
# Generate secure secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Use strong passwords
SIP_PASSWORD=your-very-strong-password-here
SECRET_KEY=your-generated-secret-key-here
```

#### Database Security
```bash
# Use PostgreSQL with encryption
sudo -u postgres psql
CREATE USER callbot WITH PASSWORD 'strong-password';
GRANT CONNECT ON DATABASE callbot TO callbot;
GRANT USAGE ON SCHEMA public TO callbot;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO callbot;
```

### Access Control

#### User Management
```bash
# Create dedicated user
sudo useradd -m -s /bin/bash callbot
sudo usermod -aG audio callbot

# Set proper permissions
sudo chown -R callbot:callbot /opt/callbot
sudo chmod 750 /opt/callbot
```

#### File Permissions
```bash
# Secure sensitive files
sudo chmod 600 /opt/callbot/.env
sudo chmod 600 /opt/callbot/callbot.db
sudo chmod 750 /opt/callbot/audio_output/
```

## Data Protection

### Audio Data
- Audio files are stored locally by default
- Consider encryption for sensitive recordings
- Implement automatic cleanup policies
- Use secure storage for production

### Transcript Security
```python
# Example: Encrypt sensitive data
from cryptography.fernet import Fernet

def encrypt_transcript(text, key):
    f = Fernet(key)
    return f.encrypt(text.encode())

def decrypt_transcript(encrypted_text, key):
    f = Fernet(key)
    return f.decrypt(encrypted_text).decode()
```

### Database Encryption
```bash
# PostgreSQL with encryption
sudo -u postgres psql
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_cert_file = '/etc/ssl/certs/ssl-cert-snakeoil.pem';
ALTER SYSTEM SET ssl_key_file = '/etc/ssl/private/ssl-cert-snakeoil.key';
SELECT pg_reload_conf();
```

## Network Security

### SIP Security
```bash
# Use SRTP for encrypted audio
# Configure TLS for SIP signaling
# Implement SIP authentication
```

### API Security
```python
# Rate limiting example
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

### HTTPS Configuration
```bash
# Obtain SSL certificate
sudo certbot --nginx -d callbot.yourdomain.com

# Force HTTPS redirect
# Configure HSTS headers
```

## Monitoring and Logging

### Security Logging
```python
import logging
from datetime import datetime

def log_security_event(event_type, details):
    logging.warning(f"SECURITY: {event_type} - {details} - {datetime.now()}")
```

### Audit Trail
```sql
-- Create audit table
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    user_id VARCHAR(50),
    action VARCHAR(100),
    details TEXT,
    ip_address INET
);
```

### Monitoring Setup
```bash
# Install monitoring tools
sudo apt-get install fail2ban logwatch

# Configure fail2ban for web interface
sudo tee /etc/fail2ban/jail.local << EOF
[callbot-web]
enabled = true
port = 5000
filter = callbot-web
logpath = /var/log/callbot/access.log
maxretry = 3
bantime = 3600
EOF
```

## Compliance

### GDPR Compliance
- Implement data retention policies
- Provide data export functionality
- Enable user consent management
- Document data processing activities

### HIPAA Compliance (if applicable)
- Encrypt all data at rest and in transit
- Implement access controls
- Maintain audit logs
- Regular security assessments

### SOX Compliance (if applicable)
- Maintain detailed audit trails
- Implement change management
- Regular security reviews
- Document all procedures

## Incident Response

### Security Incident Plan
1. **Detection**: Monitor logs and alerts
2. **Assessment**: Evaluate impact and scope
3. **Containment**: Isolate affected systems
4. **Eradication**: Remove threat
5. **Recovery**: Restore normal operations
6. **Lessons Learned**: Document and improve

### Contact Information
```bash
# Security team contacts
SECURITY_EMAIL=security@yourcompany.com
EMERGENCY_PHONE=+1-555-0123
```

## Regular Security Tasks

### Daily
- Review security logs
- Check system status
- Monitor for unusual activity

### Weekly
- Update security patches
- Review access logs
- Backup verification

### Monthly
- Security assessment
- Update dependencies
- Review user access

### Quarterly
- Penetration testing
- Security training
- Policy review

## Security Checklist

### Pre-Deployment
- [ ] Change default passwords
- [ ] Configure firewall
- [ ] Set up HTTPS
- [ ] Install security updates
- [ ] Configure logging
- [ ] Set up monitoring

### Post-Deployment
- [ ] Regular security scans
- [ ] Monitor logs
- [ ] Update dependencies
- [ ] Review access controls
- [ ] Test backup/restore
- [ ] Security training

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [SIP Security Best Practices](https://tools.ietf.org/html/rfc3261)
- [Flask Security Documentation](https://flask-security.readthedocs.io/) 