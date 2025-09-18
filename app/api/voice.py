"""
Voice Processing API Endpoints for FloatChat.

Provides REST API endpoints for voice-related functionality including:
- Speech-to-text transcription
- Text-to-speech synthesis  
- Voice language detection
- Audio quality enhancement
"""

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
import base64
import io
import logging

from app.services.voice_service import voice_service
from app.models.schemas import (
    VoiceTranscriptionRequest, VoiceTranscriptionResponse,
    TextToSpeechRequest, TextToSpeechResponse,
    ErrorResponse
)
from app.utils.exceptions import VoiceProcessingError, raise_voice_processing_error
from app.core.security import create_correlation_id

router = APIRouter(prefix="/voice", tags=["voice"])
logger = logging.getLogger(__name__)


@router.post(
    "/transcribe",
    response_model=VoiceTranscriptionResponse,
    summary="Convert speech to text",
    description="""
    Transcribe audio input to text with multilingual support.
    
    Supports multiple audio formats:
    - WAV, MP3, FLAC, OGG, WebM, M4A
    
    Supported languages:
    - English (en), Hindi (hi), Bengali (bn), Telugu (te), Tamil (ta)
    - Marathi (mr), Gujarati (gu), Kannada (kn), Malayalam (ml)
    - Odia (or), Punjabi (pa), Assamese (as)
    
    The service automatically enhances audio quality and converts formats as needed.
    """
)
async def transcribe_audio(
    request: VoiceTranscriptionRequest,
    correlation_id: str = Depends(create_correlation_id)
) -> VoiceTranscriptionResponse:
    """
    Transcribe audio to text using speech recognition.
    
    Args:
        request: Voice transcription request with base64 audio
        correlation_id: Request correlation ID for tracking
        
    Returns:
        Transcription result with text and confidence score
        
    Raises:
        HTTPException: If transcription fails or audio is invalid
    """
    try:
        logger.info(
            "Processing voice transcription request",
            language=request.language,
            correlation_id=correlation_id
        )
        
        # Validate language support
        supported_languages = [lang['code'] for lang in voice_service.get_supported_languages()]
        if request.language not in supported_languages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Language '{request.language}' not supported. Supported languages: {supported_languages}"
            )
        
        # Validate audio data
        if not request.audio_base64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio data is required"
            )
        
        # Process transcription
        result = await voice_service.transcribe_voice(request)
        
        logger.info(
            "Voice transcription completed",
            text_length=len(result.text),
            confidence=result.confidence,
            correlation_id=correlation_id
        )
        
        return result
        
    except VoiceProcessingError as e:
        logger.error(
            "Voice processing error during transcription",
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Unexpected error during transcription",
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during transcription"
        )


@router.post(
    "/transcribe-file",
    response_model=VoiceTranscriptionResponse,
    summary="Convert uploaded audio file to text",
    description="Transcribe an uploaded audio file to text. Alternative to base64 encoding."
)
async def transcribe_audio_file(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = "en",
    correlation_id: str = Depends(create_correlation_id)
) -> VoiceTranscriptionResponse:
    """
    Transcribe uploaded audio file to text.
    
    Args:
        file: Uploaded audio file
        language: Language code for transcription
        correlation_id: Request correlation ID
        
    Returns:
        Transcription result
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Read file content
        audio_data = await file.read()
        
        # Convert to base64 for processing
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Create transcription request
        request = VoiceTranscriptionRequest(
            audio_base64=audio_base64,
            language=language
        )
        
        # Process transcription
        return await voice_service.transcribe_voice(request)
        
    except Exception as e:
        logger.error(
            "Error transcribing uploaded file",
            filename=file.filename,
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to transcribe file: {str(e)}"
        )


@router.post(
    "/synthesize",
    response_model=TextToSpeechResponse,
    summary="Convert text to speech",
    description="""
    Convert text to speech audio with multilingual support.
    
    Returns MP3 audio data encoded in base64 format.
    
    Supported languages:
    - English (en), Hindi (hi), Bengali (bn), Telugu (te), Tamil (ta)
    - Marathi (mr), Gujarati (gu), Kannada (kn), Malayalam (ml)
    - Odia (or), Punjabi (pa), Assamese (as)
    """
)
async def synthesize_speech(
    request: TextToSpeechRequest,
    correlation_id: str = Depends(create_correlation_id)
) -> TextToSpeechResponse:
    """
    Convert text to speech audio.
    
    Args:
        request: Text-to-speech request
        correlation_id: Request correlation ID
        
    Returns:
        Audio response with base64 encoded MP3
    """
    try:
        logger.info(
            "Processing text-to-speech request",
            text_length=len(request.text),
            language=request.language,
            correlation_id=correlation_id
        )
        
        # Validate text
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text is required for synthesis"
            )
        
        # Validate text length (reasonable limit)
        if len(request.text) > 5000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text too long. Maximum 5000 characters allowed."
            )
        
        # Process synthesis
        result = await voice_service.synthesize_voice(request)
        
        logger.info(
            "Text-to-speech synthesis completed",
            audio_size=len(result.audio_base64),
            correlation_id=correlation_id
        )
        
        return result
        
    except VoiceProcessingError as e:
        logger.error(
            "Voice processing error during synthesis",
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Unexpected error during synthesis",
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during synthesis"
        )


@router.post(
    "/synthesize-stream",
    summary="Convert text to speech (streaming response)",
    description="Convert text to speech and return audio as streaming MP3 response."
)
async def synthesize_speech_stream(
    request: TextToSpeechRequest,
    correlation_id: str = Depends(create_correlation_id)
):
    """
    Convert text to speech and return as streaming audio.
    
    Args:
        request: Text-to-speech request
        correlation_id: Request correlation ID
        
    Returns:
        Streaming MP3 audio response
    """
    try:
        # Process synthesis
        result = await voice_service.synthesize_voice(request)
        
        # Decode base64 audio
        audio_data = base64.b64decode(result.audio_base64)
        
        # Create streaming response
        audio_stream = io.BytesIO(audio_data)
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3",
                "X-Correlation-ID": correlation_id
            }
        )
        
    except Exception as e:
        logger.error(
            "Error in streaming synthesis",
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to synthesize speech: {str(e)}"
        )


@router.get(
    "/languages",
    response_model=List[Dict[str, str]],
    summary="Get supported languages",
    description="Get list of all supported languages for voice processing."
)
async def get_supported_languages() -> List[Dict[str, str]]:
    """
    Get list of supported languages for voice processing.
    
    Returns:
        List of language information with codes, names, and native names
    """
    return voice_service.get_supported_languages()


@router.get(
    "/health",
    summary="Voice service health check",
    description="Check if voice processing services are available and working."
)
async def voice_health_check() -> Dict[str, Any]:
    """
    Health check for voice processing services.
    
    Returns:
        Service status and capabilities
    """
    try:
        # Check if voice service dependencies are available
        from app.services.voice_service import AUDIO_DEPS_AVAILABLE
        
        status_info = {
            "status": "healthy" if AUDIO_DEPS_AVAILABLE else "degraded",
            "services": {
                "speech_to_text": AUDIO_DEPS_AVAILABLE,
                "text_to_speech": AUDIO_DEPS_AVAILABLE,
                "audio_processing": AUDIO_DEPS_AVAILABLE
            },
            "supported_languages": len(voice_service.get_supported_languages()),
            "capabilities": {
                "transcription": AUDIO_DEPS_AVAILABLE,
                "synthesis": AUDIO_DEPS_AVAILABLE,
                "multilingual": True,
                "audio_enhancement": AUDIO_DEPS_AVAILABLE
            }
        }
        
        if not AUDIO_DEPS_AVAILABLE:
            status_info["message"] = "Voice processing dependencies not fully available"
        
        return status_info
        
    except Exception as e:
        logger.error(f"Voice health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "services": {
                "speech_to_text": False,
                "text_to_speech": False,
                "audio_processing": False
            }
        }


@router.post(
    "/detect-language",
    summary="Detect language from audio",
    description="Detect the language spoken in an audio sample."
)
async def detect_audio_language(
    request: VoiceTranscriptionRequest,
    correlation_id: str = Depends(create_correlation_id)
) -> Dict[str, Any]:
    """
    Detect language from audio sample.
    
    Args:
        request: Audio data for language detection
        correlation_id: Request correlation ID
        
    Returns:
        Detected language information
    """
    try:
        # Decode audio data
        audio_data = base64.b64decode(request.audio_base64)
        
        # Detect language
        detected_language = await voice_service.detect_language(audio_data)
        
        # Get language info
        supported_languages = voice_service.get_supported_languages()
        language_info = next(
            (lang for lang in supported_languages if lang['code'] == detected_language),
            {'code': detected_language, 'name': 'Unknown', 'native_name': 'Unknown'}
        )
        
        return {
            "detected_language": detected_language,
            "language_info": language_info,
            "confidence": 0.8,  # Placeholder confidence score
            "correlation_id": correlation_id
        }
        
    except Exception as e:
        logger.error(
            "Language detection failed",
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Language detection failed: {str(e)}"
        )
