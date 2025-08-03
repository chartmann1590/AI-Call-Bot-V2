import os
import logging
import tempfile
import subprocess
from typing import Optional, List, Dict, Any
from pydub import AudioSegment
import soundfile as sf
import numpy as np

# Try to import TTS engines
try:
    from TTS.api import TTS
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

logger = logging.getLogger(__name__)

class TTSEngine:
    """Base class for TTS engines"""
    
    def __init__(self, voice: str = 'default'):
        self.voice = voice
        self.sample_rate = 16000
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Synthesize text to speech
        
        Args:
            text: Text to synthesize
            output_path: Output audio file path
            
        Returns:
            True if synthesis successful, False otherwise
        """
        raise NotImplementedError
    
    def get_available_voices(self) -> List[str]:
        """Get list of available voices"""
        raise NotImplementedError
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get engine information"""
        raise NotImplementedError

class CoquiTTSEngine(TTSEngine):
    """Coqui TTS engine implementation"""
    
    def __init__(self, voice: str = 'en_0'):
        super().__init__(voice)
        self.tts = None
        self._initialize_tts()
    
    def _initialize_tts(self):
        """Initialize Coqui TTS"""
        try:
            if COQUI_AVAILABLE:
                # Use a lightweight model for faster synthesis
                self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", 
                              progress_bar=False)
                logger.info("Coqui TTS initialized successfully")
            else:
                logger.warning("Coqui TTS not available")
        except Exception as e:
            logger.error(f"Failed to initialize Coqui TTS: {e}")
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """Synthesize text using Coqui TTS"""
        try:
            if not self.tts:
                logger.error("Coqui TTS not initialized")
                return False
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Synthesize speech
            self.tts.tts_to_file(text=text, file_path=output_path)
            
            # Convert to target format and sample rate
            self._convert_audio(output_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Coqui TTS synthesis failed: {e}")
            return False
    
    def _convert_audio(self, file_path: str):
        """Convert audio to target format and sample rate"""
        try:
            # Load audio
            audio = AudioSegment.from_file(file_path)
            
            # Convert to mono and target sample rate
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(self.sample_rate)
            
            # Export
            audio.export(file_path, format="wav")
            
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
    
    def get_available_voices(self) -> List[str]:
        """Get available Coqui TTS voices"""
        return ['en_0', 'en_1', 'en_2']  # Simplified list
    
    def get_engine_info(self) -> Dict[str, Any]:
        return {
            'name': 'Coqui TTS',
            'available': COQUI_AVAILABLE,
            'voices': self.get_available_voices(),
            'sample_rate': self.sample_rate
        }

class ESpeakTTSEngine(TTSEngine):
    """eSpeak NG TTS engine implementation"""
    
    def __init__(self, voice: str = 'en-us'):
        super().__init__(voice)
        self._check_espeak()
    
    def _check_espeak(self):
        """Check if eSpeak is available"""
        try:
            subprocess.run(['espeak-ng', '--version'], 
                         capture_output=True, check=True)
            self.available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.available = False
            logger.warning("eSpeak NG not found")
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """Synthesize text using eSpeak NG"""
        try:
            if not self.available:
                logger.error("eSpeak NG not available")
                return False
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Synthesize using eSpeak NG
            cmd = [
                'espeak-ng',
                '-v', self.voice,
                '-s', '150',  # Speed
                '-p', '50',   # Pitch
                '-a', '100',  # Amplitude
                '-w', output_path,
                text
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Convert to target format and sample rate
                self._convert_audio(output_path)
                return True
            else:
                logger.error(f"eSpeak synthesis failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"eSpeak TTS synthesis failed: {e}")
            return False
    
    def _convert_audio(self, file_path: str):
        """Convert audio to target format and sample rate"""
        try:
            # Load audio
            audio = AudioSegment.from_file(file_path)
            
            # Convert to mono and target sample rate
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(self.sample_rate)
            
            # Export
            audio.export(file_path, format="wav")
            
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
    
    def get_available_voices(self) -> List[str]:
        """Get available eSpeak voices"""
        try:
            if not self.available:
                return []
            
            result = subprocess.run(['espeak-ng', '--voices'], 
                                  capture_output=True, text=True)
            
            voices = []
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        voices.append(parts[3])  # Voice name
            
            return voices[:10]  # Return first 10 voices
            
        except Exception as e:
            logger.error(f"Failed to get eSpeak voices: {e}")
            return ['en-us', 'en-gb', 'en-sc']
    
    def get_engine_info(self) -> Dict[str, Any]:
        return {
            'name': 'eSpeak NG',
            'available': self.available,
            'voices': self.get_available_voices(),
            'sample_rate': self.sample_rate
        }

class Pyttsx3TTSEngine(TTSEngine):
    """pyttsx3 TTS engine implementation"""
    
    def __init__(self, voice: str = 'default'):
        super().__init__(voice)
        self.engine = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize pyttsx3 engine"""
        try:
            if PYTTSX3_AVAILABLE:
                self.engine = pyttsx3.init()
                self.engine.setProperty('rate', 150)  # Speed
                self.engine.setProperty('volume', 0.9)  # Volume
                logger.info("pyttsx3 engine initialized successfully")
            else:
                logger.warning("pyttsx3 not available")
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
    
    def synthesize(self, text: str, output_path: str) -> bool:
        """Synthesize text using pyttsx3"""
        try:
            if not self.engine:
                logger.error("pyttsx3 engine not initialized")
                return False
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Set voice if specified
            if self.voice != 'default':
                voices = self.engine.getProperty('voices')
                for voice in voices:
                    if self.voice in voice.name:
                        self.engine.setProperty('voice', voice.id)
                        break
            
            # Synthesize to file
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()
            
            # Convert to target format and sample rate
            self._convert_audio(output_path)
            
            return True
            
        except Exception as e:
            logger.error(f"pyttsx3 synthesis failed: {e}")
            return False
    
    def _convert_audio(self, file_path: str):
        """Convert audio to target format and sample rate"""
        try:
            # Load audio
            audio = AudioSegment.from_file(file_path)
            
            # Convert to mono and target sample rate
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(self.sample_rate)
            
            # Export
            audio.export(file_path, format="wav")
            
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
    
    def get_available_voices(self) -> List[str]:
        """Get available pyttsx3 voices"""
        try:
            if not self.engine:
                return []
            
            voices = self.engine.getProperty('voices')
            return [voice.name for voice in voices]
            
        except Exception as e:
            logger.error(f"Failed to get pyttsx3 voices: {e}")
            return ['default']
    
    def get_engine_info(self) -> Dict[str, Any]:
        return {
            'name': 'pyttsx3',
            'available': PYTTSX3_AVAILABLE,
            'voices': self.get_available_voices(),
            'sample_rate': self.sample_rate
        }

class TTSManager:
    """Manager for multiple TTS engines"""
    
    def __init__(self):
        self.engines = {
            'coqui': CoquiTTSEngine(),
            'espeak': ESpeakTTSEngine(),
            'pyttsx3': Pyttsx3TTSEngine()
        }
    
    def get_engine(self, engine_name: str, voice: str = 'default') -> Optional[TTSEngine]:
        """
        Get TTS engine by name
        
        Args:
            engine_name: Name of the engine
            voice: Voice to use
            
        Returns:
            TTS engine instance or None if not available
        """
        if engine_name not in self.engines:
            logger.error(f"Unknown TTS engine: {engine_name}")
            return None
        
        engine_class = type(self.engines[engine_name])
        return engine_class(voice)
    
    def synthesize(self, text: str, engine_name: str, voice: str, 
                  output_path: str) -> bool:
        """
        Synthesize text using specified engine
        
        Args:
            text: Text to synthesize
            engine_name: Name of the TTS engine
            voice: Voice to use
            output_path: Output audio file path
            
        Returns:
            True if synthesis successful, False otherwise
        """
        engine = self.get_engine(engine_name, voice)
        if not engine:
            return False
        
        return engine.synthesize(text, output_path)
    
    def get_available_engines(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available engines"""
        info = {}
        for name, engine in self.engines.items():
            info[name] = engine.get_engine_info()
        return info
    
    def get_engine_voices(self, engine_name: str) -> List[str]:
        """Get available voices for a specific engine"""
        engine = self.get_engine(engine_name)
        if engine:
            return engine.get_available_voices()
        return [] 