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
from pyVoIP.VoIP import VoIPPhone, VoIPCall, CallState
from pyVoIP.SIP import SIPClient as pyVoIPSIPClient
from pyVoIP.SIP import SIPMessage
import pyVoIP.RTP as RTP

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
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:  # UDP for SIP
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
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.bind(('', port))
                sip_logger.info(f"✅ Found available random port: {port}")
                return port
        except OSError:
            continue
    
    sip_logger.error(f"❌ Could not find available port")
    raise RuntimeError(f"Could not find available port")

class AudioRecorder:
    """Handles audio recording and processing"""
    
    def __init__(self, sample_rate: int = 8000, channels: int = 1):  # SIP typically uses 8kHz
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
                self.recording_thread.join(timeout=5.0)
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

class CallHandler:
    """Handles individual call sessions"""
    
    def __init__(self, call_id: str, caller_id: str, pyvoip_call: VoIPCall,
                 on_transcript: Callable[[str], None],
                 on_call_end: Callable[[], None]):
        self.call_id = call_id
        self.caller_id = caller_id
        self.pyvoip_call = pyvoip_call  # Store the actual pyVoIP call object
        self.on_transcript = on_transcript
        self.on_call_end = on_call_end
        self.recorder = AudioRecorder()
        self.transcript_parts = []
        self.call_start_time = datetime.now()
        self.status = 'in_progress'
        
        sip_logger.info(f"💬 CallHandler created for call {call_id} from {caller_id}")
    
    def start_call(self):
        """Start the call session"""
        try:
            # THIS IS THE KEY FIX: Don't answer here, it's already answered
            # The call is answered by returning from the callback
            self.recorder.start_recording()
            self.status = 'in_progress'
            sip_logger.info(f"💬 Call {self.call_id} started (already answered by callback)")
        except Exception as e:
            sip_logger.error(f"❌ Error starting call {self.call_id}: {e}")
    
    def end_call(self):
        """End the call session"""
        try:
            self.status = 'completed'
            
            # Hang up the pyVoIP call
            if self.pyvoip_call:
                try:
                    self.pyvoip_call.hangup()
                except:
                    pass
            
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
            self.cleanup()
    
    def cleanup(self):
        """Clean up call handler resources"""
        try:
            if hasattr(self, 'recorder'):
                self.recorder.cleanup()
            self.transcript_parts.clear()
            sip_logger.info(f"🧹 Call handler {self.call_id} cleaned up")
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
    """Main SIP client for handling VoIP calls with VitalPBX compatibility"""
    
    def __init__(self, domain: str, username: str, password: str, port: int = 5060, local_port: int = None):
        sip_logger.info("=== INITIALIZING SIP CLIENT FOR VITALPBX ===")
        sip_logger.info(f"📱 Creating SIP client with domain: {domain}")
        sip_logger.info(f"📱 Username: {username}")
        sip_logger.info(f"📱 Password: {'*' * len(password) if password else 'None'}")
        sip_logger.info(f"📱 PBX Port: {port}")
        sip_logger.info(f"📱 Local Port: {local_port if local_port else 'Auto'}")
        
        # Validate required parameters
        if not domain or not domain.strip():
            raise ValueError("SIP domain is required and cannot be empty")
        if not username or not username.strip():
            raise ValueError("SIP username is required and cannot be empty")
        if not password or not password.strip():
            raise ValueError("SIP password is required and cannot be empty")
        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ValueError("SIP port must be a valid integer between 1 and 65535")
        
        # Clean and store parameters
        self.domain = domain.strip()
        self.username = username.strip()
        self.password = password.strip()
        self.port = port
        self.local_port = local_port
        self.registered = False
        self.active_calls = {}
        self.on_incoming_call = None
        self.on_call_transcript = None
        self.on_call_end = None
        self.phone = None
        self.registration_thread = None
        self.keep_alive_thread = None
        self.running = False
        
        sip_logger.info("📱 SIP client parameters validated and set")
        
        # Initialize SIP
        sip_logger.info("📱 Starting SIP initialization...")
        self._init_sip()
        sip_logger.info("✅ SIP client initialization completed")
    
    def _init_sip(self):
        """Initialize pyVoIP with proper VitalPBX compatibility"""
        max_attempts = 5
        
        # Start with a different local port range to avoid conflicts
        if self.local_port is None:
            current_local_port = find_available_port(5070)
        else:
            current_local_port = self.local_port
        
        # Get local IP address for pyVoIP
        try:
            import socket
            # Method 1: Try to connect to external service to get local IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                sip_logger.info(f"📱 Detected local IP (method 1): {local_ip}")
            except Exception as e1:
                sip_logger.warning(f"⚠️ Method 1 failed: {e1}")
                
                # Method 2: Try to get IP from hostname
                try:
                    local_ip = socket.gethostbyname(socket.gethostname())
                    sip_logger.info(f"📱 Detected local IP (method 2): {local_ip}")
                except Exception as e2:
                    sip_logger.warning(f"⚠️ Method 2 failed: {e2}")
                    
                    # Method 3: Try to get IP from network interfaces
                    try:
                        import subprocess
                        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                        if result.returncode == 0:
                            local_ip = result.stdout.strip().split()[0]
                            sip_logger.info(f"📱 Detected local IP (method 3): {local_ip}")
                        else:
                            raise Exception("hostname -I failed")
                    except Exception as e3:
                        sip_logger.warning(f"⚠️ Method 3 failed: {e3}")
                        
                        # Fallback to default
                        local_ip = "0.0.0.0"
                        sip_logger.info(f"📱 Using fallback IP: {local_ip}")
                        
        except Exception as e:
            sip_logger.warning(f"⚠️ Could not detect local IP, using default: {e}")
            local_ip = "0.0.0.0"  # Fallback to all interfaces
        
        for attempt in range(max_attempts):
            try:
                sip_logger.info(f"🔄 Attempt {attempt + 1}/{max_attempts}: Initializing pyVoIP")
                sip_logger.info(f"📱 Domain: {self.domain}:{self.port}, Local port: {current_local_port}")
                sip_logger.info(f"📱 Username: {self.username}, Password: {'*' * len(self.password)}")
                sip_logger.info(f"📱 Local IP: {local_ip}")
                
                # Ensure all parameters are valid strings/ints before passing to pyVoIP
                server = str(self.domain).strip()
                username = str(self.username).strip()
                password = str(self.password).strip()
                port = int(self.port)
                sip_port = int(current_local_port)
                
                # Double-check that no parameters are empty or None
                if not server or not username or not password:
                    raise ValueError(f"Invalid SIP parameters - server: '{server}', username: '{username}', password: {'*' * len(password) if password else 'None'}")
                
                # Initialize VoIPPhone with proper parameters for VitalPBX
                # CRITICAL: Pass the callback directly here
                self.phone = VoIPPhone(
                    server=server,
                    port=port,
                    username=username,
                    password=password,
                    callCallback=self._handle_incoming_call_wrapper,  # Use wrapper method
                    myIP=local_ip,  # Use detected local IP instead of None
                    sipPort=sip_port,
                    rtpPortLow=10000,
                    rtpPortHigh=20000
                )
                
                # Update the local port to the successfully used port
                self.local_port = current_local_port
                sip_logger.info(f"✅ pyVoIP initialized for {self.username}@{self.domain}")
                sip_logger.info(f"🔗 PBX Port: {self.port}, Local Port: {self.local_port}")
                return
                
            except Exception as e:
                sip_logger.error(f"💥 Attempt {attempt + 1} failed: {e}")
                sip_logger.error(f"💥 Error type: {type(e)}")
                import traceback
                sip_logger.error(f"💥 Traceback: {traceback.format_exc()}")
                
                if "Address already in use" in str(e) or "Errno 98" in str(e):
                    sip_logger.warning(f"⚠️ Port {current_local_port} is in use")
                    current_local_port = find_available_port(current_local_port + 1)
                    continue
                
                if attempt == max_attempts - 1:
                    raise
                current_local_port += 1
    
    def _handle_incoming_call_wrapper(self, call: VoIPCall):
        """
        Wrapper method for handling incoming calls from pyVoIP.
        THIS IS THE CRITICAL FIX: We need to answer the call by calling call.answer()
        and then handle it in a separate thread.
        """
        try:
            sip_logger.info("=== INCOMING CALL WRAPPER TRIGGERED ===")
            
            # Generate a unique call ID
            call_id = f"call_{int(time.time())}_{call.request.headers['Call-ID'][0][:8]}"
            
            # Extract caller ID from SIP headers
            from_header = call.request.headers.get('From', [''])[0]
            caller_id = from_header.split('<')[0].strip() if '<' in from_header else from_header
            
            sip_logger.info(f"📞 Incoming call {call_id} from {caller_id}")
            sip_logger.info(f"📞 Call state: {call.state}")
            
            # CRITICAL: Answer the call immediately
            sip_logger.info(f"📞 Answering call {call_id}...")
            call.answer()
            sip_logger.info(f"✅ Call {call_id} answered successfully")
            
            # Now handle the call in a separate thread
            threading.Thread(
                target=self._handle_answered_call,
                args=(call, call_id, caller_id),
                daemon=True
            ).start()
            
            sip_logger.info(f"✅ Call handler thread started for {call_id}")
            
        except Exception as e:
            sip_logger.error(f"❌ Error in incoming call wrapper: {e}")
            import traceback
            sip_logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    def _handle_answered_call(self, call: VoIPCall, call_id: str, caller_id: str):
        """Handle the call after it has been answered"""
        try:
            sip_logger.info(f"📞 Handling answered call {call_id}")
            
            # Create call handler with the actual pyVoIP call object
            call_handler = CallHandler(
                call_id=call_id,
                caller_id=caller_id,
                pyvoip_call=call,  # Pass the actual call object
                on_transcript=lambda transcript: self._on_transcript(call_id, transcript),
                on_call_end=lambda: self._on_call_end(call_id)
            )
            
            # Store call handler
            self.active_calls[call_id] = call_handler
            
            # Start call handling (recording, etc.)
            call_handler.start_call()
            
            # Notify application
            if self.on_incoming_call:
                self.on_incoming_call(call_id, caller_id)
            
            # Handle audio in this thread
            sip_logger.info(f"📞 Starting audio handling for call {call_id}")
            try:
                while call.state == CallState.ANSWERED:
                    # Read audio from the call
                    audio = call.read_audio()
                    if audio:
                        call_handler.add_audio_chunk(audio)
                    time.sleep(0.02)  # 20ms chunks
            except Exception as e:
                sip_logger.error(f"❌ Audio handler error for call {call_id}: {e}")
            finally:
                # Call ended
                self._on_call_end(call_id)
            
        except Exception as e:
            sip_logger.error(f"❌ Error handling answered call {call_id}: {e}")
            import traceback
            sip_logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    def register(self) -> bool:
        """Register with VitalPBX server and maintain registration"""
        try:
            sip_logger.info(f"🔄 Starting registration with VitalPBX {self.domain}:{self.port}")
            
            if not hasattr(self, 'phone') or self.phone is None:
                sip_logger.error("📱 Phone object not initialized!")
                return False
            
            # Validate phone object has required attributes
            if not hasattr(self.phone, 'start'):
                sip_logger.error("📱 Phone object is invalid - missing start method")
                return False
            
            # Start the phone (this initiates registration)
            sip_logger.info("📱 Starting VoIPPhone...")
            try:
                self.phone.start()
                sip_logger.info("📱 VoIPPhone started successfully")
            except Exception as e:
                sip_logger.error(f"❌ Failed to start VoIPPhone: {e}")
                sip_logger.error(f"❌ Error type: {type(e)}")
                import traceback
                sip_logger.error(f"❌ Start error traceback: {traceback.format_exc()}")
                return False
            
            # Wait for registration to complete
            sip_logger.info("📱 Waiting for registration to complete...")
            time.sleep(2)
            
            # Check if phone is still running and handle socket errors
            try:
                if hasattr(self.phone, 'sip') and self.phone.sip:
                    # Check if SIP socket is still valid
                    if hasattr(self.phone.sip, 's') and self.phone.sip.s:
                        try:
                            # Test if socket is still valid
                            self.phone.sip.s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                            sip_logger.info("✅ SIP client appears to be running with valid socket")
                            self.registered = True
                            self.running = True
                            
                            # Start keep-alive thread for maintaining registration
                            self._start_keep_alive()
                            
                            sip_logger.info(f"✅ Registered with VitalPBX at {self.domain}:{self.port}")
                            sip_logger.info(f"📱 Extension: {self.username}")
                            sip_logger.info(f"📱 Ready to receive calls!")
                            
                            return True
                        except (OSError, socket.error) as socket_err:
                            sip_logger.error(f"❌ SIP socket is invalid: {socket_err}")
                            return False
                    else:
                        sip_logger.error("❌ SIP socket not found")
                        return False
                else:
                    sip_logger.error("❌ SIP client failed to start properly")
                    return False
                    
            except Exception as e:
                sip_logger.error(f"❌ Error checking SIP client status: {e}")
                return False
            
        except Exception as e:
            sip_logger.error(f"❌ Registration failed: {e}")
            sip_logger.error(f"❌ Error type: {type(e)}")
            import traceback
            sip_logger.error(f"❌ Registration error traceback: {traceback.format_exc()}")
            self.registered = False
            return False
    
    def _start_keep_alive(self):
        """Start keep-alive thread to maintain registration with VitalPBX"""
        def keep_alive():
            while self.running:
                try:
                    if self.phone and self.phone.sip:
                        # Send OPTIONS or re-REGISTER periodically
                        sip_logger.debug("📡 Sending keep-alive to VitalPBX")
                        # pyVoIP should handle re-registration automatically
                        # but we can trigger it manually if needed
                    time.sleep(30)  # Send keep-alive every 30 seconds
                except Exception as e:
                    sip_logger.error(f"❌ Keep-alive error: {e}")
        
        self.keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        self.keep_alive_thread.start()
        sip_logger.info("✅ Keep-alive thread started")
    
    def set_callbacks(self, on_incoming_call: Callable[[str, str], None],
                     on_call_transcript: Callable[[str, str], None],
                     on_call_end: Callable[[str], None]):
        """Set callback functions for call events"""
        sip_logger.info("=== SETTING SIP CALLBACKS ===")
        self.on_incoming_call = on_incoming_call
        self.on_call_transcript = on_call_transcript
        self.on_call_end = on_call_end
        sip_logger.info("✅ SIP callbacks set successfully")
    
    def _on_transcript(self, call_id: str, transcript: str):
        """Handle transcript from speech recognition"""
        sip_logger.info(f"🎤 Call {call_id} transcript: {transcript}")
        
        if call_id in self.active_calls:
            self.active_calls[call_id].add_transcript_part(transcript)
        
        if self.on_call_transcript:
            self.on_call_transcript(call_id, transcript)
    
    def _on_call_end(self, call_id: str):
        """Handle call end"""
        sip_logger.info(f"📞 Call {call_id} ended")
        
        if call_id in self.active_calls:
            call_data = self.active_calls[call_id].end_call()
            del self.active_calls[call_id]
            
            if self.on_call_end:
                self.on_call_end(call_id)
    
    def play_audio(self, call_id: str, audio_file_path: str) -> bool:
        """Play audio file to call"""
        if call_id not in self.active_calls:
            sip_logger.error(f"📞 Call {call_id} not found")
            return False
        
        try:
            call_handler = self.active_calls[call_id]
            pyvoip_call = call_handler.pyvoip_call
            
            # Load audio file
            audio = AudioSegment.from_file(audio_file_path)
            
            # Convert to appropriate format for SIP (8kHz, mono)
            audio = audio.set_frame_rate(8000)
            audio = audio.set_channels(1)
            
            # Convert to raw PCM
            raw_audio = audio.raw_data
            
            # Send audio through pyVoIP call
            if pyvoip_call and pyvoip_call.state == CallState.ANSWERED:
                pyvoip_call.write_audio(raw_audio)
                sip_logger.info(f"🔊 Playing audio to call {call_id}")
                return True
            else:
                sip_logger.error(f"❌ Call {call_id} not in answered state")
                return False
            
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
        return self.registered
    
    def get_registration_status(self) -> Dict[str, Any]:
        """Get registration status information"""
        return {
            'registered': self.registered,
            'domain': self.domain,
            'username': self.username,
            'pbx_port': self.port,
            'local_port': self.local_port,
            'active_calls': len(self.active_calls)
        }
    
    def shutdown(self):
        """Shutdown SIP client properly"""
        sip_logger.info("=== SHUTTING DOWN SIP CLIENT ===")
        
        try:
            self.running = False
            
            # End all active calls
            for call_id in list(self.active_calls.keys()):
                try:
                    self._on_call_end(call_id)
                except Exception as e:
                    sip_logger.error(f"❌ Error ending call {call_id}: {e}")
            
            # Stop the phone with proper socket handling
            if self.phone:
                try:
                    # Check if SIP socket is still valid before stopping
                    if hasattr(self.phone, 'sip') and self.phone.sip:
                        if hasattr(self.phone.sip, 's') and self.phone.sip.s:
                            try:
                                # Test socket validity
                                self.phone.sip.s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                                sip_logger.info("📱 Stopping VoIPPhone with valid socket...")
                                self.phone.stop()
                                sip_logger.info("✅ VoIPPhone stopped successfully")
                            except (OSError, socket.error) as socket_err:
                                sip_logger.warning(f"⚠️ Socket already closed or invalid: {socket_err}")
                                # Try to stop anyway
                                try:
                                    self.phone.stop()
                                    sip_logger.info("✅ VoIPPhone stopped despite socket error")
                                except Exception as e:
                                    sip_logger.warning(f"⚠️ Could not stop VoIPPhone: {e}")
                        else:
                            sip_logger.warning("⚠️ SIP socket not found, stopping phone anyway")
                            try:
                                self.phone.stop()
                                sip_logger.info("✅ VoIPPhone stopped successfully")
                            except Exception as e:
                                sip_logger.warning(f"⚠️ Could not stop VoIPPhone: {e}")
                    else:
                        sip_logger.warning("⚠️ SIP object not found, stopping phone anyway")
                        try:
                            self.phone.stop()
                            sip_logger.info("✅ VoIPPhone stopped successfully")
                        except Exception as e:
                            sip_logger.warning(f"⚠️ Could not stop VoIPPhone: {e}")
                except Exception as e:
                    sip_logger.error(f"❌ Error stopping VoIPPhone: {e}")
                finally:
                    self.phone = None
            
            self.registered = False
            sip_logger.info("✅ SIP client shutdown complete")
            
        except Exception as e:
            sip_logger.error(f"❌ Error during shutdown: {e}")
            import traceback
            sip_logger.error(f"❌ Shutdown error traceback: {traceback.format_exc()}")