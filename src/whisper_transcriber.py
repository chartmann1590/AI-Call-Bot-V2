import os
import logging
import numpy as np
from faster_whisper import WhisperModel
from typing import Generator, Optional, List
import soundfile as sf
from pydub import AudioSegment
import tempfile

logger = logging.getLogger(__name__)

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
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model"""
        try:
            logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
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
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            audio_array = audio_array.astype(np.float32) / 32768.0
            
            # Transcribe using Whisper
            segments, _ = self.model.transcribe(
                audio_array,
                language="en",
                beam_size=5,
                vad_filter=True
            )
            
            # Combine all segments
            transcript = " ".join([segment.text for segment in segments])
            return transcript.strip() if transcript else None
            
        except Exception as e:
            logger.error(f"Error transcribing audio chunk: {e}")
            return None
    
    def transcribe_file(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe an audio file
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text or None if transcription failed
        """
        try:
            segments, _ = self.model.transcribe(
                audio_file_path,
                language="en",
                beam_size=5,
                vad_filter=True
            )
            
            transcript = " ".join([segment.text for segment in segments])
            return transcript.strip() if transcript else None
            
        except Exception as e:
            logger.error(f"Error transcribing audio file {audio_file_path}: {e}")
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
            logger.error(f"Error converting audio format: {e}")
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
                logger.info("Whisper model cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up Whisper model: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during cleanup 