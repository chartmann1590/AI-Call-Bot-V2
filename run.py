#!/usr/bin/env python3
"""
CallBot Development Server
Simple script to run the CallBot application in development mode.
"""

import os
import sys
from src.app import create_app

def main():
    """Run the CallBot application"""
    
    # Set development environment
    os.environ.setdefault('FLASK_ENV', 'development')
    os.environ.setdefault('FLASK_DEBUG', '1')
    
    # Create the application
    app = create_app('development')
    
    # Run the application
    app.run(
        host=app.config.get('WEB_HOST', '0.0.0.0'),
        port=app.config.get('WEB_PORT', 5000),
        debug=app.config.get('DEBUG', True)
    )

if __name__ == '__main__':
    main() 