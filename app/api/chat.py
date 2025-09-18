"""
FloatChat - Chat API Endpoints

RESTful API endpoints for conversational AI interface with ARGO data,
supporting text and voice interactions with multilingual capabilities.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

from app.services.rag_service import RAGPipeline
from app.services.gemini_service import GeminiService
from app.services.nlu_service import NLUService
from app.services.voice_service import voice_service
from app.services.translation_service import multilingual_service
from app.models.schemas import (
    ChatQuery, ChatResponse, ChatMessage,
    VoiceTranscriptionRequest, VoiceTranscriptionResponse,
    VoiceSynthesisRequest, VoiceSynthesisResponse
)
from app.utils.exceptions import AIServiceError, ValidationError, RateLimitError
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter()

# Global service instances (will be initialized on startup)
rag_pipeline: Optional[RAGPipeline] = None
gemini_service: Optional[GeminiService] = None
nlu_service: Optional[NLUService] = None


async def get_rag_pipeline() -> RAGPipeline:
    """Dependency to get RAG pipeline instance."""
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = RAGPipeline()
        await rag_pipeline.initialize()
    return rag_pipeline


async def get_gemini_service() -> GeminiService:
    """Dependency to get Gemini service instance."""
    global gemini_service
    if gemini_service is None:
        gemini_service = GeminiService()
        await gemini_service.initialize()
    return gemini_service


async def get_nlu_service() -> NLUService:
    """Dependency to get NLU service instance."""
    global nlu_service
    if nlu_service is None:
        nlu_service = NLUService()
    return nlu_service


def get_correlation_id() -> str:
    """Generate correlation ID for request tracking."""
    return f"chat_{uuid.uuid4().hex[:12]}"


# =============================================================================
# CHAT ENDPOINTS
# =============================================================================

@router.post("/query", response_model=ChatResponse)
async def process_chat_query(
    query: ChatQuery,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
    correlation_id: str = Depends(get_correlation_id)
) -> ChatResponse:
    """
    Process a natural language query about ARGO oceanographic data.
    
    This endpoint handles the complete conversational AI pipeline:
    - Natural language understanding
    - Context retrieval from knowledge base
    - SQL query generation for data access
    - Response generation with fact checking
    - Multilingual support
    """
    try:
        logger.info(
            "Processing chat query",
            message_length=len(query.message),
            language=query.language,
            conversation_id=query.conversation_id,
            correlation_id=correlation_id
        )
        
        # Process query through RAG pipeline
        rag_response = await rag_pipeline.process_query(
            query=query.message,
            conversation_id=query.conversation_id,
            user_preferences={"language": query.language},
            correlation_id=correlation_id
        )
        
        # Determine query type from metadata
        query_type = "general_query"
        if rag_response.generation_metadata.get("query_analysis"):
            query_type = rag_response.generation_metadata["query_analysis"]["intent"]
        
        # Prepare visualization config if applicable
        visualization_config = None
        if query_type in ["show_map", "plot_profile", "analyze_temperature", "analyze_salinity"]:
            visualization_config = _generate_visualization_config(
                query_type, rag_response.query_results, rag_response.generation_metadata
            )
        
        # Prepare data summary
        data_summary = None
        if rag_response.query_results:
            data_summary = {
                "record_count": len(rag_response.query_results),
                "data_type": _infer_data_type(rag_response.query_results),
                "summary_stats": _calculate_summary_stats(rag_response.query_results)
            }
        
        # Create response
        response = ChatResponse(
            message=rag_response.response,
            conversation_id=rag_response.generation_metadata.get("conversation_id", query.conversation_id),
            query_type=query_type,
            sql_query=rag_response.sql_query,
            data_summary=data_summary,
            visualization_config=visualization_config,
            confidence_score=rag_response.confidence_score,
            processing_time_ms=rag_response.processing_time_ms,
            correlation_id=correlation_id
        )
        
        logger.info(
            "Chat query processed successfully",
            confidence_score=rag_response.confidence_score,
            query_type=query_type,
            processing_time_ms=rag_response.processing_time_ms,
            correlation_id=correlation_id
        )
        
        return response
        
    except RateLimitError as e:
        logger.warning("Rate limit exceeded", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    
    except ValidationError as e:
        logger.warning("Query validation failed", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except AIServiceError as e:
        logger.error("AI service error", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service temporarily unavailable"
        )
    
    except Exception as e:
        logger.error(
            "Chat query processing failed",
            error=str(e),
            correlation_id=correlation_id,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your query"
        )


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    limit: int = 50,
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> Dict[str, Any]:
    """
    Get conversation history for a specific conversation.
    
    Returns the message history with timestamps and metadata.
    """
    try:
        logger.info("Retrieving conversation history", conversation_id=conversation_id)
        
        # Get conversation from Gemini service
        context = await gemini_service.conversation_manager.get_conversation(conversation_id)
        
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation not found: {conversation_id}"
            )
        
        # Format messages
        messages = []
        for msg in context.messages[-limit:]:
            messages.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            })
        
        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "total_messages": len(context.messages),
            "created_at": context.created_at.isoformat(),
            "last_activity": context.last_activity.isoformat(),
            "session_metadata": context.session_metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get conversation history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation history"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> Dict[str, str]:
    """Delete a conversation and its history."""
    try:
        logger.info("Deleting conversation", conversation_id=conversation_id)
        
        # Remove from active conversations
        if conversation_id in gemini_service.conversation_manager.active_conversations:
            del gemini_service.conversation_manager.active_conversations[conversation_id]
        
        # Remove from Redis cache
        await gemini_service.redis_client.delete(f"conversation:{conversation_id}")
        
        return {"message": f"Conversation {conversation_id} deleted successfully"}
        
    except Exception as e:
        logger.error("Failed to delete conversation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )


# =============================================================================
# VOICE ENDPOINTS
# =============================================================================

@router.post("/voice/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_audio(
    request: VoiceTranscriptionRequest,
    correlation_id: str = Depends(get_correlation_id)
) -> VoiceTranscriptionResponse:
    """
    Transcribe audio to text using speech recognition.
    
    Supports multiple languages and provides confidence scoring.
    """
    try:
        logger.info(
            "Processing voice transcription",
            audio_format=request.audio_format,
            language=request.language,
            correlation_id=correlation_id
        )
        
        # Import voice service (would be implemented)
        # from app.services.voice_service import VoiceService
        # voice_service = VoiceService()
        
        # Mock implementation for now
        start_time = datetime.utcnow()
        
        # Simulate transcription processing
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Mock transcription result
        transcription = "Show me temperature data from the Arabian Sea"
        confidence = 0.95
        detected_language = request.language if request.language != "auto" else "en"
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        response = VoiceTranscriptionResponse(
            transcription=transcription,
            confidence=confidence,
            language=detected_language,
            processing_time_ms=processing_time,
            correlation_id=correlation_id
        )
        
        logger.info(
            "Voice transcription completed",
            transcription_length=len(transcription),
            confidence=confidence,
            processing_time_ms=processing_time,
            correlation_id=correlation_id
        )
        
        return response
        
    except Exception as e:
        logger.error("Voice transcription failed", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Voice transcription failed"
        )


@router.post("/voice/synthesize", response_model=VoiceSynthesisResponse)
async def synthesize_speech(
    request: VoiceSynthesisRequest,
    correlation_id: str = Depends(get_correlation_id)
) -> VoiceSynthesisResponse:
    """
    Convert text to speech using text-to-speech synthesis.
    
    Supports multiple languages and voice options.
    """
    try:
        logger.info(
            "Processing speech synthesis",
            text_length=len(request.text),
            language=request.language,
            speed=request.speed,
            correlation_id=correlation_id
        )
        
        # Mock implementation for now
        start_time = datetime.utcnow()
        
        # Simulate TTS processing
        await asyncio.sleep(0.2)  # Simulate processing time
        
        # Mock audio data (base64 encoded)
        audio_data = "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="  # Mock WAV header
        duration_seconds = len(request.text) * 0.1  # Estimate duration
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        response = VoiceSynthesisResponse(
            audio_data=audio_data,
            audio_format="wav",
            duration_seconds=duration_seconds,
            processing_time_ms=processing_time,
            correlation_id=correlation_id
        )
        
        logger.info(
            "Speech synthesis completed",
            duration_seconds=duration_seconds,
            processing_time_ms=processing_time,
            correlation_id=correlation_id
        )
        
        return response
        
    except Exception as e:
        logger.error("Speech synthesis failed", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Speech synthesis failed"
        )


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================

@router.post("/analyze/intent")
async def analyze_query_intent(
    query: str,
    nlu_service: NLUService = Depends(get_nlu_service),
    correlation_id: str = Depends(get_correlation_id)
) -> Dict[str, Any]:
    """
    Analyze query intent and extract entities without full processing.
    
    Useful for query suggestion and disambiguation.
    """
    try:
        logger.info("Analyzing query intent", query_length=len(query), correlation_id=correlation_id)
        
        # Analyze query
        analysis = await nlu_service.analyze_query(query, correlation_id=correlation_id)
        
        # Extract parameters
        parameters = nlu_service.extract_query_parameters(analysis)
        
        return {
            "intent": analysis.intent.value,
            "confidence": analysis.confidence,
            "language": analysis.language,
            "entities": [
                {
                    "text": entity.text,
                    "label": entity.label,
                    "confidence": entity.confidence
                }
                for entity in analysis.entities
            ],
            "spatial_scope": {
                "locations": analysis.spatial_scope.locations,
                "coordinates": analysis.spatial_scope.coordinates,
                "ocean_basins": analysis.spatial_scope.ocean_basins
            },
            "temporal_scope": {
                "start_date": analysis.temporal_scope.start_date.isoformat() if analysis.temporal_scope.start_date else None,
                "end_date": analysis.temporal_scope.end_date.isoformat() if analysis.temporal_scope.end_date else None,
                "relative_time": analysis.temporal_scope.relative_time
            },
            "parameter_scope": {
                "measurements": analysis.parameter_scope.measurements,
                "depth_range": analysis.parameter_scope.depth_range
            },
            "disambiguation_needed": analysis.disambiguation_needed,
            "clarification_questions": analysis.clarification_questions,
            "extracted_parameters": parameters,
            "correlation_id": correlation_id
        }
        
    except Exception as e:
        logger.error("Intent analysis failed", error=str(e), correlation_id=correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Intent analysis failed"
        )


@router.get("/suggestions")
async def get_query_suggestions(
    context: Optional[str] = None,
    language: str = "en"
) -> Dict[str, List[str]]:
    """
    Get query suggestions based on context or popular queries.
    
    Helps users discover what they can ask about ARGO data.
    """
    try:
        # Predefined suggestions by category
        suggestions = {
            "float_information": [
                "Show me information about float 1234567",
                "What floats are active in the Arabian Sea?",
                "Find floats deployed in the last year"
            ],
            "temperature_analysis": [
                "What's the average temperature in the Bay of Bengal?",
                "Show temperature trends over the last 5 years",
                "Compare temperature profiles between two locations"
            ],
            "salinity_analysis": [
                "Analyze salinity patterns in the Indian Ocean",
                "What's the salinity range at 1000m depth?",
                "Show salinity variations by season"
            ],
            "visualization": [
                "Show me a map of all active floats",
                "Plot temperature vs depth profile",
                "Create a time series chart of ocean temperature"
            ],
            "data_exploration": [
                "What data is available for the last month?",
                "Show me the most recent profiles",
                "Find anomalies in temperature data"
            ]
        }
        
        # Add Hindi suggestions if requested
        if language == "hi":
            suggestions["hindi_examples"] = [
                "समुद्री तापमान के बारे में बताएं",  # Tell about ocean temperature
                "अरब सागर में नमक की मात्रा दिखाएं",  # Show salinity in Arabian Sea
                "फ्लोट की जानकारी दें"  # Give float information
            ]
        
        return suggestions
        
    except Exception as e:
        logger.error("Failed to get suggestions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get query suggestions"
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _generate_visualization_config(
    query_type: str,
    query_results: Optional[List[Dict[str, Any]]],
    metadata: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Generate visualization configuration based on query type and results."""
    
    if not query_results:
        return None
    
    config = {
        "chart_type": "table",  # Default
        "title": "ARGO Data Results",
        "data_fields": [],
        "settings": {}
    }
    
    if query_type == "show_map":
        config.update({
            "chart_type": "map",
            "title": "ARGO Float Locations",
            "data_fields": ["latitude", "longitude", "wmo_id"],
            "settings": {
                "center": [20.0, 65.0],  # Indian Ocean
                "zoom": 4,
                "marker_type": "float_location"
            }
        })
    
    elif query_type == "plot_profile":
        config.update({
            "chart_type": "line",
            "title": "Ocean Profile",
            "data_fields": ["pressure", "temperature", "salinity"],
            "settings": {
                "x_axis": "pressure",
                "y_axis": ["temperature", "salinity"],
                "invert_y": True  # Depth increases downward
            }
        })
    
    elif query_type in ["analyze_temperature", "analyze_salinity"]:
        config.update({
            "chart_type": "scatter",
            "title": f"Ocean {query_type.split('_')[1].title()} Analysis",
            "data_fields": ["profile_date", query_type.split('_')[1]],
            "settings": {
                "x_axis": "profile_date",
                "y_axis": query_type.split('_')[1],
                "trend_line": True
            }
        })
    
    return config


def _infer_data_type(query_results: List[Dict[str, Any]]) -> str:
    """Infer the type of data from query results."""
    if not query_results:
        return "unknown"
    
    first_record = query_results[0]
    
    if "wmo_id" in first_record and "deployment_date" in first_record:
        return "float_information"
    elif "cycle_number" in first_record and "profile_date" in first_record:
        return "profile_data"
    elif "pressure" in first_record and "temperature" in first_record:
        return "measurement_data"
    else:
        return "general_data"


def _calculate_summary_stats(query_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary statistics for query results."""
    if not query_results:
        return {}
    
    stats = {"record_count": len(query_results)}
    
    # Calculate stats for numerical fields
    numerical_fields = []
    for key, value in query_results[0].items():
        if isinstance(value, (int, float)):
            numerical_fields.append(key)
    
    for field in numerical_fields:
        values = [record.get(field) for record in query_results if record.get(field) is not None]
        if values:
            stats[f"{field}_min"] = min(values)
            stats[f"{field}_max"] = max(values)
            stats[f"{field}_avg"] = sum(values) / len(values)
    
    return stats
