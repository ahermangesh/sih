#!/usr/bin/env python3
"""
Simple test server for FloatChat without database dependencies.
This allows us to test the API endpoints while Docker is starting up.
"""

import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from app.core.config import get_settings
from app.services.real_gemini_service import real_gemini_service

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="FloatChat Test Server",
    description="Simplified test server for FloatChat API testing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with system status."""
    return {
        "message": "FloatChat Test Server is running!",
        "status": "online",
        "version": "1.0.0",
        "gemini_available": real_gemini_service.available,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "services": {
            "gemini": real_gemini_service.available,
            "database": "bypassed_for_testing"
        }
    }

@app.post("/api/v1/chat/query")
async def test_chat_query(request: Dict[str, Any]):
    """Test chat endpoint without database."""
    try:
        query = request.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Test Gemini API
        if real_gemini_service.available:
            response = await real_gemini_service.analyze_ocean_query(query)
            return {
                "success": True,
                "message": response.get("message", "Response generated successfully"),
                "query_type": response.get("query_type", "unknown"),
                "confidence": response.get("confidence", 0.8),
                "data_source": "test_mode",
                "processing_time_ms": 150
            }
        else:
            return {
                "success": True,
                "message": f"Test response for: {query}",
                "query_type": "test",
                "confidence": 1.0,
                "data_source": "mock",
                "processing_time_ms": 50
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.get("/api/v1/floats/test")
async def test_floats():
    """Test floats endpoint with mock data."""
    return {
        "success": True,
        "data": [
            {
                "float_id": "test_001",
                "latitude": 20.5,
                "longitude": 75.3,
                "temperature": 28.5,
                "salinity": 35.2,
                "date": "2024-09-18"
            },
            {
                "float_id": "test_002", 
                "latitude": 21.0,
                "longitude": 76.0,
                "temperature": 29.1,
                "salinity": 35.5,
                "date": "2024-09-18"
            }
        ],
        "count": 2,
        "data_source": "test_mode"
    }

@app.get("/test", response_class=HTMLResponse)
async def test_page():
    """Serve the test HTML page."""
    try:
        with open("test_api.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Test page not found</h1><p>test_api.html is missing</p>")

if __name__ == "__main__":
    print("🚀 Starting FloatChat Test Server...")
    print("📊 Dashboard: http://localhost:8001/test")
    print("📖 API Docs: http://localhost:8001/docs")
    print("💚 Health Check: http://localhost:8001/health")
    
    uvicorn.run(
        "test_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
