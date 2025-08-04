#!/bin/bash

echo "Python Version Compatibility Fix"
echo "================================"
echo ""
echo "The error you encountered is due to the TTS package requiring Python 3.10+"
echo "but your environment is using Python 3.9."
echo ""
echo "You have two options:"
echo ""
echo "1. UPGRADE TO PYTHON 3.10+ (Recommended)"
echo "   - I've already updated the Dockerfiles to use Python 3.10"
echo "   - This allows you to use all TTS engines including Coqui TTS"
echo "   - Run: docker-compose build --no-cache"
echo ""
echo "2. USE ALTERNATIVE TTS ENGINES (Python 3.9 compatible)"
echo "   - Use pyttsx3 and espeak-ng instead of Coqui TTS"
echo "   - Copy requirements-python39.txt to requirements.txt"
echo "   - Run: cp requirements-python39.txt requirements.txt && docker-compose build"
echo ""
echo "Which option would you like to use?"
echo ""
echo "Enter 1 for Python 3.10 upgrade (recommended)"
echo "Enter 2 for alternative TTS engines"
echo ""
read -p "Enter your choice (1 or 2): " choice

case $choice in
    1)
        echo "Upgrading to Python 3.10..."
        echo "Dockerfiles have been updated. Running build..."
        docker-compose build --no-cache
        ;;
    2)
        echo "Using alternative TTS engines..."
        cp requirements-python39.txt requirements.txt
        echo "requirements.txt updated. Running build..."
        docker-compose build
        ;;
    *)
        echo "Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "Build completed! You can now run: docker-compose up" 