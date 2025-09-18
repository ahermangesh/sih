"""
FloatChat - WebSocket API Endpoints

Real-time WebSocket connections for live chat, notifications, and data updates.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.websockets import WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.services.gemini_service import GeminiClient
from app.services.voice_service import voice_service
from app.services.translation_service import multilingual_service

logger = structlog.get_logger(__name__)
router = APIRouter()
settings = get_settings()


class ConnectionManager:
    """Manages WebSocket connections for real-time features."""
    
    def __init__(self):
        # Active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        # Chat connections by conversation ID
        self.chat_connections: Dict[str, List[str]] = {}
        # Dashboard connections for real-time updates
        self.dashboard_connections: List[str] = []
        
    async def connect(self, websocket: WebSocket, connection_id: str, connection_type: str = "general"):
        """Accept a WebSocket connection and register it."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if connection_type == "dashboard":
            self.dashboard_connections.append(connection_id)
        
        logger.info(
            "WebSocket connection established",
            connection_id=connection_id,
            connection_type=connection_type,
            total_connections=len(self.active_connections)
        )
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "WebSocket connection established successfully"
        }, connection_id)
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if connection_id in self.dashboard_connections:
            self.dashboard_connections.remove(connection_id)
        
        # Remove from chat connections
        for conversation_id, connections in self.chat_connections.items():
            if connection_id in connections:
                connections.remove(connection_id)
                if not connections:
                    del self.chat_connections[conversation_id]
                break
        
        logger.info(
            "WebSocket connection closed",
            connection_id=connection_id,
            remaining_connections=len(self.active_connections)
        )
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(
                    "Failed to send personal message",
                    connection_id=connection_id,
                    error=str(e)
                )
                # Connection might be dead, remove it
                self.disconnect(connection_id)
    
    async def broadcast_to_chat(self, message: Dict[str, Any], conversation_id: str, exclude_connection: Optional[str] = None):
        """Broadcast a message to all connections in a chat conversation."""
        if conversation_id in self.chat_connections:
            connections = self.chat_connections[conversation_id].copy()
            for connection_id in connections:
                if connection_id != exclude_connection:
                    await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_dashboard(self, message: Dict[str, Any]):
        """Broadcast a message to all dashboard connections."""
        disconnected = []
        for connection_id in self.dashboard_connections.copy():
            try:
                await self.send_personal_message(message, connection_id)
            except Exception:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            self.disconnect(connection_id)
    
    def join_chat(self, connection_id: str, conversation_id: str):
        """Add a connection to a chat conversation."""
        if conversation_id not in self.chat_connections:
            self.chat_connections[conversation_id] = []
        
        if connection_id not in self.chat_connections[conversation_id]:
            self.chat_connections[conversation_id].append(connection_id)
        
        logger.info(
            "Connection joined chat",
            connection_id=connection_id,
            conversation_id=conversation_id
        )
    
    def leave_chat(self, connection_id: str, conversation_id: str):
        """Remove a connection from a chat conversation."""
        if conversation_id in self.chat_connections:
            if connection_id in self.chat_connections[conversation_id]:
                self.chat_connections[conversation_id].remove(connection_id)
                
                if not self.chat_connections[conversation_id]:
                    del self.chat_connections[conversation_id]
        
        logger.info(
            "Connection left chat",
            connection_id=connection_id,
            conversation_id=conversation_id
        )


# Global connection manager
connection_manager = ConnectionManager()


@router.websocket("/chat/{connection_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    connection_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat functionality.
    
    Supports:
    - Real-time message exchange
    - Typing indicators
    - Voice message processing
    - Multi-language support
    """
    await connection_manager.connect(websocket, connection_id, "chat")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_chat_message(message, connection_id, websocket, db)
                
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
                
            except Exception as e:
                logger.error(
                    "Error handling chat message",
                    connection_id=connection_id,
                    error=str(e),
                    exc_info=True
                )
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Failed to process message",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
                
    except WebSocketDisconnect:
        connection_manager.disconnect(connection_id)
    except Exception as e:
        logger.error(
            "WebSocket chat error",
            connection_id=connection_id,
            error=str(e),
            exc_info=True
        )
        connection_manager.disconnect(connection_id)


@router.websocket("/dashboard/{connection_id}")
async def websocket_dashboard_endpoint(
    websocket: WebSocket,
    connection_id: str
):
    """
    WebSocket endpoint for real-time dashboard updates.
    
    Supports:
    - Live statistics updates
    - Activity feed updates
    - System notifications
    - Performance metrics
    """
    await connection_manager.connect(websocket, connection_id, "dashboard")
    
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_dashboard_message(message, connection_id)
                
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
                
    except WebSocketDisconnect:
        connection_manager.disconnect(connection_id)
    except Exception as e:
        logger.error(
            "WebSocket dashboard error",
            connection_id=connection_id,
            error=str(e),
            exc_info=True
        )
        connection_manager.disconnect(connection_id)


async def handle_chat_message(message: Dict[str, Any], connection_id: str, websocket: WebSocket, db: AsyncSession):
    """Handle incoming chat messages from WebSocket clients."""
    message_type = message.get("type")
    
    if message_type == "join_conversation":
        conversation_id = message.get("conversation_id")
        if conversation_id:
            connection_manager.join_chat(connection_id, conversation_id)
            
            # Notify other participants
            await connection_manager.broadcast_to_chat({
                "type": "user_joined",
                "connection_id": connection_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            }, conversation_id, exclude_connection=connection_id)
    
    elif message_type == "leave_conversation":
        conversation_id = message.get("conversation_id")
        if conversation_id:
            connection_manager.leave_chat(connection_id, conversation_id)
            
            # Notify other participants
            await connection_manager.broadcast_to_chat({
                "type": "user_left",
                "connection_id": connection_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            }, conversation_id)
    
    elif message_type == "typing_start":
        conversation_id = message.get("conversation_id")
        if conversation_id:
            await connection_manager.broadcast_to_chat({
                "type": "typing_indicator",
                "status": "start",
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat()
            }, conversation_id, exclude_connection=connection_id)
    
    elif message_type == "typing_stop":
        conversation_id = message.get("conversation_id")
        if conversation_id:
            await connection_manager.broadcast_to_chat({
                "type": "typing_indicator",
                "status": "stop",
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat()
            }, conversation_id, exclude_connection=connection_id)
    
    elif message_type == "chat_message":
        await process_chat_message(message, connection_id, db)
    
    elif message_type == "voice_message":
        await process_voice_message(message, connection_id, db)
    
    elif message_type == "ping":
        await connection_manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)


async def handle_dashboard_message(message: Dict[str, Any], connection_id: str):
    """Handle incoming dashboard messages from WebSocket clients."""
    message_type = message.get("type")
    
    if message_type == "request_stats_update":
        # Trigger a stats update for this connection
        await send_dashboard_stats_update(connection_id)
    
    elif message_type == "subscribe_to_updates":
        update_types = message.get("update_types", [])
        # Store subscription preferences (could be stored in connection metadata)
        await connection_manager.send_personal_message({
            "type": "subscription_confirmed",
            "update_types": update_types,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
    
    elif message_type == "ping":
        await connection_manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)


async def process_chat_message(message: Dict[str, Any], connection_id: str, db: AsyncSession):
    """Process a chat message and generate AI response."""
    try:
        user_message = message.get("message", "")
        conversation_id = message.get("conversation_id", "")
        language = message.get("language", "en")
        
        if not user_message.strip():
            return
        
        # Send typing indicator
        await connection_manager.broadcast_to_chat({
            "type": "ai_typing",
            "status": "start",
            "timestamp": datetime.utcnow().isoformat()
        }, conversation_id)
        
        # Process message with AI (mock implementation)
        # In production, this would use the actual Gemini service
        await asyncio.sleep(1)  # Simulate processing time
        
        ai_response = {
            "type": "ai_message",
            "message": f"I understand you're asking about: '{user_message}'. This is a mock response for WebSocket testing.",
            "conversation_id": conversation_id,
            "language": language,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "processing_time": 1.0,
                "confidence": 0.95
            }
        }
        
        # Stop typing indicator
        await connection_manager.broadcast_to_chat({
            "type": "ai_typing",
            "status": "stop",
            "timestamp": datetime.utcnow().isoformat()
        }, conversation_id)
        
        # Send AI response
        await connection_manager.broadcast_to_chat(ai_response, conversation_id)
        
        logger.info(
            "Chat message processed",
            connection_id=connection_id,
            conversation_id=conversation_id,
            language=language
        )
        
    except Exception as e:
        logger.error(
            "Failed to process chat message",
            connection_id=connection_id,
            error=str(e),
            exc_info=True
        )


async def process_voice_message(message: Dict[str, Any], connection_id: str, db: AsyncSession):
    """Process a voice message through speech recognition."""
    try:
        audio_data = message.get("audio_data", "")
        conversation_id = message.get("conversation_id", "")
        language = message.get("language", "en")
        
        if not audio_data:
            return
        
        # Send processing indicator
        await connection_manager.send_personal_message({
            "type": "voice_processing",
            "status": "start",
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
        # Process voice (mock implementation)
        # In production, this would use the actual voice service
        await asyncio.sleep(2)  # Simulate processing time
        
        transcribed_text = "This is a mock transcription of your voice message."
        
        # Send transcription result
        await connection_manager.send_personal_message({
            "type": "voice_transcription",
            "transcription": transcribed_text,
            "language": language,
            "confidence": 0.92,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
        # Process as regular chat message
        await process_chat_message({
            "message": transcribed_text,
            "conversation_id": conversation_id,
            "language": language
        }, connection_id, db)
        
        logger.info(
            "Voice message processed",
            connection_id=connection_id,
            conversation_id=conversation_id,
            language=language
        )
        
    except Exception as e:
        logger.error(
            "Failed to process voice message",
            connection_id=connection_id,
            error=str(e),
            exc_info=True
        )


async def send_dashboard_stats_update(connection_id: Optional[str] = None):
    """Send dashboard statistics update to connections."""
    stats_update = {
        "type": "stats_update",
        "data": {
            "floats_count": 1247,
            "profiles_count": 45892,
            "queries_today": 1856,
            "active_users": len(connection_manager.active_connections),
            "system_status": "healthy"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if connection_id:
        await connection_manager.send_personal_message(stats_update, connection_id)
    else:
        await connection_manager.broadcast_to_dashboard(stats_update)


async def send_activity_update(activity: Dict[str, Any]):
    """Send new activity update to dashboard connections."""
    activity_update = {
        "type": "activity_update",
        "activity": activity,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await connection_manager.broadcast_to_dashboard(activity_update)


# Background task to send periodic updates
async def periodic_dashboard_updates():
    """Send periodic updates to dashboard connections."""
    while True:
        try:
            if connection_manager.dashboard_connections:
                await send_dashboard_stats_update()
            
            await asyncio.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            logger.error("Error in periodic dashboard updates", error=str(e), exc_info=True)
            await asyncio.sleep(60)  # Wait longer on error


# Start background task (would be started in app lifespan)
# asyncio.create_task(periodic_dashboard_updates())


@router.get("/connections/stats")
async def get_connection_stats():
    """Get current WebSocket connection statistics."""
    return {
        "total_connections": len(connection_manager.active_connections),
        "chat_conversations": len(connection_manager.chat_connections),
        "dashboard_connections": len(connection_manager.dashboard_connections),
        "active_chats": sum(len(conns) for conns in connection_manager.chat_connections.values()),
        "timestamp": datetime.utcnow().isoformat()
    }
