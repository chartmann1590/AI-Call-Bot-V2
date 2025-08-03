import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///callbot.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SIP Configuration
    SIP_DOMAIN = os.environ.get('SIP_DOMAIN') or 'pbx.example.com'
    SIP_USERNAME = os.environ.get('SIP_USERNAME') or '1001'
    SIP_PASSWORD = os.environ.get('SIP_PASSWORD') or 'password'
    SIP_PORT = int(os.environ.get('SIP_PORT') or 5060)
    
    # Whisper Configuration
    WHISPER_MODEL_SIZE = os.environ.get('WHISPER_MODEL_SIZE') or 'base'
    WHISPER_DEVICE = os.environ.get('WHISPER_DEVICE') or 'cpu'
    WHISPER_COMPUTE_TYPE = os.environ.get('WHISPER_COMPUTE_TYPE') or 'int8'
    
    # Ollama Configuration
    OLLAMA_URL = os.environ.get('OLLAMA_URL') or 'http://localhost:11434'
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL') or 'llama2'
    
    # TTS Configuration
    TTS_ENGINE = os.environ.get('TTS_ENGINE') or 'coqui'
    TTS_VOICE = os.environ.get('TTS_VOICE') or 'en_0'
    
    # Audio Configuration
    AUDIO_SAMPLE_RATE = 16000
    AUDIO_CHUNK_DURATION = 5  # seconds
    AUDIO_OUTPUT_DIR = os.environ.get('AUDIO_OUTPUT_DIR') or 'audio_output'
    
    # Redis Configuration (for Celery)
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Web Server Configuration
    WEB_PORT = int(os.environ.get('WEB_PORT') or 5000)
    WEB_HOST = os.environ.get('WEB_HOST') or '0.0.0.0'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 