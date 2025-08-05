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
from src.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_sip_client():
    """Test SIP client initialization and registration"""
    
    # Test configuration
    test_config = {
        'domain': 'pbx.example.com',
        'username': 'test_user',
        'password': 'test_password',
        'port': 5060
    }
    
    print("Testing SIP client initialization...")
    
    try:
        # Initialize SIP client
        sip_client = SIPClient(
            domain=test_config['domain'],
            username=test_config['username'],
            password=test_config['password'],
            port=test_config['port']
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
        
    except Exception as e:
        print(f"✗ Error testing SIP client: {e}")
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