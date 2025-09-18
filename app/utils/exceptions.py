"""
FloatChat - Custom Exceptions and Error Handling

Custom exception classes and error handling utilities for the FloatChat application.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# CUSTOM EXCEPTION CLASSES
# =============================================================================

class FloatChatException(Exception):
    """Base exception class for FloatChat application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: Dict[str, Any] = None,
        correlation_id: str = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.correlation_id = correlation_id
        super().__init__(self.message)


class DataProcessingError(FloatChatException):
    """Exception raised during data processing operations."""
    pass


class ValidationError(FloatChatException):
    """Exception raised during data validation."""
    pass


class DatabaseError(FloatChatException):
    """Exception raised during database operations."""
    pass


class AIServiceError(FloatChatException):
    """Exception raised during AI/LLM service operations."""
    pass


class VoiceProcessingError(FloatChatException):
    """Exception raised during voice processing operations."""
    pass


class TranslationError(FloatChatException):
    """Exception raised during translation operations."""
    pass


class ConfigurationError(FloatChatException):
    """Exception raised for configuration-related errors."""
    pass


class AuthenticationError(FloatChatException):
    """Exception raised for authentication failures."""
    pass


class RateLimitError(FloatChatException):
    """Exception raised when rate limits are exceeded."""
    pass


class DataNotFoundError(FloatChatException):
    """Exception raised when requested data is not found."""
    pass


class ChatProcessingError(FloatChatException):
    """Exception raised during chat processing operations."""
    pass


# =============================================================================
# HTTP EXCEPTION MAPPERS
# =============================================================================

def map_exception_to_http_status(exception: FloatChatException) -> int:
    """Map custom exceptions to appropriate HTTP status codes."""
    
    exception_status_map = {
        DataProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ValidationError: status.HTTP_400_BAD_REQUEST,
        DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        AIServiceError: status.HTTP_503_SERVICE_UNAVAILABLE,
        VoiceProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
        DataNotFoundError: status.HTTP_404_NOT_FOUND,
    }
    
    return exception_status_map.get(type(exception), status.HTTP_500_INTERNAL_SERVER_ERROR)


def create_error_response(
    exception: FloatChatException,
    request: Request = None
) -> JSONResponse:
    """Create standardized error response."""
    
    correlation_id = exception.correlation_id
    if not correlation_id and request:
        correlation_id = getattr(request.state, 'correlation_id', None)
    
    error_response = {
        "error": {
            "type": exception.error_code,
            "message": exception.message,
            "details": exception.details,
            "correlation_id": correlation_id,
            "timestamp": "2025-09-18T01:30:00Z"  # Would use datetime.utcnow().isoformat()
        }
    }
    
    status_code = map_exception_to_http_status(exception)
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


# =============================================================================
# ERROR HANDLERS
# =============================================================================

def setup_exception_handlers(app):
    """Set up global exception handlers for the FastAPI app."""
    
    @app.exception_handler(FloatChatException)
    async def floatchat_exception_handler(request: Request, exc: FloatChatException):
        """Handle custom FloatChat exceptions."""
        
        logger.error(
            "FloatChat exception occurred",
            exception_type=type(exc).__name__,
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
            correlation_id=exc.correlation_id,
            url=str(request.url),
            method=request.method
        )
        
        return create_error_response(exc, request)
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""
        
        correlation_id = getattr(request.state, 'correlation_id', None)
        
        logger.warning(
            "HTTP exception occurred",
            status_code=exc.status_code,
            detail=exc.detail,
            correlation_id=correlation_id,
            url=str(request.url),
            method=request.method
        )
        
        error_response = {
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code,
                "correlation_id": correlation_id,
                "timestamp": "2025-09-18T01:30:00Z"
            }
        }
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        
        correlation_id = getattr(request.state, 'correlation_id', None)
        
        logger.error(
            "Unexpected exception occurred",
            exception_type=type(exc).__name__,
            message=str(exc),
            correlation_id=correlation_id,
            url=str(request.url),
            method=request.method,
            exc_info=True
        )
        
        error_response = {
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred. Please try again later.",
                "correlation_id": correlation_id,
                "timestamp": "2025-09-18T01:30:00Z"
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def raise_data_processing_error(
    message: str,
    details: Dict[str, Any] = None,
    correlation_id: str = None
):
    """Utility function to raise DataProcessingError with logging."""
    
    logger.error(
        "Data processing error",
        message=message,
        details=details,
        correlation_id=correlation_id
    )
    
    raise DataProcessingError(
        message=message,
        details=details,
        correlation_id=correlation_id
    )


def raise_validation_error(
    message: str,
    field: str = None,
    value: Any = None,
    correlation_id: str = None
):
    """Utility function to raise ValidationError with field information."""
    
    details = {}
    if field:
        details["field"] = field
    if value is not None:
        details["value"] = value
    
    logger.error(
        "Validation error",
        message=message,
        field=field,
        value=value,
        correlation_id=correlation_id
    )
    
    raise ValidationError(
        message=message,
        details=details,
        correlation_id=correlation_id
    )


def raise_database_error(
    message: str,
    operation: str = None,
    table: str = None,
    correlation_id: str = None
):
    """Utility function to raise DatabaseError with operation context."""
    
    details = {}
    if operation:
        details["operation"] = operation
    if table:
        details["table"] = table
    
    logger.error(
        "Database error",
        message=message,
        operation=operation,
        table=table,
        correlation_id=correlation_id
    )
    
    raise DatabaseError(
        message=message,
        details=details,
        correlation_id=correlation_id
    )


def raise_ai_service_error(
    message: str,
    service: str = None,
    model: str = None,
    correlation_id: str = None
):
    """Utility function to raise AIServiceError with service context."""
    
    details = {}
    if service:
        details["service"] = service
    if model:
        details["model"] = model
    
    logger.error(
        "AI service error",
        message=message,
        service=service,
        model=model,
        correlation_id=correlation_id
    )
    
    raise AIServiceError(
        message=message,
        details=details,
        correlation_id=correlation_id
    )


def raise_voice_processing_error(
    message: str,
    operation: str = None,
    language: str = None,
    correlation_id: str = None
):
    """Utility function to raise VoiceProcessingError with context."""
    
    details = {}
    if operation:
        details["operation"] = operation
    if language:
        details["language"] = language
    
    logger.error(
        "Voice processing error",
        message=message,
        operation=operation,
        language=language,
        correlation_id=correlation_id
    )
    
    raise VoiceProcessingError(
        message=message,
        details=details,
        correlation_id=correlation_id
    )


def raise_data_not_found_error(
    message: str,
    resource_type: str = None,
    resource_id: str = None,
    correlation_id: str = None
):
    """Utility function to raise DataNotFoundError with resource context."""
    
    details = {}
    if resource_type:
        details["resource_type"] = resource_type
    if resource_id:
        details["resource_id"] = resource_id
    
    logger.warning(
        "Data not found",
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
        correlation_id=correlation_id
    )
    
    raise DataNotFoundError(
        message=message,
        details=details,
        correlation_id=correlation_id
    )


# =============================================================================
# CONTEXT MANAGERS FOR ERROR HANDLING
# =============================================================================

class ErrorContext:
    """Context manager for handling errors with correlation ID."""
    
    def __init__(self, operation: str, correlation_id: str = None):
        self.operation = operation
        self.correlation_id = correlation_id
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, Exception):
            # Add correlation ID to exception if it's a FloatChat exception
            if isinstance(exc_val, FloatChatException) and not exc_val.correlation_id:
                exc_val.correlation_id = self.correlation_id
            
            logger.error(
                f"Error in {self.operation}",
                exception_type=exc_type.__name__,
                message=str(exc_val),
                correlation_id=self.correlation_id,
                exc_info=True
            )
        
        return False  # Don't suppress the exception
