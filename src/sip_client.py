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
from pyVoIP.SIP import SIPClient as pyVoIPSIPClient, SIPStatus
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
    
    def __init__(self, sample_rate: int = 8000, channels: int = 1):
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
        self.pyvoip_call = pyvoip_call
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
            self.recorder.start_recording()
            self.status = 'in_progress'
            sip_logger.info(f"💬 Call {self.call_id} started")
        except Exception as e:
            sip_logger.error(f"❌ Error starting call {self.call_id}: {e}")
    
    def end_call(self):
        """End the call session"""
        try:
            self.status = 'completed'
            
            if self.pyvoip_call:
                try:
                    self.pyvoip_call.hangup()
                except:
                    pass
            
            audio_data = self.recorder.stop_recording()
            duration = (datetime.now() - self.call_start_time).total_seconds()
            
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
    """Main SIP client for handling VoIP calls - FIXED for Docker IP reachability issue"""
    
    def __init__(self, domain: str, username: str, password: str, port: int = 5060, local_port: int = None):
        sip_logger.info("=== INITIALIZING SIP CLIENT (DOCKER FIXED VERSION) ===")
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
        self.options_thread = None
        self.running = False
        
        sip_logger.info("📱 SIP client parameters validated and set")
        
        # Initialize SIP
        sip_logger.info("📱 Starting SIP initialization...")
        self._init_sip()
        sip_logger.info("✅ SIP client initialization completed")
    
    def _get_docker_local_ip(self):
        """Get the correct local IP address for Docker container to reach PBX"""
        try:
            # CRITICAL FIX: For Docker containers, we need to use the host's network
            # or get the IP that can actually reach the PBX network
            
            # Method 1: Try to connect to the PBX to get the correct local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(5.0)
            s.connect((self.domain, self.port))
            local_ip = s.getsockname()[0]
            s.close()
            
            # If we got a Docker internal IP (172.x.x.x), try to get the host IP
            if local_ip.startswith('172.') or local_ip.startswith('10.') or local_ip.startswith('192.168.'):
                sip_logger.warning(f"⚠️ Detected Docker internal IP: {local_ip}")
                sip_logger.info("🔧 Attempting to get host network IP...")
                
                # Method 2: Try to get the host's external IP
                try:
                    # Connect to external service to get our external IP
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.settimeout(5.0)
                    s.connect(("8.8.8.8", 80))
                    external_ip = s.getsockname()[0]
                    s.close()
                    
                    # If we're in host network mode, use the external IP
                    if os.environ.get('DOCKER_HOST_NETWORK', 'false').lower() == 'true':
                        sip_logger.info(f"📱 Using host network mode, external IP: {external_ip}")
                        return external_ip
                    else:
                        # For bridge mode, we need to use the host's IP that the PBX can reach
                        sip_logger.info(f"📱 Bridge mode detected, using external IP: {external_ip}")
                        return external_ip
                        
                except Exception as e:
                    sip_logger.warning(f"⚠️ Could not get external IP: {e}")
                    # Fallback to the original IP
                    return local_ip
            
            sip_logger.info(f"📱 Using detected local IP: {local_ip}")
            return local_ip
            
        except Exception as e:
            sip_logger.warning(f"⚠️ Could not detect optimal local IP: {e}")
            
            # Fallback methods
            try:
                # Try to get any available IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(5.0)
                s.connect(("8.8.8.8", 80))
                fallback_ip = s.getsockname()[0]
                s.close()
                sip_logger.info(f"📱 Using fallback IP: {fallback_ip}")
                return fallback_ip
            except:
                sip_logger.error("❌ Could not determine local IP, using 0.0.0.0")
                return "0.0.0.0"
    
    def _init_sip(self):
        """Initialize pyVoIP with proper settings for Docker container"""
        max_attempts = 5
        
        # Start with SIP port 5070 (as configured in docker-compose)
        if self.local_port is None:
            current_local_port = find_available_port(5070)
        else:
            current_local_port = self.local_port
        
        # Get the correct local IP that can reach the PBX
        local_ip = self._get_docker_local_ip()
        
        for attempt in range(max_attempts):
            try:
                sip_logger.info(f"🔄 Attempt {attempt + 1}/{max_attempts}: Initializing pyVoIP")
                sip_logger.info(f"📱 PBX: {self.domain}:{self.port}, Local: {local_ip}:{current_local_port}")
                sip_logger.info(f"📱 Username: {self.username}")
                sip_logger.info(f"📱 Docker Network Mode: {os.environ.get('DOCKER_NETWORK_MODE', 'bridge')}")
                
                # Ensure all parameters are valid
                server = str(self.domain).strip()
                username = str(self.username).strip()
                password = str(self.password).strip()
                port = int(self.port)
                sip_port = int(current_local_port)
                
                if not server or not username or not password:
                    raise ValueError(f"Invalid SIP parameters")
                
                # CRITICAL FIX: Initialize VoIPPhone with Docker-optimized settings
                self.phone = VoIPPhone(
                    server=server,
                    port=port,
                    username=username,
                    password=password,
                    callCallback=self._handle_incoming_call_wrapper,
                    myIP=local_ip,  # Use the IP that can reach the PBX
                    sipPort=sip_port,
                    rtpPortLow=10000,
                    rtpPortHigh=20000
                )
                
                # Store the local port
                self.local_port = current_local_port
                
                sip_logger.info(f"✅ pyVoIP initialized successfully")
                sip_logger.info(f"📱 Local endpoint: {local_ip}:{self.local_port}")
                sip_logger.info(f"📱 PBX endpoint: {self.domain}:{self.port}")
                sip_logger.info(f"📱 RTP ports: 10000-20000")
                return
                
            except Exception as e:
                sip_logger.error(f"💥 Attempt {attempt + 1} failed: {e}")
                
                if "Address already in use" in str(e) or "Errno 98" in str(e):
                    sip_logger.warning(f"⚠️ Port {current_local_port} is in use")
                    current_local_port = find_available_port(current_local_port + 1)
                    continue
                
                if attempt == max_attempts - 1:
                    raise
                current_local_port += 1
    
    def _handle_incoming_call_wrapper(self, call: VoIPCall):
        """
        CRITICAL: Answer calls immediately to prevent voicemail
        """
        try:
            sip_logger.info("=== INCOMING CALL DETECTED ===")
            sip_logger.info(f"📞 MUST ANSWER IMMEDIATELY!")
            
            # Generate call ID
            call_id = f"call_{int(time.time())}_{call.request.headers['Call-ID'][0][:8]}"
            
            # Extract caller ID
            from_header = call.request.headers.get('From', [''])[0]
            caller_id = from_header.split('<')[0].strip() if '<' in from_header else from_header
            
            sip_logger.info(f"📞 Incoming call {call_id} from {caller_id}")
            
            # CRITICAL: Answer immediately
            try:
                sip_logger.info(f"📞 ANSWERING CALL NOW...")
                call.answer()
                sip_logger.info(f"✅ Call {call_id} ANSWERED!")
                
                # Small delay to ensure answer is processed
                time.sleep(0.1)
                
            except Exception as answer_error:
                sip_logger.error(f"❌ Failed to answer call: {answer_error}")
            
            # Handle the call in a separate thread
            handler_thread = threading.Thread(
                target=self._handle_answered_call,
                args=(call, call_id, caller_id),
                daemon=True
            )
            handler_thread.start()
            
            # Keep function alive briefly
            time.sleep(0.5)
            
        except Exception as e:
            sip_logger.error(f"❌ Error in incoming call wrapper: {e}")
            # Try to answer anyway
            try:
                call.answer()
            except:
                pass
    
    def _handle_answered_call(self, call: VoIPCall, call_id: str, caller_id: str):
        """Handle the call after it has been answered"""
        try:
            sip_logger.info(f"📞 Handling answered call {call_id}")
            
            # Create call handler
            call_handler = CallHandler(
                call_id=call_id,
                caller_id=caller_id,
                pyvoip_call=call,
                on_transcript=lambda transcript: self._on_transcript(call_id, transcript),
                on_call_end=lambda: self._on_call_end(call_id)
            )
            
            # Store call handler
            self.active_calls[call_id] = call_handler
            
            # Start call handling
            call_handler.start_call()
            
            # Notify application
            if self.on_incoming_call:
                self.on_incoming_call(call_id, caller_id)
            
            # Handle audio
            sip_logger.info(f"📞 Starting audio handling for call {call_id}")
            try:
                while call.state == CallState.ANSWERED:
                    try:
                        audio = call.read_audio()
                        if audio:
                            call_handler.add_audio_chunk(audio)
                    except Exception as audio_error:
                        sip_logger.warning(f"⚠️ Audio read error: {audio_error}")
                    
                    time.sleep(0.02)
                
            except Exception as e:
                sip_logger.error(f"❌ Audio handler error: {e}")
            finally:
                self._on_call_end(call_id)
            
        except Exception as e:
            sip_logger.error(f"❌ Error handling answered call: {e}")
    
    def register(self) -> bool:
        """Register with PBX and maintain registration"""
        try:
            sip_logger.info(f"🔄 Starting registration with PBX {self.domain}:{self.port}")
            
            if not hasattr(self, 'phone') or self.phone is None:
                sip_logger.error("📱 Phone object not initialized!")
                return False
            
            # Start the phone (initiates registration)
            sip_logger.info("📱 Starting VoIPPhone...")
            try:
                self.phone.start()
                sip_logger.info("📱 VoIPPhone started")
            except Exception as e:
                sip_logger.error(f"❌ Failed to start VoIPPhone: {e}")
                return False
            
            # Wait for initial registration
            sip_logger.info("📱 Waiting for registration...")
            time.sleep(3)  # Give it more time to register
            
            # Check registration status
            try:
                if hasattr(self.phone, 'sip') and self.phone.sip:
                    # Check if we're registered
                    if hasattr(self.phone.sip, 'status'):
                        status = self.phone.sip.status
                        sip_logger.info(f"📱 SIP Status: {status}")
                        
                        if status == SIPStatus.REGISTERED:
                            sip_logger.info("✅ Successfully registered!")
                        else:
                            sip_logger.warning(f"⚠️ Registration status: {status}")
                    
                    self.registered = True
                    self.running = True
                    
                    # Start keep-alive mechanism
                    self._start_keep_alive()
                    
                    # Start OPTIONS responder for reachability
                    self._start_options_responder()
                    
                    sip_logger.info(f"✅ REGISTERED with PBX at {self.domain}:{self.port}")
                    sip_logger.info(f"📱 Extension: {self.username}")
                    sip_logger.info(f"📱 Status should now be REACHABLE")
                    sip_logger.info(f"📱 Ready to receive calls!")
                    
                    return True
                else:
                    sip_logger.error("❌ SIP client failed to start properly")
                    return False
                    
            except Exception as e:
                sip_logger.error(f"❌ Error checking SIP status: {e}")
                return False
            
        except Exception as e:
            sip_logger.error(f"❌ Registration failed: {e}")
            self.registered = False
            return False
    
    def _start_keep_alive(self):
        """Maintain registration and respond to keep-alive requests"""
        def keep_alive():
            while self.running:
                try:
                    if self.phone and self.phone.sip:
                        # The pyVoIP library should handle re-registration
                        # but we can send periodic OPTIONS to stay alive
                        sip_logger.debug("📡 Keep-alive check")
                        
                        # Check if we're still registered
                        if hasattr(self.phone.sip, 'status'):
                            status = self.phone.sip.status
                            if status != SIPStatus.REGISTERED:
                                sip_logger.warning(f"⚠️ Lost registration, status: {status}")
                                # Try to re-register
                                try:
                                    self.phone.sip.register()
                                    sip_logger.info("📱 Re-registration attempted")
                                except:
                                    pass
                    
                    time.sleep(20)  # Check every 20 seconds
                except Exception as e:
                    sip_logger.error(f"❌ Keep-alive error: {e}")
        
        self.keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        self.keep_alive_thread.start()
        sip_logger.info("✅ Keep-alive thread started")
    
    def _start_options_responder(self):
        """Respond to OPTIONS requests to maintain REACHABLE status"""
        def options_responder():
            while self.running:
                try:
                    # The pyVoIP library should handle OPTIONS automatically
                    # but we ensure we're responsive
                    if self.phone and hasattr(self.phone, 'sip'):
                        sip_logger.debug("📡 OPTIONS responder active")
                    
                    time.sleep(5)  # Check every 5 seconds
                except Exception as e:
                    sip_logger.error(f"❌ OPTIONS responder error: {e}")
        
        self.options_thread = threading.Thread(target=options_responder, daemon=True)
        self.options_thread.start()
        sip_logger.info("✅ OPTIONS responder thread started")
    
    def set_callbacks(self, on_incoming_call: Callable[[str, str], None],
                     on_call_transcript: Callable[[str, str], None],
                     on_call_end: Callable[[str], None]):
        """Set callback functions for call events"""
        sip_logger.info("=== SETTING SIP CALLBACKS ===")
        self.on_incoming_call = on_incoming_call
        self.on_call_transcript = on_call_transcript
        self.on_call_end = on_call_end
        sip_logger.info("✅ SIP callbacks set")
    
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
            
            # Load and convert audio
            audio = AudioSegment.from_file(audio_file_path)
            audio = audio.set_frame_rate(8000)
            audio = audio.set_channels(1)
            raw_audio = audio.raw_data
            
            # Send audio
            if pyvoip_call and pyvoip_call.state == CallState.ANSWERED:
                pyvoip_call.write_audio(raw_audio)
                sip_logger.info(f"🔊 Playing audio to call {call_id}")
                return True
            else:
                sip_logger.error(f"❌ Call {call_id} not in answered state")
                return False
            
        except Exception as e:
            sip_logger.error(f"❌ Failed to play audio: {e}")
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
        status_info = {
            'registered': self.registered,
            'domain': self.domain,
            'username': self.username,
            'pbx_port': self.port,
            'local_port': self.local_port,
            'active_calls': len(self.active_calls),
            'docker_network_mode': os.environ.get('DOCKER_NETWORK_MODE', 'bridge')
        }
        
        # Try to get more detailed status
        if self.phone and hasattr(self.phone, 'sip'):
            if hasattr(self.phone.sip, 'status'):
                status_info['sip_status'] = str(self.phone.sip.status)
        
        return status_info
    
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
            
            # Stop the phone
            if self.phone:
                try:
                    self.phone.stop()
                    sip_logger.info("✅ VoIPPhone stopped")
                except Exception as e:
                    sip_logger.warning(f"⚠️ Error stopping phone: {e}")
                finally:
                    self.phone = None
            
            self.registered = False
            sip_logger.info("✅ SIP client shutdown complete")
            
        except Exception as e:
            sip_logger.error(f"❌ Error during shutdown: {e}")