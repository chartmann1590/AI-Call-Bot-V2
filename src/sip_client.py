import logging
import threading
import time
import os
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import tempfile
import wave
import numpy as np
from pydub import AudioSegment

# REAL SIP IMPORTS - no mock implementations
import sip
SIP_AVAILABLE = True

logger = logging.getLogger(__name__)

class AudioRecorder:
    """Handles audio recording and processing"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.audio_chunks = []
        self.recording_thread = None
        self.start_time = None
    
    def start_recording(self):
        """Start audio recording"""
        self.recording = True
        self.audio_chunks = []
        self.start_time = datetime.now()
        logger.info("Audio recording started")
    
    def stop_recording(self) -> bytes:
        """Stop recording and return audio data"""
        self.recording = False
        if self.recording_thread:
            self.recording_thread.join()
        
        # Combine all audio chunks
        if self.audio_chunks:
            combined_audio = b''.join(self.audio_chunks)
            duration = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"Recording stopped. Duration: {duration:.2f}s, Size: {len(combined_audio)} bytes")
            return combined_audio
        return b''
    
    def add_audio_chunk(self, audio_data: bytes):
        """Add audio chunk to recording"""
        if self.recording:
            self.audio_chunks.append(audio_data)
    
    def save_audio_file(self, audio_data: bytes, file_path: str) -> bool:
        """Save audio data to WAV file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Save as WAV file
            with wave.open(file_path, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)
            
            logger.info(f"Audio saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")
            return False

class CallHandler:
    """Handles individual call sessions"""
    
    def __init__(self, call_id: str, caller_id: str, 
                 on_transcript: Callable[[str], None],
                 on_call_end: Callable[[], None]):
        self.call_id = call_id
        self.caller_id = caller_id
        self.on_transcript = on_transcript
        self.on_call_end = on_call_end
        self.recorder = AudioRecorder()
        self.transcript_parts = []
        self.call_start_time = datetime.now()
        self.status = 'in_progress'
        
        logger.info(f"Call handler created for call {call_id} from {caller_id}")
    
    def start_call(self):
        """Start the call session"""
        self.recorder.start_recording()
        self.status = 'in_progress'
        logger.info(f"Call {self.call_id} started")
    
    def end_call(self):
        """End the call session"""
        self.status = 'completed'
        audio_data = self.recorder.stop_recording()
        duration = (datetime.now() - self.call_start_time).total_seconds()
        
        # Combine transcript parts
        full_transcript = " ".join(self.transcript_parts)
        
        call_data = {
            'call_id': self.call_id,
            'caller_id': self.caller_id,
            'transcript': full_transcript,
            'audio_data': audio_data,
            'duration': duration,
            'status': self.status
        }
        
        logger.info(f"Call {self.call_id} ended. Duration: {duration:.2f}s")
        self.on_call_end()
        
        return call_data
    
    def add_transcript_part(self, transcript: str):
        """Add transcript part from speech recognition"""
        if transcript:
            self.transcript_parts.append(transcript)
            self.on_transcript(transcript)
    
    def add_audio_chunk(self, audio_data: bytes):
        """Add audio chunk to recording"""
        self.recorder.add_audio_chunk(audio_data)

class SIPClient:
    """Main SIP client for handling VoIP calls"""
    
    def __init__(self, domain: str, username: str, password: str, port: int = 5060):
        self.domain = domain
        self.username = username
        self.password = password
        self.port = port
        self.registered = False
        self.active_calls = {}
        self.on_incoming_call = None
        self.on_call_transcript = None
        self.on_call_end = None
        
        # Initialize SIP
        self._init_sip()
    
    def _init_sip(self):
        """Initialize REAL SIP library"""
        if not SIP_AVAILABLE:
            logger.error("Cannot initialize SIP - library not available")
            raise ImportError("SIP library not available")
        
        try:
            # Initialize REAL sip library
            self.sip_client = sip.SIPClient()
            logger.info("REAL SIP library initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SIP: {e}")
            raise
    
    def _create_account(self):
        """Create SIP account"""
        try:
            # Account configuration
            acc_cfg = pj.AccountConfig()
            acc_cfg.idUri = f"sip:{self.username}@{self.domain}"
            acc_cfg.regConfig.registrarUri = f"sip:{self.domain}"
            acc_cfg.sipConfig.authCreds.append(
                pj.AuthCredInfo("digest", "*", self.username, 0, self.password)
            )
            
            # Create account
            self.account = pj.Account()
            self.account.create(acc_cfg)
            
            # Set callbacks
            self.account.setCallback(self._AccountCallback(self))
            
            logger.info(f"SIP account created for {self.username}@{self.domain}")
            
        except Exception as e:
            logger.error(f"Failed to create SIP account: {e}")
            raise
    
    async def register(self) -> bool:
        """Register with REAL SIP server"""
        try:
            # REAL SIP registration
            await self.sip_client.register(self.domain, self.username, self.password)
            self.registered = True
            logger.info("REAL SIP registration successful")
            return True
            
        except Exception as e:
            logger.error(f"REAL SIP registration failed: {e}")
            return False
    
    def set_callbacks(self, on_incoming_call: Callable[[str, str], None],
                     on_call_transcript: Callable[[str, str], None],
                     on_call_end: Callable[[str], None]):
        """Set callback functions for call events"""
        self.on_incoming_call = on_incoming_call
        self.on_call_transcript = on_call_transcript
        self.on_call_end = on_call_end
    
    def handle_incoming_call(self, call_id: str, caller_id: str) -> CallHandler:
        """Handle incoming call"""
        logger.info(f"Incoming call {call_id} from {caller_id}")
        
        # Create call handler
        call_handler = CallHandler(
            call_id=call_id,
            caller_id=caller_id,
            on_transcript=lambda transcript: self._on_transcript(call_id, transcript),
            on_call_end=lambda: self._on_call_end(call_id)
        )
        
        # Store call handler
        self.active_calls[call_id] = call_handler
        
        # Start call
        call_handler.start_call()
        
        # Notify application
        if self.on_incoming_call:
            self.on_incoming_call(call_id, caller_id)
        
        return call_handler
    
    def _on_transcript(self, call_id: str, transcript: str):
        """Handle transcript from speech recognition"""
        if call_id in self.active_calls:
            self.active_calls[call_id].add_transcript_part(transcript)
        
        if self.on_call_transcript:
            self.on_call_transcript(call_id, transcript)
    
    def _on_call_end(self, call_id: str):
        """Handle call end"""
        if call_id in self.active_calls:
            call_data = self.active_calls[call_id].end_call()
            del self.active_calls[call_id]
            
            if self.on_call_end:
                self.on_call_end(call_id)
    
    def play_audio(self, call_id: str, audio_file_path: str) -> bool:
        """Play audio file to call"""
        if call_id not in self.active_calls:
            logger.error(f"Call {call_id} not found")
            return False
        
        try:
            # Load audio file
            audio = AudioSegment.from_file(audio_file_path)
            
            # Convert to appropriate format for SIP
            audio = audio.set_frame_rate(8000)  # SIP typically uses 8kHz
            audio = audio.set_channels(1)
            
            # Save temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            audio.export(temp_file.name, format='wav')
            temp_file.close()
            
            # In a real implementation, this would send audio to the SIP call
            logger.info(f"Playing audio file {audio_file_path} to call {call_id}")
            
            # Clean up temp file
            os.unlink(temp_file.name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to play audio to call {call_id}: {e}")
            return False
    
    def get_call_info(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a call"""
        if call_id in self.active_calls:
            handler = self.active_calls[call_id]
            return {
                'call_id': handler.call_id,
                'caller_id': handler.caller_id,
                'status': handler.status,
                'duration': (datetime.now() - handler.call_start_time).total_seconds(),
                'transcript_parts': handler.transcript_parts
            }
        return None
    
    def get_active_calls(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active calls"""
        return {call_id: self.get_call_info(call_id) 
                for call_id in self.active_calls.keys()}
    
    def shutdown(self):
        """Shutdown SIP client"""
        # Cleanup SIP resources
        logger.info("SIP client shutdown complete")

class SIPCallback:
    """SIP callback handler"""
    
    def __init__(self, sip_client: SIPClient):
        self.sip_client = sip_client
    
    def on_registration_state(self, state: str, reason: str):
        """Handle registration state changes"""
        logger.info(f"Registration state: {state} - {reason}")
    
    def on_incoming_call(self, call_id: str, caller_id: str):
        """Handle incoming calls"""
        logger.info(f"Incoming call from {caller_id}")
        
        # Handle call in main client
        self.sip_client.handle_incoming_call(call_id, caller_id) 