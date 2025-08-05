from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()

class Call(db.Model):
    """Model for storing call records"""
    __tablename__ = 'calls'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    caller_id = db.Column(db.String(50), nullable=False)
    transcript = db.Column(db.Text, nullable=True)
    ai_response = db.Column(db.Text, nullable=True)
    tts_voice = db.Column(db.String(50), nullable=True)
    audio_filename = db.Column(db.String(255), nullable=True)
    duration = db.Column(db.Integer, nullable=True)  # duration in seconds
    status = db.Column(db.String(20), default='completed')  # completed, failed, in_progress
    
    def __repr__(self):
        return f'<Call {self.id}: {self.caller_id} at {self.timestamp}>'
    
    @hybrid_property
    def duration_formatted(self):
        """Return duration in MM:SS format"""
        if self.duration:
            minutes = self.duration // 60
            seconds = self.duration % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"
    
    def to_dict(self):
        """Convert call to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'caller_id': self.caller_id,
            'transcript': self.transcript,
            'ai_response': self.ai_response,
            'tts_voice': self.tts_voice,
            'audio_filename': self.audio_filename,
            'duration': self.duration,
            'duration_formatted': self.duration_formatted,
            'status': self.status
        }

class Settings(db.Model):
    """Singleton model for application settings"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    ollama_url = db.Column(db.String(255), nullable=False, default='')
    ollama_model = db.Column(db.String(100), nullable=False, default='llama2')
    tts_engine = db.Column(db.String(50), nullable=False, default='coqui')
    tts_voice = db.Column(db.String(100), nullable=False, default='en_0')
    sip_domain = db.Column(db.String(255), nullable=False, default='')
    sip_username = db.Column(db.String(100), nullable=False, default='')
    sip_password = db.Column(db.String(255), nullable=False, default='')
    sip_port = db.Column(db.Integer, nullable=False, default=5060)
    whisper_model_size = db.Column(db.String(20), nullable=False, default='base')
    whisper_device = db.Column(db.String(20), nullable=False, default='cpu')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Settings {self.id}>'
    
    @classmethod
    def get_settings(cls):
        """Get the singleton settings instance, create if doesn't exist"""
        import os
        settings = cls.query.first()
        if not settings:
            settings = cls()
            # Initialize with environment variables if available
            settings.ollama_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
            settings.ollama_model = os.environ.get('OLLAMA_MODEL', 'llama2')
            settings.tts_engine = os.environ.get('TTS_ENGINE', 'coqui')
            settings.tts_voice = os.environ.get('TTS_VOICE', 'en_0')
            settings.sip_domain = os.environ.get('SIP_DOMAIN', '')
            settings.sip_username = os.environ.get('SIP_USERNAME', '')
            settings.sip_password = os.environ.get('SIP_PASSWORD', '')
            settings.sip_port = int(os.environ.get('SIP_PORT', 5060))
            settings.whisper_model_size = os.environ.get('WHISPER_MODEL_SIZE', 'base')
            settings.whisper_device = os.environ.get('WHISPER_DEVICE', 'cpu')
            db.session.add(settings)
            db.session.commit()
        return settings
    
    def to_dict(self):
        """Convert settings to dictionary"""
        return {
            'id': self.id,
            'ollama_url': self.ollama_url,
            'ollama_model': self.ollama_model,
            'tts_engine': self.tts_engine,
            'tts_voice': self.tts_voice,
            'sip_domain': self.sip_domain,
            'sip_username': self.sip_username,
            'sip_password': self.sip_password,
            'sip_port': self.sip_port,
            'whisper_model_size': self.whisper_model_size,
            'whisper_device': self.whisper_device,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def reset_settings(cls):
        """Reset settings to environment variables"""
        import os
        settings = cls.get_settings()
        settings.ollama_url = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        settings.ollama_model = os.environ.get('OLLAMA_MODEL', 'llama2')
        settings.tts_engine = os.environ.get('TTS_ENGINE', 'coqui')
        settings.tts_voice = os.environ.get('TTS_VOICE', 'en_0')
        settings.sip_domain = os.environ.get('SIP_DOMAIN', '')
        settings.sip_username = os.environ.get('SIP_USERNAME', '')
        settings.sip_password = os.environ.get('SIP_PASSWORD', '')
        settings.sip_port = int(os.environ.get('SIP_PORT', 5060))
        settings.whisper_model_size = os.environ.get('WHISPER_MODEL_SIZE', 'base')
        settings.whisper_device = os.environ.get('WHISPER_DEVICE', 'cpu')
        db.session.commit()
        return settings 