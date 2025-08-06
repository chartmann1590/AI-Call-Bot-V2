import os
import logging
import numpy as np
from faster_whisper import WhisperModel
from typing import Generator, Optional, List
import soundfile as sf
from pydub import AudioSegment
import tempfile
from datetime import datetime

# Configure comprehensive logging for Whisper transcriber
whisper_logger = logging.getLogger('whisper')
whisper_logger.setLevel(logging.DEBUG)

class WhisperTranscriber:
    """Handles real-time audio transcription using Faster Whisper"""
    
    def __init__(self, model_size: str = 'base', device: str = 'cpu', compute_type: str = 'int8'):
        """
        Initialize the Whisper transcriber
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to run on (cpu, cuda)
            compute_type: Compute type for quantization (int8, float16, float32)
        """
        whisper_logger.info("=== INITIALIZING WHISPER TRANSCRIBER ===")
        whisper_logger.info(f"🎤 Model size: {model_size}")
        whisper_logger.info(f"🎤 Device: {device}")
        whisper_logger.info(f"🎤 Compute type: {compute_type}")
        
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        
        whisper_logger.info("🎤 Starting model loading...")
        self._load_model()
        whisper_logger.info("✅ Whisper transcriber initialized successfully")
    
    def _load_model(self):
        """Load the Whisper model"""
        try:
            whisper_logger.info(f"🎤 Loading Whisper model: {self.model_size} on {self.device}")
            whisper_logger.info(f"🎤 Compute type: {self.compute_type}")
            
            start_time = datetime.now()
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            load_time = (datetime.now() - start_time).total_seconds()
            
            whisper_logger.info(f"✅ Whisper model loaded successfully in {load_time:.2f}s")
            whisper_logger.info(f"🎤 Model type: {type(self.model)}")
            
        except Exception as e:
            whisper_logger.error(f"❌ Failed to load Whisper model: {e}")
            whisper_logger.error(f"Exception type: {type(e)}")
            import traceback
            whisper_logger.error(f"Model loading error traceback: {traceback.format_exc()}")
            raise
    
    def transcribe_audio_chunk(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[str]:
        """
        Transcribe a single audio chunk
        
        Args:
            audio_data: Raw audio data as bytes
            sample_rate: Audio sample rate
            
        Returns:
            Transcribed text or None if transcription failed
        """
        whisper_logger.info("=== TRANSCRIBING AUDIO CHUNK ===")
        whisper_logger.info(f"🎤 Audio data size: {len(audio_data)} bytes")
        whisper_logger.info(f"🎤 Sample rate: {sample_rate}")
        whisper_logger.info(f"🎤 Timestamp: {datetime.now()}")
        
        try:
            # Convert bytes to numpy array
            whisper_logger.debug(f"🎤 Converting audio bytes to numpy array...")
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            audio_array = audio_array.astype(np.float32) / 32768.0
            whisper_logger.debug(f"🎤 Audio array shape: {audio_array.shape}")
            whisper_logger.debug(f"🎤 Audio array dtype: {audio_array.dtype}")
            
            # Transcribe using Whisper
            whisper_logger.info(f"🎤 Starting Whisper transcription...")
            start_time = datetime.now()
            
            segments, _ = self.model.transcribe(
                audio_array,
                language="en",
                beam_size=5,
                vad_filter=True
            )
            
            transcription_time = (datetime.now() - start_time).total_seconds()
            whisper_logger.info(f"🎤 Transcription completed in {transcription_time:.2f}s")
            
            # Combine all segments
            transcript = " ".join([segment.text for segment in segments])
            whisper_logger.info(f"🎤 Number of segments: {len(list(segments))}")
            whisper_logger.info(f"🎤 Raw transcript: {transcript}")
            
            if transcript:
                transcript = transcript.strip()
                whisper_logger.info(f"✅ Transcription successful")
                whisper_logger.info(f"🎤 Final transcript: {transcript}")
                whisper_logger.info(f"🎤 Transcript length: {len(transcript)} characters")
            else:
                whisper_logger.warning(f"⚠️ No transcript generated")
            
            return transcript
            
        except Exception as e:
            whisper_logger.error(f"❌ Error transcribing audio chunk: {e}")
            whisper_logger.error(f"Exception type: {type(e)}")
            import traceback
            whisper_logger.error(f"Transcription error traceback: {traceback.format_exc()}")
            return None
    
    def transcribe_file(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe an audio file
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text or None if transcription failed
        """
        whisper_logger.info("=== TRANSCRIBING AUDIO FILE ===")
        whisper_logger.info(f"🎤 Audio file: {audio_file_path}")
        whisper_logger.info(f"🎤 File exists: {os.path.exists(audio_file_path)}")
        whisper_logger.info(f"🎤 File size: {os.path.getsize(audio_file_path) if os.path.exists(audio_file_path) else 'Unknown'} bytes")
        whisper_logger.info(f"🎤 Timestamp: {datetime.now()}")
        
        try:
            whisper_logger.info(f"🎤 Starting Whisper transcription of file...")
            start_time = datetime.now()
            
            segments, _ = self.model.transcribe(
                audio_file_path,
                language="en",
                beam_size=5,
                vad_filter=True
            )
            
            transcription_time = (datetime.now() - start_time).total_seconds()
            whisper_logger.info(f"🎤 File transcription completed in {transcription_time:.2f}s")
            
            transcript = " ".join([segment.text for segment in segments])
            whisper_logger.info(f"🎤 Number of segments: {len(list(segments))}")
            whisper_logger.info(f"🎤 Raw transcript: {transcript}")
            
            if transcript:
                transcript = transcript.strip()
                whisper_logger.info(f"✅ File transcription successful")
                whisper_logger.info(f"🎤 Final transcript: {transcript}")
                whisper_logger.info(f"🎤 Transcript length: {len(transcript)} characters")
            else:
                whisper_logger.warning(f"⚠️ No transcript generated from file")
            
            return transcript
            
        except Exception as e:
            whisper_logger.error(f"❌ Error transcribing audio file {audio_file_path}: {e}")
            whisper_logger.error(f"Exception type: {type(e)}")
            import traceback
            whisper_logger.error(f"File transcription error traceback: {traceback.format_exc()}")
            return None
    
    def transcribe_streaming(self, audio_chunks: Generator[bytes, None, None], 
                           sample_rate: int = 16000) -> Generator[str, None, None]:
        """
        Stream transcription of audio chunks
        
        Args:
            audio_chunks: Generator yielding audio chunks as bytes
            sample_rate: Audio sample rate
            
        Yields:
            Transcribed text segments
        """
        buffer = []
        buffer_duration = 5  # seconds
        samples_per_chunk = sample_rate * 2  # 16-bit audio
        
        for chunk in audio_chunks:
            buffer.append(chunk)
            
            # Check if buffer is full (5 seconds of audio)
            total_samples = sum(len(c) // 2 for c in buffer)  # 2 bytes per sample
            if total_samples >= sample_rate * buffer_duration:
                # Combine chunks into single audio data
                combined_audio = b''.join(buffer)
                
                # Transcribe the buffer
                transcript = self.transcribe_audio_chunk(combined_audio, sample_rate)
                if transcript:
                    yield transcript
                
                # Clear buffer
                buffer = []
        
        # Transcribe remaining audio
        if buffer:
            combined_audio = b''.join(buffer)
            transcript = self.transcribe_audio_chunk(combined_audio, sample_rate)
            if transcript:
                yield transcript
    
    def convert_audio_format(self, input_path: str, output_path: str, 
                           target_format: str = 'wav', sample_rate: int = 16000) -> bool:
        """
        Convert audio file to target format
        
        Args:
            input_path: Input audio file path
            output_path: Output audio file path
            target_format: Target format (wav, mp3, etc.)
            sample_rate: Target sample rate
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            audio = AudioSegment.from_file(input_path)
            audio = audio.set_frame_rate(sample_rate)
            audio = audio.set_channels(1)  # Convert to mono
            
            audio.export(output_path, format=target_format)
            return True
            
        except Exception as e:
            whisper_logger.error(f"❌ Error converting audio format: {e}")
            whisper_logger.error(f"Exception type: {type(e)}")
            import traceback
            whisper_logger.error(f"Audio format conversion error traceback: {traceback.format_exc()}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available Whisper model sizes"""
        return ['tiny', 'base', 'small', 'medium', 'large']
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            'model_size': self.model_size,
            'device': self.device,
            'compute_type': self.compute_type,
            'available_models': self.get_available_models()
        }
    
    def cleanup(self):
        """Clean up Whisper model resources"""
        try:
            if self.model is not None:
                # Clear model reference to allow garbage collection
                self.model = None
                whisper_logger.info("🎤 Whisper model cleaned up")
        except Exception as e:
            whisper_logger.error(f"❌ Error cleaning up Whisper model: {e}")
            whisper_logger.error(f"Exception type: {type(e)}")
            import traceback
            whisper_logger.error(f"Model cleanup error traceback: {traceback.format_exc()}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during cleanup 