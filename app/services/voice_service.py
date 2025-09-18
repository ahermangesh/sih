"""
Voice Processing Service for FloatChat.

Provides speech-to-text and text-to-speech functionality with multilingual support.
Handles audio processing, quality enhancement, and voice-based interactions.
"""

import io
import base64
import asyncio
import logging
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import tempfile
import os

# Audio processing
try:
    import speech_recognition as sr
    from gtts import gTTS
    import pydub
    from pydub import AudioSegment
    from pydub.effects import normalize
    AUDIO_DEPS_AVAILABLE = True
except ImportError:
    AUDIO_DEPS_AVAILABLE = False
    sr = None  # type: ignore

from app.core.config import get_settings
from app.utils.exceptions import VoiceProcessingError
from app.models.schemas import (
    VoiceTranscriptionRequest, VoiceTranscriptionResponse,
    TextToSpeechRequest, TextToSpeechResponse
)

settings = get_settings()
logger = logging.getLogger(__name__)


class AudioProcessor:
    """Audio processing and enhancement utilities."""
    
    def __init__(self):
        self.sample_rate = settings.audio_sample_rate
        self.supported_formats = ['wav', 'mp3', 'flac', 'ogg', 'webm', 'm4a']
    
    def enhance_audio_quality(self, audio_data: bytes, format: str = 'wav') -> bytes:
        """
        Enhance audio quality for better speech recognition.
        
        Args:
            audio_data: Raw audio data
            format: Audio format
            
        Returns:
            Enhanced audio data
        """
        if not AUDIO_DEPS_AVAILABLE:
            logger.warning("Audio processing dependencies not available, returning original audio")
            return audio_data
        
        try:
            # Load audio
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=format)
            
            # Normalize volume
            audio = normalize(audio)
            
            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Set sample rate
            if audio.frame_rate != self.sample_rate:
                audio = audio.set_frame_rate(self.sample_rate)
            
            # Export enhanced audio
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format='wav')
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}")
            return audio_data
    
    def convert_to_wav(self, audio_data: bytes, source_format: str) -> bytes:
        """
        Convert audio to WAV format for speech recognition.
        
        Args:
            audio_data: Raw audio data
            source_format: Source audio format
            
        Returns:
            WAV audio data
        """
        if not AUDIO_DEPS_AVAILABLE:
            return audio_data
        
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=source_format)
            
            # Convert to WAV
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format='wav')
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            raise VoiceProcessingError(f"Failed to convert audio to WAV: {str(e)}")
    
    def detect_audio_format(self, audio_data: bytes) -> Optional[str]:
        """
        Detect audio format from audio data.
        
        Args:
            audio_data: Raw audio data
            
        Returns:
            Detected format or None
        """
        # Check for common audio file signatures
        if audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
            return 'wav'
        elif audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
            return 'mp3'
        elif audio_data[:4] == b'fLaC':
            return 'flac'
        elif audio_data[:4] == b'OggS':
            return 'ogg'
        else:
            return None


class SpeechRecognitionEngine:
    """Speech recognition engine with multiple provider support."""
    
    def __init__(self):
        if not AUDIO_DEPS_AVAILABLE:
            logger.warning("Speech recognition dependencies not available")
            return
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        # Language mapping for speech recognition
        self.language_mapping = {
            'en': 'en-US',
            'hi': 'hi-IN',
            'bn': 'bn-IN',
            'te': 'te-IN',
            'ta': 'ta-IN',
            'mr': 'mr-IN',
            'gu': 'gu-IN',
            'kn': 'kn-IN',
            'ml': 'ml-IN',
            'or': 'or-IN',
            'pa': 'pa-IN',
            'as': 'as-IN'
        }
    
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        language: str = 'en',
        engine: str = 'google'
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text using specified engine.
        
        Args:
            audio_data: WAV audio data
            language: Language code
            engine: Recognition engine ('google', 'sphinx', 'wit', 'azure')
            
        Returns:
            Transcription result with confidence score
        """
        if not AUDIO_DEPS_AVAILABLE:
            raise VoiceProcessingError("Speech recognition dependencies not available")
        
        try:
            # Create temporary file for audio data
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                
                # Load audio file
                with sr.AudioFile(temp_file.name) as source:
                    audio = self.recognizer.record(source)
                
                # Clean up temp file
                os.unlink(temp_file.name)
            
            # Get language code for recognition engine
            recognition_language = self.language_mapping.get(language, 'en-US')
            
            # Perform transcription based on engine
            if engine == 'google':
                text = await self._transcribe_google(audio, recognition_language)
            elif engine == 'sphinx':
                text = await self._transcribe_sphinx(audio, recognition_language)
            else:
                text = await self._transcribe_google(audio, recognition_language)
            
            return {
                'text': text,
                'language': language,
                'confidence': 0.9,  # Google API doesn't provide confidence scores
                'engine': engine
            }
            
        except sr.UnknownValueError:
            raise VoiceProcessingError("Could not understand audio")
        except sr.RequestError as e:
            raise VoiceProcessingError(f"Speech recognition service error: {str(e)}")
        except Exception as e:
            logger.error(f"Speech recognition failed: {e}")
            raise VoiceProcessingError(f"Transcription failed: {str(e)}")
    
    async def _transcribe_google(self, audio: Any, language: str) -> str:
        """Transcribe using Google Speech Recognition."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.recognizer.recognize_google, 
            audio, 
            None, 
            language
        )
    
    async def _transcribe_sphinx(self, audio: Any, language: str) -> str:
        """Transcribe using CMU Sphinx (offline)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.recognizer.recognize_sphinx, 
            audio
        )


class TextToSpeechEngine:
    """Text-to-speech engine with multilingual support."""
    
    def __init__(self):
        # Language mapping for TTS
        self.language_mapping = {
            'en': 'en',
            'hi': 'hi',
            'bn': 'bn',
            'te': 'te',
            'ta': 'ta',
            'mr': 'mr',
            'gu': 'gu',
            'kn': 'kn',
            'ml': 'ml',
            'or': 'or',
            'pa': 'pa',
            'as': 'as'
        }
        
        # Voice quality settings
        self.tts_settings = {
            'slow': False,
            'lang': 'en'
        }
    
    async def synthesize_speech(
        self, 
        text: str, 
        language: str = 'en',
        voice_speed: str = 'normal'
    ) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to synthesize
            language: Language code
            voice_speed: Speech speed ('slow', 'normal', 'fast')
            
        Returns:
            MP3 audio data
        """
        if not AUDIO_DEPS_AVAILABLE:
            raise VoiceProcessingError("Text-to-speech dependencies not available")
        
        try:
            # Get language for TTS
            tts_language = self.language_mapping.get(language, 'en')
            
            # Configure speech speed
            slow_speech = voice_speed == 'slow'
            
            # Create TTS object
            tts = gTTS(
                text=text, 
                lang=tts_language, 
                slow=slow_speech
            )
            
            # Generate audio
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_data = audio_buffer.getvalue()
            
            logger.info(f"Generated TTS audio: {len(audio_data)} bytes for language {language}")
            return audio_data
            
        except Exception as e:
            logger.error(f"Text-to-speech synthesis failed: {e}")
            raise VoiceProcessingError(f"Speech synthesis failed: {str(e)}")


class VoiceService:
    """
    Main voice processing service for FloatChat.
    
    Provides comprehensive voice processing capabilities including:
    - Speech-to-text transcription
    - Text-to-speech synthesis
    - Audio quality enhancement
    - Multilingual voice support
    """
    
    def __init__(self):
        self.audio_processor = AudioProcessor()
        self.speech_recognizer = SpeechRecognitionEngine()
        self.tts_engine = TextToSpeechEngine()
        
        # Supported languages
        self.supported_languages = [
            'en', 'hi', 'bn', 'te', 'ta', 'mr', 'gu', 
            'kn', 'ml', 'or', 'pa', 'as'
        ]
        
        logger.info(f"VoiceService initialized with {len(self.supported_languages)} languages")
    
    async def transcribe_voice(
        self, 
        request: VoiceTranscriptionRequest
    ) -> VoiceTranscriptionResponse:
        """
        Transcribe voice input to text.
        
        Args:
            request: Voice transcription request
            
        Returns:
            Transcription response with text and confidence
        """
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(request.audio_base64)
            
            # Detect audio format
            audio_format = self.audio_processor.detect_audio_format(audio_data)
            if not audio_format:
                audio_format = 'wav'  # Default assumption
            
            # Convert to WAV if needed
            if audio_format != 'wav':
                audio_data = self.audio_processor.convert_to_wav(audio_data, audio_format)
            
            # Enhance audio quality
            audio_data = self.audio_processor.enhance_audio_quality(audio_data)
            
            # Transcribe audio
            result = await self.speech_recognizer.transcribe_audio(
                audio_data=audio_data,
                language=request.language,
                engine=getattr(request, 'engine', 'google')
            )
            
            return VoiceTranscriptionResponse(
                text=result['text'],
                language=result['language'],
                confidence=result['confidence']
            )
            
        except Exception as e:
            logger.error(f"Voice transcription failed: {e}")
            raise VoiceProcessingError(f"Transcription failed: {str(e)}")
    
    async def synthesize_voice(
        self, 
        request: TextToSpeechRequest
    ) -> TextToSpeechResponse:
        """
        Convert text to speech.
        
        Args:
            request: Text-to-speech request
            
        Returns:
            Audio response with base64 encoded audio
        """
        try:
            # Validate language support
            if request.language not in self.supported_languages:
                raise VoiceProcessingError(f"Language '{request.language}' not supported")
            
            # Synthesize speech
            audio_data = await self.tts_engine.synthesize_speech(
                text=request.text,
                language=request.language,
                voice_speed=getattr(request, 'speed', 'normal')
            )
            
            # Encode to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return TextToSpeechResponse(
                audio_base64=audio_base64,
                language=request.language
            )
            
        except Exception as e:
            logger.error(f"Voice synthesis failed: {e}")
            raise VoiceProcessingError(f"Speech synthesis failed: {str(e)}")
    
    async def detect_language(self, audio_data: bytes) -> str:
        """
        Detect language from audio data.
        
        Args:
            audio_data: Audio data to analyze
            
        Returns:
            Detected language code
        """
        # For now, return default language
        # In production, you might use a language detection service
        return settings.default_language
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        Get list of supported languages for voice processing.
        
        Returns:
            List of language information
        """
        language_info = [
            {'code': 'en', 'name': 'English', 'native_name': 'English'},
            {'code': 'hi', 'name': 'Hindi', 'native_name': 'हिन्दी'},
            {'code': 'bn', 'name': 'Bengali', 'native_name': 'বাংলা'},
            {'code': 'te', 'name': 'Telugu', 'native_name': 'తెలుగు'},
            {'code': 'ta', 'name': 'Tamil', 'native_name': 'தமிழ்'},
            {'code': 'mr', 'name': 'Marathi', 'native_name': 'मराठी'},
            {'code': 'gu', 'name': 'Gujarati', 'native_name': 'ગુજરાતી'},
            {'code': 'kn', 'name': 'Kannada', 'native_name': 'ಕನ್ನಡ'},
            {'code': 'ml', 'name': 'Malayalam', 'native_name': 'മലയാളം'},
            {'code': 'or', 'name': 'Odia', 'native_name': 'ଓଡ଼ିଆ'},
            {'code': 'pa', 'name': 'Punjabi', 'native_name': 'ਪੰਜਾਬੀ'},
            {'code': 'as', 'name': 'Assamese', 'native_name': 'অসমীয়া'}
        ]
        
        return language_info


# Service instance
voice_service = VoiceService()
