#!/usr/bin/env python3
"""
Simple test script to verify SIP client functionality
"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sip_client import SIPClient
from src.models import Settings, db
from src.config import config
from flask import Flask

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_sip_client():
    """Test SIP client initialization and registration using database settings"""
    
    # Create Flask app context to access database
    app = Flask(__name__)
    app.config.from_object(config['default'])
    db.init_app(app)
    
    with app.app_context():
        # Get settings from database
        settings = Settings.get_settings()
        
        # Check if SIP settings are configured
        print(f"Checking SIP settings from database:")
        print(f"Domain: '{settings.sip_domain}'")
        print(f"Username: '{settings.sip_username}'")
        print(f"Password: {'*' * len(settings.sip_password) if settings.sip_password else 'None'}")
        print(f"Port: {settings.sip_port}")
        
        if not settings.sip_domain or not settings.sip_domain.strip():
            print("✗ SIP domain is not configured")
            print("Please configure SIP settings in the web interface or environment variables")
            return False
        elif not settings.sip_username or not settings.sip_username.strip():
            print("✗ SIP username is not configured")
            print("Please configure SIP settings in the web interface or environment variables")
            return False
        elif not settings.sip_password or not settings.sip_password.strip():
            print("✗ SIP password is not configured")
            print("Please configure SIP settings in the web interface or environment variables")
            return False
        
        print(f"✓ SIP settings are configured")
        print(f"Testing SIP client with settings from database:")
        print(f"Domain: {settings.sip_domain}")
        print(f"Username: {settings.sip_username}")
        print(f"Port: {settings.sip_port}")
        
        try:
            # Initialize SIP client with database settings
            sip_client = SIPClient(
                domain=settings.sip_domain.strip(),
                username=settings.sip_username.strip(),
                password=settings.sip_password.strip(),
                port=settings.sip_port
            )
            
            print("✓ SIP client initialized successfully")
            
            # Test registration
            print("Testing SIP registration...")
            if sip_client.register():
                print("✓ SIP registration successful")
            else:
                print("✗ SIP registration failed")
            
            # Test status methods
            print(f"Registration status: {sip_client.is_registered()}")
            print(f"Registration info: {sip_client.get_registration_status()}")
            
            # Cleanup
            sip_client.shutdown()
            print("✓ SIP client shutdown complete")
            
        except ValueError as e:
            print(f"✗ SIP client validation error: {e}")
            return False
        except Exception as e:
            print(f"✗ Error testing SIP client: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    
    return True

if __name__ == "__main__":
    print("SIP Client Test")
    print("=" * 50)
    
    success = test_sip_client()
    
    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Tests failed!")
        sys.exit(1) 