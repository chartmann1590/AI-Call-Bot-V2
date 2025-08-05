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

# REAL SIP IMPORTS - pyVoIP library
from pyVoIP.VoIP import VoIPPhone, InvalidStateError
import socket
import threading
import time
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
    
    def __init__(self, domain: str, username: str, password: str, port: int = 5060, local_port: int = None):
        self.domain = domain
        self.username = username
        self.password = password
        self.port = port
        self.local_port = local_port or self._find_available_port()
        self.registered = False
        self.active_calls = {}
        self.on_incoming_call = None
        self.on_call_transcript = None
        self.on_call_end = None
        
        # Initialize SIP
        self._init_sip()
    
    def _find_available_port(self) -> int:
        """Find an available port for SIP client"""
        import socket
        for port in range(5060, 5080):  # Try ports 5060-5079
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.bind(('0.0.0.0', port))
                    logger.info(f"Found available port: {port}")
                    return port
            except OSError:
                continue
        logger.warning("No available ports found in range 5060-5079, using 5060")
        return 5060
    
    def _init_sip(self):
        """Initialize REAL pyVoIP library"""
        try:
            logger.info(f"Initializing pyVoIP with domain={self.domain}, port={self.port}, local_port={self.local_port}, username={self.username}")
            
            # Initialize pyVoIP phone with local port
            self.phone = VoIPPhone(
                self.domain, 
                self.port, 
                self.username, 
                self.password,
                callCallback=self._on_incoming_call,
                myIP="0.0.0.0",
                myPort=self.local_port
            )
            logger.info(f"Real pyVoIP library initialized successfully for {self.username}@{self.domain} on local port {self.local_port}")
            logger.info(f"Phone object type: {type(self.phone)}")
            logger.info(f"Phone object attributes: {dir(self.phone)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize pyVoIP: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _create_account(self):
        """Create REAL pyVoIP account"""
        try:
            # pyVoIP account is created during initialization
            # The phone object contains the account information
            logger.info(f"Real pyVoIP account created for {self.username}@{self.domain}")
            
        except Exception as e:
            logger.error(f"Failed to create pyVoIP account: {e}")
            raise
    
    def register(self) -> bool:
        """Register with REAL SIP server using pyVoIP"""
        try:
            logger.info(f"Attempting to register with SIP server {self.domain}:{self.port}")
            logger.info(f"Phone object exists: {hasattr(self, 'phone')}")
            logger.info(f"Phone object: {self.phone}")
            
            if not hasattr(self, 'phone') or self.phone is None:
                logger.error("Phone object not initialized!")
                return False
            
            # Start pyVoIP phone
            logger.info("Calling phone.start()...")
            self.phone.start()
            logger.info("phone.start() completed successfully")
            
            self.registered = True
            logger.info(f"Real pyVoIP registration successful for {self.username}@{self.domain}")
            logger.info(f"Registration status: {self.registered}")
            return True
            
        except Exception as e:
            logger.error(f"Real pyVoIP registration failed for {self.username}@{self.domain}: {e}")
            logger.error(f"Exception type: {type(e)}")
            
            # Handle specific port binding errors
            if "Address already in use" in str(e) or "Errno 98" in str(e):
                logger.error("Port binding error - trying to find another available port")
                try:
                    # Try to find another available port
                    old_local_port = self.local_port
                    self.local_port = self._find_available_port()
                    if self.local_port != old_local_port:
                        logger.info(f"Retrying with new local port: {self.local_port}")
                        # Reinitialize with new port
                        self._init_sip()
                        self.phone.start()
                        self.registered = True
                        logger.info(f"Registration successful with new port {self.local_port}")
                        return True
                except Exception as retry_e:
                    logger.error(f"Retry with new port also failed: {retry_e}")
            
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.registered = False
            return False
    
    def set_callbacks(self, on_incoming_call: Callable[[str, str], None],
                     on_call_transcript: Callable[[str, str], None],
                     on_call_end: Callable[[str], None]):
        """Set callback functions for call events"""
        self.on_incoming_call = on_incoming_call
        self.on_call_transcript = on_call_transcript
        self.on_call_end = on_call_end
    
    def _on_incoming_call(self, call):
        """Handle incoming call from pyVoIP"""
        call_id = str(call.call_id)
        caller_id = call.caller_id
        
        logger.info(f"Real pyVoIP incoming call {call_id} from {caller_id}")
        
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
    
    def is_registered(self) -> bool:
        """Check if SIP client is registered"""
        return self.registered
    
    def get_registration_status(self) -> Dict[str, Any]:
        """Get registration status information"""
        return {
            'registered': self.registered,
            'domain': self.domain,
            'username': self.username,
            'port': self.port,
            'local_port': self.local_port,
            'active_calls': len(self.active_calls)
        }
    
    def shutdown(self):
        """Shutdown REAL pyVoIP client"""
        try:
            # Cleanup pyVoIP resources
            if hasattr(self, 'phone'):
                self.phone.stop()
            self.registered = False
            logger.info("Real pyVoIP client shutdown complete")
        except Exception as e:
            logger.error(f"Error during pyVoIP shutdown: {e}")

class pyVoIPCallback:
    """REAL pyVoIP callback handler"""
    
    def __init__(self, sip_client: SIPClient):
        self.sip_client = sip_client
    
    def on_registration_state(self, state: str, reason: str):
        """Handle registration state changes"""
        logger.info(f"Real pyVoIP registration state: {state} - {reason}")
    
    def on_incoming_call(self, call):
        """Handle incoming calls from pyVoIP"""
        call_id = str(call.call_id)
        caller_id = call.caller_id
        logger.info(f"Real pyVoIP incoming call from {caller_id}")
        
        # Handle call in main client
        self.sip_client._on_incoming_call(call) 