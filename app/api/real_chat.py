"""
FloatChat - Real Chat API with Actual AI Integration

Production chat API using real Google Gemini AI and ARGO data services.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.services.real_gemini_service import real_gemini_service
from app.services.real_argo_service import real_argo_service
from app.services.voice_service import voice_service
from app.services.translation_service import multilingual_service
from app.models.schemas import ChatQueryRequest, ChatQueryResponse
from app.utils.exceptions import AIServiceError, ChatProcessingError

logger = structlog.get_logger(__name__)
router = APIRouter()
settings = get_settings()


# Conversation storage (in production, use Redis or database)
conversation_store = {}


@router.post(
    "/query",
    response_model=ChatQueryResponse,
    summary="Process chat query with real AI",
    description="Process natural language queries about ocean data using real Google Gemini AI and ARGO data APIs."
)
async def process_real_chat_query(
    query: ChatQueryRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> ChatQueryResponse:
    """
    Process a chat query using real AI and ocean data services.
    
    This endpoint:
    - Uses real Google Gemini AI for natural language processing
    - Fetches actual ARGO float data from ocean APIs
    - Provides scientific analysis of ocean conditions
    - Supports voice input/output and multilingual responses
    """
    correlation_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    logger.info(
        "Processing real chat query",
        correlation_id=correlation_id,
        conversation_id=query.conversation_id,
        language=query.language,
        voice_input=query.voice_input,
        message_length=len(query.message)
    )
    
    try:
        # Get conversation context
        conversation_context = conversation_store.get(query.conversation_id, {
            'messages': [],
            'created_at': datetime.now(),
            'language': query.language
        })
        
        # Handle voice input if provided
        processed_message = query.message
        if query.voice_input and query.audio_data:
            try:
                transcription_result = await voice_service.transcribe(
                    query.audio_data,
                    language=query.language
                )
                processed_message = transcription_result[0]  # Get transcribed text
                logger.info("Voice input transcribed", 
                           original_length=len(query.message),
                           transcribed_length=len(processed_message))
            except Exception as e:
                logger.warning(f"Voice transcription failed: {e}")
                # Continue with original message
        
        # Detect language if not specified
        if not query.language or query.language == 'auto':
            try:
                detection_result = await multilingual_service.detect_language(processed_message)
                query.language = detection_result.detected_language
                logger.info("Language detected", detected_language=query.language)
            except Exception as e:
                logger.warning(f"Language detection failed: {e}")
                query.language = 'en'  # Default to English
        
        # Translate to English for AI processing if needed
        english_message = processed_message
        if query.language != 'en':
            try:
                english_message = await multilingual_service.translate(
                    processed_message, 'en', query.language
                )
                logger.info("Message translated for AI processing")
            except Exception as e:
                logger.warning(f"Translation failed: {e}")
                # Continue with original message
        
        # Prepare context for AI analysis
        ai_context = {
            'conversation_history': conversation_context.get('messages', [])[-5:],  # Last 5 messages
            'user_language': query.language,
            'correlation_id': correlation_id
        }
        
        # Process with real Gemini AI
        ai_response = await real_gemini_service.analyze_ocean_query(
            english_message,
            context=ai_context
        )
        
        # Translate response back to user's language if needed
        response_message = ai_response['message']
        if query.language != 'en':
            try:
                response_message = await multilingual_service.translate(
                    ai_response['message'], query.language, 'en'
                )
                logger.info("Response translated to user language")
            except Exception as e:
                logger.warning(f"Response translation failed: {e}")
                # Keep English response
        
        # Generate voice output if requested
        audio_response = None
        if query.voice_output:
            try:
                audio_bytes = await voice_service.synthesize(
                    response_message,
                    language=query.language
                )
                # Convert to base64 for JSON response
                import base64
                audio_response = base64.b64encode(audio_bytes).decode('utf-8')
                logger.info("Voice output generated")
            except Exception as e:
                logger.warning(f"Voice synthesis failed: {e}")
        
        # Build response
        processing_time = (datetime.now() - start_time).total_seconds()
        
        chat_response = ChatQueryResponse(
            message=response_message,
            conversation_id=query.conversation_id,
            language=query.language,
            timestamp=datetime.now(),
            processing_time=processing_time,
            confidence=ai_response.get('confidence', 0.9),
            query_type=ai_response.get('query_type', 'general'),
            data_sources=ai_response.get('data_sources', []),
            visualization=ai_response.get('visualization'),
            audio_response=audio_response,
            metadata={
                'correlation_id': correlation_id,
                'argo_data_available': 'argo_data' in ai_response,
                'location_analyzed': ai_response.get('location') is not None,
                'parameters_analyzed': ai_response.get('parameters', []),
                'ai_service': 'google_gemini',
                'data_service': 'real_argo'
            }
        )
        
        # Update conversation context
        conversation_context['messages'].extend([
            {'role': 'user', 'content': processed_message, 'timestamp': start_time.isoformat()},
            {'role': 'assistant', 'content': response_message, 'timestamp': datetime.now().isoformat()}
        ])
        
        # Keep only last 20 messages to manage memory
        if len(conversation_context['messages']) > 20:
            conversation_context['messages'] = conversation_context['messages'][-20:]
        
        conversation_store[query.conversation_id] = conversation_context
        
        # Log successful processing
        logger.info(
            "Chat query processed successfully",
            correlation_id=correlation_id,
            processing_time=processing_time,
            query_type=ai_response.get('query_type'),
            has_argo_data='argo_data' in ai_response,
            response_length=len(response_message)
        )
        
        # Schedule background tasks
        background_tasks.add_task(
            log_conversation_analytics,
            query.conversation_id,
            processed_message,
            response_message,
            ai_response.get('query_type'),
            processing_time
        )
        
        return chat_response
        
    except AIServiceError as e:
        logger.error(
            "AI service error in chat processing",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service temporarily unavailable: {str(e)}"
        )
        
    except Exception as e:
        logger.error(
            "Unexpected error in chat processing",
            correlation_id=correlation_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request"
        )


@router.get(
    "/conversations/{conversation_id}",
    summary="Get conversation history",
    description="Retrieve the conversation history for a specific conversation ID."
)
async def get_conversation_history(conversation_id: str) -> Dict[str, Any]:
    """Get conversation history."""
    
    conversation = conversation_store.get(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return {
        'conversation_id': conversation_id,
        'messages': conversation['messages'],
        'created_at': conversation['created_at'].isoformat(),
        'language': conversation.get('language', 'en'),
        'total_messages': len(conversation['messages'])
    }


@router.delete(
    "/conversations/{conversation_id}",
    summary="Clear conversation history",
    description="Clear the conversation history for a specific conversation ID."
)
async def clear_conversation_history(conversation_id: str) -> Dict[str, str]:
    """Clear conversation history."""
    
    if conversation_id in conversation_store:
        del conversation_store[conversation_id]
        logger.info("Conversation history cleared", conversation_id=conversation_id)
        return {"message": "Conversation history cleared successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )


@router.post(
    "/analyze-ocean-data",
    summary="Analyze specific ocean data",
    description="Analyze specific ocean data using AI with location and parameters."
)
async def analyze_ocean_data(
    location: Dict[str, float],  # {"latitude": lat, "longitude": lon}
    parameters: List[str] = None,  # ["temperature", "salinity", etc.]
    radius_km: float = 100,
    language: str = 'en'
) -> Dict[str, Any]:
    """
    Analyze ocean data for a specific location using real ARGO data and AI.
    """
    try:
        logger.info(
            "Analyzing ocean data for location",
            latitude=location.get('latitude'),
            longitude=location.get('longitude'),
            radius_km=radius_km,
            parameters=parameters
        )
        
        # Fetch ARGO data for the location
        argo_data = await real_argo_service.get_ocean_conditions(
            location['latitude'],
            location['longitude'],
            radius_km
        )
        
        # Create analysis query
        if parameters:
            param_text = ", ".join(parameters)
            analysis_query = f"Analyze the {param_text} data at {location['latitude']:.3f}°, {location['longitude']:.3f}°"
        else:
            analysis_query = f"Analyze the ocean conditions at {location['latitude']:.3f}°, {location['longitude']:.3f}°"
        
        # Get AI analysis
        ai_response = await real_gemini_service.analyze_ocean_query(
            analysis_query,
            context={'requested_parameters': parameters or []}
        )
        
        # Combine results
        result = {
            'location': location,
            'radius_km': radius_km,
            'argo_data': argo_data,
            'ai_analysis': ai_response['message'],
            'parameters_analyzed': parameters or [],
            'data_sources': ai_response.get('data_sources', []),
            'visualization': ai_response.get('visualization'),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("Ocean data analysis completed", location=location)
        return result
        
    except Exception as e:
        logger.error(f"Failed to analyze ocean data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze ocean data: {str(e)}"
        )


@router.get(
    "/health",
    summary="Chat service health check",
    description="Check the health of chat service and its dependencies."
)
async def chat_health_check() -> Dict[str, Any]:
    """Health check for chat service."""
    
    health_status = {
        'status': 'healthy',
        'service': 'real_chat',
        'timestamp': datetime.now().isoformat(),
        'dependencies': {
            'gemini_ai': real_gemini_service.available,
            'voice_service': voice_service.audio_dependencies_available if hasattr(voice_service, 'audio_dependencies_available') else True,
            'translation_service': True,  # Always available with fallbacks
            'argo_data_service': True     # Always available with fallbacks
        },
        'features': {
            'real_ai_analysis': real_gemini_service.available,
            'voice_processing': hasattr(voice_service, 'audio_dependencies_available'),
            'multilingual_support': True,
            'real_argo_data': True,
            'conversation_memory': True
        }
    }
    
    # Overall health based on critical dependencies
    if not real_gemini_service.available:
        health_status['status'] = 'degraded'
        health_status['warning'] = 'AI service not fully available - using fallback responses'
    
    return health_status


async def log_conversation_analytics(
    conversation_id: str,
    user_message: str,
    ai_response: str,
    query_type: str,
    processing_time: float
):
    """Background task to log conversation analytics."""
    try:
        # In production, this would log to analytics service
        logger.info(
            "Conversation analytics",
            conversation_id=conversation_id,
            message_length=len(user_message),
            response_length=len(ai_response),
            query_type=query_type,
            processing_time=processing_time
        )
    except Exception as e:
        logger.error(f"Failed to log analytics: {e}")


# Add cleanup task for conversation store (in production, use Redis with TTL)
@router.on_event("startup")
async def cleanup_conversations():
    """Periodic cleanup of old conversations."""
    async def cleanup_task():
        while True:
            try:
                current_time = datetime.now()
                expired_conversations = []
                
                for conv_id, conv_data in conversation_store.items():
                    if (current_time - conv_data['created_at']).days > 1:  # 1 day TTL
                        expired_conversations.append(conv_id)
                
                for conv_id in expired_conversations:
                    del conversation_store[conv_id]
                
                if expired_conversations:
                    logger.info(f"Cleaned up {len(expired_conversations)} expired conversations")
                
                await asyncio.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Error in conversation cleanup: {e}")
                await asyncio.sleep(3600)
    
    asyncio.create_task(cleanup_task())
