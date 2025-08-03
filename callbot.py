#!/usr/bin/env python3
"""
CallBot Entry Point
Simple script to run CallBot from the project root.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import main

if __name__ == '__main__':
    main() 