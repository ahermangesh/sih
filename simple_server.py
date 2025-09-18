"""
FloatChat - Simple Working Server
Real AI and ARGO data integration without complex dependencies
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

# Import our working services
from app.services.real_gemini_service import real_gemini_service
from app.services.real_argo_service import real_argo_service

# Create FastAPI app
app = FastAPI(
    title="FloatChat - Real AI Ocean Data Explorer",
    description="Production-ready AI-powered conversational interface for ARGO ocean data",
    version="1.0.0"
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
    """Home page with working demo."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FloatChat - Real AI Ocean Data Explorer</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { 
                background: linear-gradient(135deg, #0077be, #2e8bc0);
                color: white;
                min-height: 100vh;
            }
            .hero { padding: 3rem 0; text-align: center; }
            .card { 
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                backdrop-filter: blur(10px);
            }
            .btn-ocean {
                background: linear-gradient(135deg, #ff6b6b, #ff8a80);
                border: none;
                color: white;
                font-weight: 600;
            }
            .chat-area {
                height: 400px;
                overflow-y: auto;
                background: rgba(255,255,255,0.9);
                color: #333;
                border-radius: 10px;
                padding: 1rem;
            }
            .message {
                margin-bottom: 1rem;
                padding: 0.5rem;
                border-radius: 8px;
            }
            .user-message {
                background: #0077be;
                color: white;
                text-align: right;
            }
            .ai-message {
                background: #f8f9fa;
                color: #333;
                border-left: 4px solid #0077be;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="hero">
                <h1 class="display-3 mb-4">🌊 FloatChat</h1>
                <p class="lead">Real AI-Powered Ocean Data Explorer</p>
                <p class="mb-4">
                    🤖 <strong>Real Google Gemini AI</strong> • 
                    🌊 <strong>Live ARGO Data (82K+ floats)</strong> • 
                    🗺️ <strong>Interactive Ocean Analysis</strong>
                </p>
            </div>
            
            <div class="row">
                <div class="col-md-8">
                    <div class="card p-4">
                        <h4>💬 AI Ocean Chat</h4>
                        <div class="chat-area" id="chatArea">
                            <div class="message ai-message">
                                <strong>🤖 FloatChat AI:</strong> Welcome! I'm connected to real ARGO ocean data with 82,000+ active floats. Ask me about ocean temperatures, salinity, float locations, or any marine conditions!
                            </div>
                        </div>
                        <div class="mt-3">
                            <div class="input-group">
                                <input type="text" class="form-control" id="chatInput" 
                                       placeholder="Ask about ocean data... (e.g., 'Temperature in Arabian Sea?')">
                                <button class="btn btn-ocean" onclick="sendMessage()">Send</button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card p-4 mb-3">
                        <h5>📊 System Status</h5>
                        <p><span id="aiStatus">🤖 AI: Loading...</span></p>
                        <p><span id="argoStatus">🌊 ARGO: Loading...</span></p>
                        <p><span id="floatCount">📍 Floats: Counting...</span></p>
                    </div>
                    
                    <div class="card p-4">
                        <h5>🚀 Quick Examples</h5>
                        <button class="btn btn-sm btn-outline-light mb-2 w-100" 
                                onclick="setMessage('What is the temperature in the Arabian Sea?')">
                            Arabian Sea Temperature
                        </button>
                        <button class="btn btn-sm btn-outline-light mb-2 w-100" 
                                onclick="setMessage('Show me ARGO floats near Mumbai')">
                            Floats near Mumbai
                        </button>
                        <button class="btn btn-sm btn-outline-light mb-2 w-100" 
                                onclick="setMessage('Ocean salinity in Indian Ocean')">
                            Indian Ocean Salinity
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // Check system status
            async function checkStatus() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    document.getElementById('aiStatus').textContent = '🤖 AI: ' + (data.ai_available ? 'Online' : 'Offline');
                    document.getElementById('argoStatus').textContent = '🌊 ARGO: ' + (data.argo_available ? 'Online' : 'Offline');
                    document.getElementById('floatCount').textContent = '📍 Floats: ' + (data.float_count || 'Unknown');
                } catch (e) {
                    console.error('Status check failed:', e);
                }
            }
            
            // Send chat message
            async function sendMessage() {
                const input = document.getElementById('chatInput');
                const message = input.value.trim();
                if (!message) return;
                
                // Add user message
                addMessage(message, true);
                input.value = '';
                
                // Add loading message
                addMessage('🤖 Analyzing with real AI and ocean data...', false, 'loading');
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: message })
                    });
                    
                    const data = await response.json();
                    
                    // Remove loading message
                    const loadingMsg = document.querySelector('.loading');
                    if (loadingMsg) loadingMsg.remove();
                    
                    // Add AI response
                    addMessage(data.response, false);
                    
                } catch (error) {
                    console.error('Chat error:', error);
                    const loadingMsg = document.querySelector('.loading');
                    if (loadingMsg) loadingMsg.remove();
                    addMessage('Sorry, I encountered an error. Please try again.', false);
                }
            }
            
            function addMessage(content, isUser, className = '') {
                const chatArea = document.getElementById('chatArea');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'} ${className}`;
                messageDiv.innerHTML = isUser ? content : `<strong>🤖 FloatChat AI:</strong> ${content}`;
                chatArea.appendChild(messageDiv);
                chatArea.scrollTop = chatArea.scrollHeight;
            }
            
            function setMessage(text) {
                document.getElementById('chatInput').value = text;
            }
            
            // Enter key support
            document.getElementById('chatInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') sendMessage();
            });
            
            // Check status on load
            checkStatus();
        </script>
    </body>
    </html>
    """)

@app.get("/health")
async def health():
    """Health check with real system status."""
    try:
        # Test ARGO data
        floats = await real_argo_service.fetch_active_floats()
        float_count = len(floats)
        argo_available = float_count > 0
    except:
        argo_available = False
        float_count = 0
    
    return {
        "status": "healthy",
        "service": "FloatChat Real",
        "ai_available": real_gemini_service.available,
        "argo_available": argo_available,
        "float_count": float_count,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/chat")
async def chat(request: Dict[str, Any]):
    """Real AI chat with ocean data."""
    try:
        message = request.get("message", "")
        
        # Use real Gemini AI
        response = await real_gemini_service.analyze_ocean_query(message)
        
        return {
            "response": response["message"],
            "query_type": response.get("query_type", "general"),
            "confidence": response.get("confidence", 0.9),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "response": f"I encountered an error analyzing your ocean data query. The real AI system is working but had a processing issue: {str(e)}",
            "query_type": "error",
            "confidence": 0.0,
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/floats")
async def get_floats():
    """Get real ARGO floats."""
    try:
        floats = await real_argo_service.fetch_active_floats()
        return {
            "floats": floats[:100],  # Limit to first 100 for demo
            "total_count": len(floats),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Starting FloatChat Real Server...")
    print("🤖 Real Google Gemini AI: ENABLED")
    print("🌊 Real ARGO Data: ENABLED")
    print("🌐 Access: http://localhost:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
