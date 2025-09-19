"""
FloatChat - AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization

Main FastAPI application entry point.
SIH 25 Problem Statement ID: 25040
Organization: Ministry of Earth Sciences (MoES) - INCOIS
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import structlog

from app.core.config import get_settings
from app.core.database import init_database, close_database
from app.core.security import setup_security_headers, add_security_headers_to_response
from app.api import chat, voice, floats, dashboard, websocket, real_chat
from app.utils.exceptions import setup_exception_handlers

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("FloatChat starting up", version=app.version)
    
    try:
        # Initialize database connections
        await init_database()
        logger.info("Database initialized successfully")
        
        # Log RAG service configuration
        try:
            from app.services.rag_service import DefaultRAGPipeline
            logger.info("RAG service configured", pipeline_type=DefaultRAGPipeline.__name__)
        except Exception as e:
            logger.warning("RAG service configuration check failed", error=str(e))
        
        # Initialize vector database
        # TODO: Initialize FAISS/ChromaDB
        
        # Initialize AI services
        # TODO: Initialize Gemini API client
        
        logger.info("FloatChat startup completed successfully")
        
    except Exception as e:
        logger.error("Failed to start FloatChat", error=str(e), exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("FloatChat shutting down")
    
    try:
        # Close database connections
        await close_database()
        logger.info("Database connections closed")
        
        # Cleanup AI services
        # TODO: Cleanup Gemini API client
        
        # Cleanup vector database
        # TODO: Cleanup FAISS/ChromaDB
        
        logger.info("FloatChat shutdown completed successfully")
        
    except Exception as e:
        logger.error("Error during FloatChat shutdown", error=str(e), exc_info=True)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    settings = get_settings()
    
    # Create FastAPI app with metadata
    app = FastAPI(
        title="FloatChat API",
        description="AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization",
        version="1.0.0",
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url="/redoc" if settings.environment == "development" else None,
        openapi_url="/openapi.json" if settings.environment == "development" else None,
        lifespan=lifespan
    )
    
    # Setup security middleware and CORS
    setup_security_headers(app)
    
    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        return add_security_headers_to_response(response)
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        # Generate correlation ID for request tracking
        correlation_id = request.headers.get("X-Correlation-ID", f"req_{id(request)}")
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        # Log request
        logger.info(
            "Request received",
            method=request.method,
            url=str(request.url),
            correlation_id=correlation_id,
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Log response
            logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                correlation_id=correlation_id
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware for security
    if settings.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts
        )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Add test page route
    @app.get("/test", response_class=HTMLResponse)
    async def test_page():
        """Serve the test HTML page."""
        try:
            with open("test_api.html", "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse(content="<h1>Test page not found</h1><p>test_api.html is missing</p>")
    
    # Include API routers
    app.include_router(
        real_chat.router,
        prefix=f"{settings.api_v1_prefix}/chat",
        tags=["Real AI Chat & Ocean Analysis"]
    )
    
    app.include_router(
        voice.router,
        prefix=f"{settings.api_v1_prefix}/voice",
        tags=["Voice Processing"]
    )
    
    app.include_router(
        floats.router,
        prefix=f"{settings.api_v1_prefix}/floats",
        tags=["ARGO Float Data"]
    )
    
    
    app.include_router(
        dashboard.router,
        prefix=f"{settings.api_v1_prefix}/dashboard",
        tags=["Dashboard & Statistics"]
    )
    
    app.include_router(
        websocket.router,
        prefix=f"{settings.api_v1_prefix}/ws",
        tags=["WebSocket Connections"]
    )
    
    # Mount static files
    if os.path.exists("frontend/static"):
        app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint for monitoring."""
        return {
            "status": "healthy",
            "service": "FloatChat",
            "version": app.version,
            "environment": settings.environment
        }
    
    # Root endpoint
    @app.get("/")
    async def root() -> Dict[str, str]:
        """Root endpoint with API information."""
        return {
            "message": "Welcome to FloatChat API",
            "description": "AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization",
            "version": app.version,
            "docs": "/docs" if settings.environment == "development" else "Documentation not available in production",
            "health": "/health"
        }
    
    logger.info("FloatChat app created successfully", environment=settings.environment)
    
    return app


# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
        access_log=True
    )
