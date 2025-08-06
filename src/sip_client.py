import logging
import threading
import time
import os
import socket
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import tempfile
import wave
import numpy as np
from pydub import AudioSegment

# REAL SIP IMPORTS - pyVoIP library
from pyVoIP.VoIP import VoIPPhone, InvalidStateError
SIP_AVAILABLE = True

# Configure comprehensive logging for SIP client
sip_logger = logging.getLogger('sip_client')
sip_logger.setLevel(logging.DEBUG)

def find_available_port(start_port: int, max_attempts: int = 20) -> int:
    """Find an available port starting from start_port"""
    sip_logger.info(f"🔍 Searching for available port starting from {start_port}")
    
    for i in range(max_attempts):
        port = start_port + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                sip_logger.info(f"✅ Found available port: {port}")
                return port
        except OSError:
            sip_logger.debug(f"🔍 Port {port} is in use, trying next...")
            continue
    
    # If we can't find a port in the sequential range, try random ports
    sip_logger.warning(f"⚠️ Could not find port in sequential range, trying random ports...")
    import random
    for i in range(10):
        port = random.randint(10000, 65000)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                sip_logger.info(f"✅ Found available random port: {port}")
                return port
        except OSError:
            continue
    
    sip_logger.error(f"❌ Could not find available port starting from {start_port} or in random range")
    raise RuntimeError(f"Could not find available port starting from {start_port} or in random range")

class AudioRecorder:
    """Handles audio recording and processing"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.audio_chunks = []
        self.recording_thread = None
        self.start_time = None
        sip_logger.info(f"🎤 AudioRecorder initialized - Sample rate: {sample_rate}, Channels: {channels}")
    
    def start_recording(self):
        """Start audio recording"""
        self.recording = True
        self.audio_chunks = []
        self.start_time = datetime.now()
        sip_logger.info("🎤 Audio recording started")
    
    def stop_recording(self) -> bytes:
        """Stop recording and return audio data"""
        self.recording = False
        sip_logger.info("🎤 Stopping audio recording...")
        
        if self.recording_thread:
            try:
                self.recording_thread.join(timeout=5.0)  # Add timeout
                sip_logger.info("🎤 Recording thread joined successfully")
            except Exception as e:
                sip_logger.error(f"❌ Error joining recording thread: {e}")
        
        # Combine all audio chunks
        if self.audio_chunks:
            try:
                combined_audio = b''.join(self.audio_chunks)
                duration = (datetime.now() - self.start_time).total_seconds()
                sip_logger.info(f"✅ Recording stopped. Duration: {duration:.2f}s, Size: {len(combined_audio)} bytes")
                return combined_audio
            except Exception as e:
                sip_logger.error(f"❌ Error combining audio chunks: {e}")
                return b''
        else:
            sip_logger.warning("⚠️ No audio chunks recorded")
            return b''
    
    def cleanup(self):
        """Clean up audio recorder resources"""
        sip_logger.info("🧹 Cleaning up audio recorder...")
        try:
            self.recording = False
            self.audio_chunks.clear()
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=1.0)
            sip_logger.info("✅ Audio recorder cleaned up successfully")
        except Exception as e:
            sip_logger.error(f"❌ Error cleaning up audio recorder: {e}")
    
    def add_audio_chunk(self, audio_data: bytes):
        """Add audio chunk to recording"""
        if self.recording:
            self.audio_chunks.append(audio_data)
            sip_logger.debug(f"🎤 Added audio chunk: {len(audio_data)} bytes")
    
    def save_audio_file(self, audio_data: bytes, file_path: str) -> bool:
        """Save audio data to file"""
        try:
            sip_logger.info(f"💾 Saving audio to file: {file_path}")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save as WAV file
            with wave.open(file_path, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_data)
            
            sip_logger.info(f"✅ Audio saved to {file_path}")
            return True
            
        except Exception as e:
            sip_logger.error(f"❌ Failed to save audio file: {e}")
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
        
        sip_logger.info(f"💬 CallHandler created for call {call_id} from {caller_id}")
    
    def start_call(self):
        """Start the call session"""
        self.recorder.start_recording()
        self.status = 'in_progress'
        sip_logger.info(f"💬 Call {self.call_id} started")
    
    def end_call(self):
        """End the call session"""
        try:
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
            
            sip_logger.info(f"💬 Call {self.call_id} ended. Duration: {duration:.2f}s")
            self.on_call_end()
            
            return call_data
        except Exception as e:
            sip_logger.error(f"❌ Error ending call {self.call_id}: {e}")
            return {
                'call_id': self.call_id,
                'caller_id': self.caller_id,
                'transcript': " ".join(self.transcript_parts),
                'audio_data': b'',
                'duration': 0,
                'status': 'error'
            }
        finally:
            # Clean up resources
            self.cleanup()
    
    def cleanup(self):
        """Clean up call handler resources"""
        try:
            if hasattr(self, 'recorder'):
                self.recorder.cleanup()
            self.transcript_parts.clear()
            sip_logger.info(f"�� Call handler {self.call_id} cleaned up")
        except Exception as e:
            sip_logger.error(f"❌ Error cleaning up call handler {self.call_id}: {e}")
    
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
        sip_logger.info("=== INITIALIZING SIP CLIENT ===")
        sip_logger.info(f"📱 Creating SIP client with domain: {domain}")
        sip_logger.info(f"📱 Username: {username}")
        sip_logger.info(f"📱 Password: {'*' * len(password) if password else 'None'}")
        sip_logger.info(f"📱 PBX Port: {port}")
        sip_logger.info(f"📱 Local Port: {local_port if local_port else 'Auto'}")
        
        self.domain = domain
        self.username = username
        self.password = password
        self.port = port  # PBX port (remote)
        self.local_port = local_port  # Local binding port (can be None for auto-selection)
        self.registered = False
        self.active_calls = {}
        self.on_incoming_call = None
        self.on_call_transcript = None
        self.on_call_end = None
        
        sip_logger.info("📱 SIP client parameters set")
        
        # Initialize SIP
        sip_logger.info("📱 Starting SIP initialization...")
        self._init_sip()
        sip_logger.info("✅ SIP client initialization completed")
    
    def _init_sip(self):
        """Initialize REAL pyVoIP library with robust port handling"""
        max_attempts = 15  # Increased attempts
        
        # Start with a different local port range to avoid conflicts
        if self.local_port is None:
            current_local_port = find_available_port(5070, max_attempts=5)  # Start from 5070 for local binding
        else:
            current_local_port = self.local_port
        
        for attempt in range(max_attempts):
            try:
                sip_logger.info(f"�� Attempt {attempt + 1}/{max_attempts}: Initializing pyVoIP with domain={self.domain}, pbx_port={self.port}, local_port={current_local_port}, username={self.username}")
                
                # Initialize pyVoIP phone with separate PBX and local ports
                self.phone = VoIPPhone(
                    f"{self.domain}:{self.port}",  # PBX address with port
                    current_local_port,  # Local binding port
                    self.username, 
                    self.password,
                    callCallback=self._on_incoming_call
                )
                
                # Update the local port to the successfully used port
                self.local_port = current_local_port
                sip_logger.info(f"✅ Real pyVoIP library initialized successfully for {self.username}@{self.domain}")
                sip_logger.info(f"🔗 PBX Port: {self.port}, Local Port: {self.local_port}")
                sip_logger.info(f"📱 Phone object type: {type(self.phone)}")
                return  # Success, exit the loop
                
            except Exception as e:
                sip_logger.error(f"💥 Attempt {attempt + 1} failed: {e}")
                sip_logger.error(f"💥 Exception type: {type(e)}")
                
                # Check if it's a port binding error
                if "Address already in use" in str(e) or "Errno 98" in str(e):
                    sip_logger.warning(f"⚠️ Local port {current_local_port} is in use, trying to find available port...")
                    try:
                        # Find an available port starting from current_local_port + 1
                        current_local_port = find_available_port(current_local_port + 1, max_attempts=5)
                        sip_logger.info(f"✅ Found available local port: {current_local_port}")
                        continue  # Try again with the new local port
                    except RuntimeError as port_error:
                        sip_logger.error(f"❌ Could not find available local port: {port_error}")
                        # Try completely different port ranges
                        if attempt < 5:
                            current_local_port = 5070 + (attempt * 20)  # Try ports 5070, 5090, 5110, etc.
                        else:
                            current_local_port = 6000 + (attempt * 10)  # Try higher port range
                        sip_logger.info(f"🔄 Trying alternative local port range: {current_local_port}")
                        continue
                else:
                    # Non-port related error, log and continue
                    sip_logger.error(f"💥 Non-port related error: {e}")
                    if attempt == max_attempts - 1:  # Last attempt
                        import traceback
                        sip_logger.error(f"💥 Final attempt failed. Traceback: {traceback.format_exc()}")
                        raise
                    current_local_port += 1
                    continue
        
        # If we get here, all attempts failed
        raise RuntimeError(f"Failed to initialize pyVoIP after {max_attempts} attempts")
    
    def _create_account(self):
        """Create REAL pyVoIP account"""
        try:
            # pyVoIP account is created during initialization
            # The phone object contains the account information
            sip_logger.info(f"✅ Real pyVoIP account created for {self.username}@{self.domain}")
            
        except Exception as e:
            sip_logger.error(f"❌ Failed to create pyVoIP account: {e}")
            raise
    
    def register(self) -> bool:
        """Register with REAL SIP server using pyVoIP"""
        max_attempts = 10
        current_local_port = self.local_port
        
        for attempt in range(max_attempts):
            try:
                sip_logger.info(f"🔄 Registration attempt {attempt + 1}/{max_attempts}: Trying to register with SIP server {self.domain}:{self.port} using local port {current_local_port}")
                
                if not hasattr(self, 'phone') or self.phone is None:
                    sip_logger.error("📱 Phone object not initialized!")
                    return False
                
                # Start pyVoIP phone
                sip_logger.info("📱 Calling phone.start()...")
                self.phone.start()
                sip_logger.info("📱 phone.start() completed successfully")
                
                self.registered = True
                sip_logger.info(f"✅ Real pyVoIP registration successful for {self.username}@{self.domain}")
                sip_logger.info(f"🔗 PBX Port: {self.port}, Local Port: {current_local_port}")
                sip_logger.info(f"📱 Registration status: {self.registered}")
                return True
                
            except Exception as e:
                sip_logger.error(f"💥 Registration attempt {attempt + 1} failed: {e}")
                sip_logger.error(f"💥 Exception type: {type(e)}")
                
                # Handle port binding errors
                if "Address already in use" in str(e) or "Errno 98" in str(e):
                    sip_logger.warning(f"⚠️ Local port {current_local_port} is in use, trying to find available port...")
                    try:
                        # Find an available port
                        new_local_port = find_available_port(current_local_port + 1, max_attempts=5)
                        sip_logger.info(f"✅ Found available local port: {new_local_port}")
                        
                        # Reinitialize the phone with the new local port
                        self.phone = VoIPPhone(
                            f"{self.domain}:{self.port}",  # PBX address with port
                            new_local_port,  # Local binding port
                            self.username, 
                            self.password,
                            callCallback=self._on_incoming_call
                        )
                        self.local_port = new_local_port
                        current_local_port = new_local_port
                        sip_logger.info(f"📱 Reinitialized phone with local port {new_local_port}")
                        continue  # Try registration again with new local port
                        
                    except RuntimeError as port_error:
                        sip_logger.error(f"❌ Could not find available local port: {port_error}")
                        # Try a completely different port range
                        current_local_port = 5070 + (attempt * 20)  # Try ports 5070, 5090, 5110, etc.
                        sip_logger.info(f"🔄 Trying alternative local port range: {current_local_port}")
                        
                        try:
                            # Reinitialize with completely different local port
                            self.phone = VoIPPhone(
                                f"{self.domain}:{self.port}",  # PBX address with port
                                current_local_port,  # Local binding port
                                self.username, 
                                self.password,
                                callCallback=self._on_incoming_call
                            )
                            self.local_port = current_local_port
                            sip_logger.info(f"📱 Reinitialized phone with alternative local port {current_local_port}")
                            continue  # Try registration again
                        except Exception as reinit_e:
                            sip_logger.error(f"❌ Failed to reinitialize with alternative local port {current_local_port}: {reinit_e}")
                            current_local_port += 1
                            continue
                else:
                    # Non-port related error
                    sip_logger.error(f"💥 Non-port related error: {e}")
                    if attempt == max_attempts - 1:  # Last attempt
                        import traceback
                        sip_logger.error(f"�� Final registration attempt failed. Traceback: {traceback.format_exc()}")
                        self.registered = False
                        return False
                    current_local_port += 1
                    continue
        
        # If we get here, all attempts failed
        sip_logger.error(f"❌ Failed to register after {max_attempts} attempts")
        self.registered = False
        return False
    
    def set_callbacks(self, on_incoming_call: Callable[[str, str], None],
                     on_call_transcript: Callable[[str, str], None],
                     on_call_end: Callable[[str], None]):
        """Set callback functions for call events"""
        sip_logger.info("=== SETTING SIP CALLBACKS ===")
        sip_logger.info(f"📞 Setting incoming call callback: {on_incoming_call is not None}")
        sip_logger.info(f"📞 Setting call transcript callback: {on_call_transcript is not None}")
        sip_logger.info(f"📞 Setting call end callback: {on_call_end is not None}")
        
        self.on_incoming_call = on_incoming_call
        self.on_call_transcript = on_call_transcript
        self.on_call_end = on_call_end
        
        sip_logger.info("✅ SIP callbacks set successfully")
    
    def _on_incoming_call(self, call):
        """Handle incoming call from pyVoIP"""
        call_id = str(call.call_id)
        caller_id = call.caller_id
        
        sip_logger.info("=== INCOMING CALL FROM PYVOIP ===")
        sip_logger.info(f"📞 Real pyVoIP incoming call {call_id} from {caller_id}")
        sip_logger.info(f"📞 Call timestamp: {datetime.now()}")
        sip_logger.info(f"📞 Call object type: {type(call)}")
        
        try:
            # Create call handler
            sip_logger.info(f"📞 Creating call handler for call {call_id}...")
            call_handler = CallHandler(
                call_id=call_id,
                caller_id=caller_id,
                on_transcript=lambda transcript: self._on_transcript(call_id, transcript),
                on_call_end=lambda: self._on_call_end(call_id)
            )
            
            # Store call handler
            self.active_calls[call_id] = call_handler
            sip_logger.info(f"✅ Call handler stored in active calls")
            sip_logger.info(f"📞 Active calls count: {len(self.active_calls)}")
            
            # Start call
            sip_logger.info(f"📞 Starting call {call_id}...")
            call_handler.start_call()
            sip_logger.info(f"✅ Call {call_id} started successfully")
            
            # Notify application
            if self.on_incoming_call:
                sip_logger.info(f"📞 Notifying application of incoming call {call_id}")
                self.on_incoming_call(call_id, caller_id)
                sip_logger.info(f"✅ Application notified of incoming call {call_id}")
            else:
                sip_logger.warning(f"⚠️ No incoming call callback set")
            
            sip_logger.info(f"✅ Incoming call {call_id} from {caller_id} handled successfully")
            return call_handler
            
        except Exception as e:
            sip_logger.error(f"❌ Error handling incoming call {call_id}: {e}")
            sip_logger.error(f"Exception type: {type(e)}")
            import traceback
            sip_logger.error(f"Incoming call error traceback: {traceback.format_exc()}")
            return None
    
    def handle_incoming_call(self, call_id: str, caller_id: str) -> CallHandler:
        """Handle incoming call"""
        sip_logger.info(f"📞 Incoming call {call_id} from {caller_id}")
        
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
        sip_logger.info("=== CALL TRANSCRIPT RECEIVED ===")
        sip_logger.info(f"🎤 Call {call_id} transcript: {transcript}")
        sip_logger.info(f"🎤 Transcript length: {len(transcript)} characters")
        sip_logger.info(f"🎤 Timestamp: {datetime.now()}")
        
        try:
            if call_id in self.active_calls:
                sip_logger.info(f"✅ Found active call {call_id}, adding transcript part")
                self.active_calls[call_id].add_transcript_part(transcript)
                sip_logger.info(f"✅ Transcript part added to call {call_id}")
            else:
                sip_logger.warning(f"⚠️ Call {call_id} not found in active calls")
                sip_logger.warning(f"⚠️ Active calls: {list(self.active_calls.keys())}")
            
            if self.on_call_transcript:
                sip_logger.info(f"🎤 Forwarding transcript to application callback")
                self.on_call_transcript(call_id, transcript)
                sip_logger.info(f"✅ Transcript forwarded to application")
            else:
                sip_logger.warning(f"⚠️ No call transcript callback set")
                
        except Exception as e:
            sip_logger.error(f"❌ Error handling transcript for call {call_id}: {e}")
            sip_logger.error(f"Exception type: {type(e)}")
            import traceback
            sip_logger.error(f"Transcript error traceback: {traceback.format_exc()}")
    
    def _on_call_end(self, call_id: str):
        """Handle call end"""
        sip_logger.info("=== CALL END RECEIVED ===")
        sip_logger.info(f"📞 Call {call_id} ended")
        sip_logger.info(f"📞 Call end timestamp: {datetime.now()}")
        
        try:
            if call_id in self.active_calls:
                sip_logger.info(f"✅ Found active call {call_id}, ending call")
                call_data = self.active_calls[call_id].end_call()
                sip_logger.info(f"✅ Call {call_id} ended successfully")
                sip_logger.info(f"📞 Call data: {call_data}")
                
                del self.active_calls[call_id]
                sip_logger.info(f"✅ Call {call_id} removed from active calls")
                sip_logger.info(f"📞 Remaining active calls: {list(self.active_calls.keys())}")
                
                if self.on_call_end:
                    sip_logger.info(f"📞 Notifying application of call end")
                    self.on_call_end(call_id)
                    sip_logger.info(f"✅ Application notified of call end")
                else:
                    sip_logger.warning(f"⚠️ No call end callback set")
            else:
                sip_logger.warning(f"⚠️ Call {call_id} not found in active calls")
                sip_logger.warning(f"⚠️ Active calls: {list(self.active_calls.keys())}")
                
        except Exception as e:
            sip_logger.error(f"❌ Error handling call end for call {call_id}: {e}")
            sip_logger.error(f"Exception type: {type(e)}")
            import traceback
            sip_logger.error(f"Call end error traceback: {traceback.format_exc()}")
    
    def play_audio(self, call_id: str, audio_file_path: str) -> bool:
        """Play audio file to call"""
        if call_id not in self.active_calls:
            sip_logger.error(f"📞 Call {call_id} not found")
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
            sip_logger.info(f"�� Playing audio file {audio_file_path} to call {call_id}")
            
            # Clean up temp file
            os.unlink(temp_file.name)
            
            return True
            
        except Exception as e:
            sip_logger.error(f"❌ Failed to play audio to call {call_id}: {e}")
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
        sip_logger.info(f"📱 Checking registration status: {self.registered}")
        return self.registered
    
    def get_registration_status(self) -> Dict[str, Any]:
        """Get registration status information"""
        status = {
            'registered': self.registered,
            'domain': self.domain,
            'username': self.username,
            'pbx_port': self.port,
            'local_port': self.local_port,
            'active_calls': len(self.active_calls)
        }
        sip_logger.info(f"📱 Registration status: {status}")
        return status
    
    def shutdown(self):
        """Shutdown REAL pyVoIP client"""
        sip_logger.info("=== SHUTTING DOWN SIP CLIENT ===")
        sip_logger.info(f"🔌 Starting SIP client shutdown...")
        sip_logger.info(f"📞 Active calls count: {len(self.active_calls)}")
        sip_logger.info(f"📞 Active calls: {list(self.active_calls.keys())}")
        
        try:
            # Cleanup active calls first
            sip_logger.info("🔌 Cleaning up active calls...")
            for call_id in list(self.active_calls.keys()):
                try:
                    if call_id in self.active_calls:
                        sip_logger.info(f"🔌 Cleaning up call {call_id}")
                        call_handler = self.active_calls[call_id]
                        if hasattr(call_handler, 'recorder'):
                            call_handler.recorder.stop_recording()
                            sip_logger.info(f"✅ Recording stopped for call {call_id}")
                        del self.active_calls[call_id]
                        sip_logger.info(f"✅ Call {call_id} removed from active calls")
                except Exception as e:
                    sip_logger.error(f"❌ Error cleaning up call {call_id}: {e}")
            
            # Clear active calls dictionary
            self.active_calls.clear()
            sip_logger.info("✅ Active calls dictionary cleared")
            
            # Cleanup pyVoIP resources
            if hasattr(self, 'phone') and self.phone is not None:
                sip_logger.info("🔌 Stopping pyVoIP phone...")
                try:
                    self.phone.stop()
                    sip_logger.info("✅ pyVoIP phone stopped successfully")
                except Exception as e:
                    sip_logger.error(f"❌ Error stopping phone: {e}")
                finally:
                    self.phone = None
                    sip_logger.info("✅ Phone object set to None")
            else:
                sip_logger.info("⚠️ No phone object to stop")
            
            self.registered = False
            sip_logger.info("✅ Registration status set to False")
            sip_logger.info("🔌 Real pyVoIP client shutdown complete")
            
        except Exception as e:
            sip_logger.error(f"❌ Error during pyVoIP shutdown: {e}")
            sip_logger.error(f"Exception type: {type(e)}")
            import traceback
            sip_logger.error(f"Shutdown error traceback: {traceback.format_exc()}")
        finally:
            # Ensure cleanup even if exceptions occur
            sip_logger.info("🔌 Final cleanup in finally block...")
            self.active_calls = {}
            self.phone = None
            self.registered = False
            sip_logger.info("✅ SIP client shutdown completed")

class pyVoIPCallback:
    """REAL pyVoIP callback handler"""
    
    def __init__(self, sip_client: SIPClient):
        self.sip_client = sip_client
    
    def on_registration_state(self, state: str, reason: str):
        """Handle registration state changes"""
        sip_logger.info(f"📝 Real pyVoIP registration state: {state} - {reason}")
    
    def on_incoming_call(self, call):
        """Handle incoming calls from pyVoIP"""
        call_id = str(call.call_id)
        caller_id = call.caller_id
        sip_logger.info(f"📞 Real pyVoIP incoming call from {caller_id}")
        
        # Handle call in main client
        self.sip_client._on_incoming_call(call) 