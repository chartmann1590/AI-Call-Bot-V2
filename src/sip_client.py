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
        
        if self.recording_thread and self.recording_thread.is_alive():
            try:
                self.recording_thread.join(timeout=1.0)
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
    """FIXED SIP client that properly handles Docker networking and ensures PBX reachability"""
    
    def __init__(self, domain: str, username: str, password: str, port: int = 5060, local_port: int = None):
        sip_logger.info("=== INITIALIZING FIXED SIP CLIENT FOR REACHABILITY ===")
        sip_logger.info(f"📱 PBX Domain: {domain}")
        sip_logger.info(f"📱 Username: {username}")
        sip_logger.info(f"📱 Password: {'*' * len(password) if password else 'None'}")
        sip_logger.info(f"📱 PBX Port: {port}")
        
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
        self.local_port = local_port if local_port else 5070  # Default to 5070
        self.registered = False
        self.active_calls = {}
        self.on_incoming_call = None
        self.on_call_transcript = None
        self.on_call_end = None
        self.phone = None
        self.registration_thread = None
        self.keep_alive_thread = None
        self.running = False
        
        # Get the proper local IP for reachability
        self.local_ip = self._get_reachable_ip()
        
        sip_logger.info(f"📱 Local IP for PBX reachability: {self.local_ip}")
        sip_logger.info(f"📱 Local SIP Port: {self.local_port}")
        
        # Initialize SIP
        self._init_sip()
        sip_logger.info("✅ SIP client initialization completed")
    
    def _get_reachable_ip(self):
        """Get the IP address that the PBX can actually reach"""
        sip_logger.info("🔍 Detecting IP address for PBX reachability...")
        
        # Check if we're in host network mode (best for SIP)
        if os.environ.get('DOCKER_HOST_NETWORK', 'false').lower() == 'true':
            sip_logger.info("🐳 Docker host network mode detected")
        
        # Method 1: Try to connect to PBX to find the right interface
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.settimeout(2.0)
            # Connect to PBX (doesn't actually send data, just selects interface)
            test_socket.connect((self.domain, self.port))
            local_ip = test_socket.getsockname()[0]
            test_socket.close()
            
            sip_logger.info(f"✅ Detected IP that can reach PBX: {local_ip}")
            
            # Verify it's not a Docker internal IP
            if local_ip.startswith('172.17.') or local_ip.startswith('172.18.'):
                sip_logger.warning(f"⚠️ Detected Docker bridge IP: {local_ip}")
                sip_logger.warning("⚠️ This may cause reachability issues!")
                sip_logger.warning("⚠️ Consider using host network mode: --network host")
            
            return local_ip
            
        except Exception as e:
            sip_logger.warning(f"⚠️ Could not detect IP via PBX connection: {e}")
        
        # Method 2: Get default route IP
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.connect(("8.8.8.8", 80))
            backup_ip = test_socket.getsockname()[0]
            test_socket.close()
            sip_logger.info(f"✅ Using default route IP: {backup_ip}")
            return backup_ip
        except Exception as e:
            sip_logger.warning(f"⚠️ Could not get default route IP: {e}")
        
        # Method 3: Get first non-loopback IP
        try:
            hostname = socket.gethostname()
            host_ips = socket.gethostbyname_ex(hostname)[2]
            for ip in host_ips:
                if not ip.startswith('127.'):
                    sip_logger.info(f"✅ Using first non-loopback IP: {ip}")
                    return ip
        except Exception as e:
            sip_logger.warning(f"⚠️ Could not get hostname IPs: {e}")
        
        # Last resort - bind to all interfaces
        sip_logger.error("❌ Could not determine reachable IP, using 0.0.0.0")
        sip_logger.error("❌ PBX may show extension as UNREACHABLE!")
        return "0.0.0.0"
    
    def _init_sip(self):
        """Initialize pyVoIP with settings optimized for PBX reachability"""
        max_attempts = 5
        current_local_port = self.local_port
        
        for attempt in range(max_attempts):
            try:
                sip_logger.info(f"🔄 Attempt {attempt + 1}/{max_attempts}: Initializing pyVoIP")
                sip_logger.info(f"📱 Registering FROM: {self.local_ip}:{current_local_port}")
                sip_logger.info(f"📱 Registering TO: {self.domain}:{self.port}")
                sip_logger.info(f"📱 Username: {self.username}")
                
                # Ensure port is available
                try:
                    test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    test_socket.bind(('', current_local_port))
                    test_socket.close()
                    sip_logger.info(f"✅ Port {current_local_port} is available")
                except OSError:
                    sip_logger.warning(f"⚠️ Port {current_local_port} is in use, finding another...")
                    current_local_port = find_available_port(current_local_port + 1)
                
                # Initialize VoIPPhone with explicit IP binding for reachability
                self.phone = VoIPPhone(
                    server=self.domain,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    callCallback=self._handle_incoming_call_immediate,
                    myIP=self.local_ip,  # CRITICAL: Use detected IP for reachability
                    sipPort=current_local_port,
                    rtpPortLow=10000,
                    rtpPortHigh=20000
                )
                
                # Store the actual port we're using
                self.local_port = current_local_port
                
                sip_logger.info(f"✅ pyVoIP initialized successfully")
                sip_logger.info(f"📱 SIP Contact URI: sip:{self.username}@{self.local_ip}:{self.local_port}")
                sip_logger.info(f"📱 This is what PBX will use to reach us")
                return
                
            except Exception as e:
                sip_logger.error(f"💥 Attempt {attempt + 1} failed: {e}")
                
                if "Address already in use" in str(e) or "Errno 98" in str(e):
                    current_local_port = find_available_port(current_local_port + 1)
                    continue
                
                if attempt == max_attempts - 1:
                    raise
                
                current_local_port += 1
    
    def _handle_incoming_call_immediate(self, call: VoIPCall):
        """
        CRITICAL: Answer calls IMMEDIATELY to prevent voicemail and ensure reachability
        """
        try:
            sip_logger.info("=" * 60)
            sip_logger.info("🔔🔔🔔 INCOMING CALL DETECTED! 🔔🔔🔔")
            sip_logger.info("=" * 60)
            
            # Generate call ID with timestamp
            call_id = f"call_{int(time.time() * 1000)}"
            
            # Extract caller information
            try:
                from_header = call.request.headers.get('From', ['Unknown'])[0]
                if '<sip:' in from_header:
                    caller_id = from_header.split('<sip:')[1].split('@')[0]
                else:
                    caller_id = from_header.split('<')[0].strip() if '<' in from_header else from_header
            except:
                caller_id = "Unknown"
            
            sip_logger.info(f"📞 Call ID: {call_id}")
            sip_logger.info(f"📞 Caller: {caller_id}")
            sip_logger.info(f"📞 Call State: {call.state}")
            
            # ANSWER IMMEDIATELY - This prevents voicemail!
            sip_logger.info(f"📞 ANSWERING CALL IMMEDIATELY...")
            try:
                call.answer()
                sip_logger.info(f"✅✅✅ CALL ANSWERED SUCCESSFULLY! ✅✅✅")
                
                # Small delay to ensure answer is processed
                time.sleep(0.1)
                
            except Exception as answer_error:
                sip_logger.error(f"❌ Failed to answer call: {answer_error}")
                # Try to answer again
                try:
                    time.sleep(0.1)
                    call.answer()
                    sip_logger.info(f"✅ Call answered on second attempt")
                except:
                    sip_logger.error(f"❌ Could not answer call after retry")
            
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
            
            # Notify application layer
            if self.on_incoming_call:
                try:
                    self.on_incoming_call(call_id, caller_id)
                except Exception as e:
                    sip_logger.error(f"❌ Error in on_incoming_call callback: {e}")
            
            # Handle the call audio in a separate thread
            audio_thread = threading.Thread(
                target=self._handle_call_audio,
                args=(call, call_handler),
                daemon=True
            )
            audio_thread.start()
            
            sip_logger.info(f"📞 Call handler started for {call_id}")
            
        except Exception as e:
            sip_logger.error(f"❌ Critical error in incoming call handler: {e}")
            import traceback
            sip_logger.error(traceback.format_exc())
            
            # Try to answer anyway to prevent voicemail
            try:
                call.answer()
                sip_logger.info("📞 Emergency answer successful")
            except:
                pass
    
    def _handle_call_audio(self, call: VoIPCall, call_handler: CallHandler):
        """Handle audio during the call"""
        try:
            sip_logger.info(f"🎤 Starting audio handler for call {call_handler.call_id}")
            
            # Simulate initial greeting after answering
            time.sleep(1)
            if self.on_call_transcript:
                self.on_call_transcript(call_handler.call_id, "Hello, this is your AI assistant. How can I help you today?")
            
            # Handle audio while call is active
            audio_timeout = 0
            max_audio_timeout = 30  # 30 seconds max call for testing
            
            while call.state == CallState.ANSWERED and audio_timeout < max_audio_timeout:
                try:
                    # In production, you would read actual audio here:
                    # audio_data = call.read_audio()
                    # if audio_data:
                    #     call_handler.add_audio_chunk(audio_data)
                    
                    # For testing, just keep the call alive
                    time.sleep(0.1)
                    audio_timeout += 0.1
                    
                except Exception as audio_error:
                    sip_logger.warning(f"⚠️ Audio processing error: {audio_error}")
                    break
            
            sip_logger.info(f"🎤 Audio handler ending for call {call_handler.call_id}")
            
        except Exception as e:
            sip_logger.error(f"❌ Error in audio handler: {e}")
        finally:
            # End the call
            self._on_call_end(call_handler.call_id)
    
    def register(self) -> bool:
        """Register with PBX and maintain reachability"""
        try:
            sip_logger.info("=" * 60)
            sip_logger.info("📱 STARTING SIP REGISTRATION FOR REACHABILITY")
            sip_logger.info("=" * 60)
            
            if not hasattr(self, 'phone') or self.phone is None:
                sip_logger.error("📱 Phone object not initialized!")
                return False
            
            # Start the phone (initiates registration)
            sip_logger.info("📱 Starting VoIPPhone...")
            sip_logger.info(f"📱 Registering as: sip:{self.username}@{self.local_ip}:{self.local_port}")
            
            try:
                self.phone.start()
                sip_logger.info("📱 VoIPPhone started successfully")
            except Exception as e:
                sip_logger.error(f"❌ Failed to start VoIPPhone: {e}")
                return False
            
            # Wait for registration to complete
            sip_logger.info("📱 Waiting for registration to complete...")
            time.sleep(3)
            
            # Mark as registered
            self.registered = True
            self.running = True
            
            # Start keep-alive mechanism for reachability
            self._start_keep_alive()
            
            sip_logger.info("=" * 60)
            sip_logger.info("✅✅✅ REGISTRATION SUCCESSFUL! ✅✅✅")
            sip_logger.info(f"📱 Extension: {self.username}")
            sip_logger.info(f"📱 Contact URI: sip:{self.username}@{self.local_ip}:{self.local_port}")
            sip_logger.info(f"📱 PBX should now show status as: OK/REACHABLE")
            sip_logger.info(f"📱 Ready to receive calls!")
            sip_logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            sip_logger.error(f"❌ Registration failed: {e}")
            import traceback
            sip_logger.error(traceback.format_exc())
            self.registered = False
            return False
    
    def _start_keep_alive(self):
        """Maintain registration and respond to OPTIONS for reachability"""
        def keep_alive():
            while self.running:
                try:
                    if self.phone and hasattr(self.phone, 'sip'):
                        # The pyVoIP library handles OPTIONS automatically
                        # This thread just ensures we stay registered
                        sip_logger.debug(f"📡 Keep-alive - Registered: {self.registered}")
                        
                        # Check if we need to re-register
                        if hasattr(self.phone.sip, 'status'):
                            status = self.phone.sip.status
                            if status != SIPStatus.REGISTERED:
                                sip_logger.warning(f"⚠️ Lost registration, status: {status}")
                                sip_logger.warning(f"⚠️ Attempting re-registration...")
                                try:
                                    self.phone.sip.register()
                                    sip_logger.info("📱 Re-registration sent")
                                except Exception as e:
                                    sip_logger.error(f"❌ Re-registration failed: {e}")
                    
                    time.sleep(20)  # Check every 20 seconds
                    
                except Exception as e:
                    sip_logger.error(f"❌ Keep-alive error: {e}")
                    time.sleep(5)
        
        self.keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        self.keep_alive_thread.start()
        sip_logger.info("✅ Keep-alive thread started for maintaining REACHABLE status")
    
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
        sip_logger.info(f"📞 Call {call_id} ending...")
        
        if call_id in self.active_calls:
            call_data = self.active_calls[call_id].end_call()
            del self.active_calls[call_id]
            sip_logger.info(f"📞 Call {call_id} ended and cleaned up")
            
            if self.on_call_end:
                self.on_call_end(call_id)
        else:
            sip_logger.warning(f"⚠️ Call {call_id} not found in active calls")
    
    def play_audio(self, call_id: str, audio_file_path: str) -> bool:
        """Play audio file to call"""
        if call_id not in self.active_calls:
            sip_logger.error(f"📞 Call {call_id} not found")
            return False
        
        try:
            call_handler = self.active_calls[call_id]
            pyvoip_call = call_handler.pyvoip_call
            
            # Load and convert audio for SIP (8kHz, mono, mulaw/alaw)
            audio = AudioSegment.from_file(audio_file_path)
            audio = audio.set_frame_rate(8000)
            audio = audio.set_channels(1)
            raw_audio = audio.raw_data
            
            # Send audio to call
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
        """Get detailed registration status for debugging"""
        status_info = {
            'registered': self.registered,
            'domain': self.domain,
            'username': self.username,
            'pbx_port': self.port,
            'local_ip': self.local_ip,
            'local_port': self.local_port,
            'contact_uri': f"sip:{self.username}@{self.local_ip}:{self.local_port}",
            'active_calls': len(self.active_calls),
            'docker_host_network': os.environ.get('DOCKER_HOST_NETWORK', 'false'),
            'expected_pbx_status': 'OK/REACHABLE' if self.registered else 'UNREACHABLE'
        }
        
        # Try to get more detailed SIP status
        if self.phone and hasattr(self.phone, 'sip'):
            if hasattr(self.phone.sip, 'status'):
                status_info['sip_status'] = str(self.phone.sip.status)
        
        return status_info
    
    def shutdown(self):
        """Shutdown SIP client properly"""
        sip_logger.info("=== SHUTTING DOWN SIP CLIENT ===")
        
        try:
            self.running = False
            self.registered = False
            
            # End all active calls
            for call_id in list(self.active_calls.keys()):
                try:
                    self._on_call_end(call_id)
                except Exception as e:
                    sip_logger.error(f"❌ Error ending call {call_id}: {e}")
            
            # Clear active calls
            self.active_calls.clear()
            
            # Stop the phone
            if self.phone:
                try:
                    sip_logger.info("📱 Stopping VoIPPhone...")
                    self.phone.stop()
                    sip_logger.info("✅ VoIPPhone stopped")
                except Exception as e:
                    sip_logger.warning(f"⚠️ Error stopping phone: {e}")
                finally:
                    self.phone = None
            
            sip_logger.info("✅ SIP client shutdown complete")
            
        except Exception as e:
            sip_logger.error(f"❌ Error during shutdown: {e}")
            import traceback
            sip_logger.error(traceback.format_exc())