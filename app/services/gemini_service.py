"""
FloatChat - Google Gemini API Integration Service

Comprehensive integration with Google Gemini Studio API for natural language
processing, conversation management, and intelligent response generation.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
import hashlib
import uuid

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog
import redis.asyncio as redis

from app.core.config import get_settings
from app.utils.exceptions import AIServiceError, RateLimitError

logger = structlog.get_logger(__name__)


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""
    role: str  # 'user' or 'model'
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Manages conversation context and history."""
    conversation_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    session_metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to the conversation."""
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_activity = datetime.utcnow()
        
        # Keep only last 10 exchanges (20 messages) for context window
        if len(self.messages) > 20:
            self.messages = self.messages[-20:]

    def get_context_messages(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent messages formatted for Gemini API."""
        recent_messages = self.messages[-max_messages:]
        return [
            {
                "role": msg.role,
                "parts": [{"text": msg.content}]
            }
            for msg in recent_messages
        ]


class RateLimiter:
    """Token bucket rate limiter for API quota management."""
    
    def __init__(self, max_requests: int = 15, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.tokens = max_requests
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Acquire a token for API request."""
        async with self.lock:
            now = time.time()
            # Refill tokens based on time elapsed
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * (self.max_requests / self.time_window)
            self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    def time_until_available(self) -> float:
        """Get time in seconds until next token is available."""
        if self.tokens >= 1:
            return 0
        return (1 - self.tokens) * (self.time_window / self.max_requests)


class ResponseCache:
    """Redis-based response caching system."""
    
    def __init__(self, redis_client: redis.Redis, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl
    
    def _generate_cache_key(self, prompt: str, context: str = "") -> str:
        """Generate cache key from prompt and context."""
        content = f"{prompt}:{context}"
        return f"gemini_cache:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def get(self, prompt: str, context: str = "") -> Optional[Dict[str, Any]]:
        """Get cached response."""
        try:
            cache_key = self._generate_cache_key(prompt, context)
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning("Cache retrieval failed", error=str(e))
        return None
    
    async def set(self, prompt: str, response: Dict[str, Any], context: str = ""):
        """Cache response."""
        try:
            cache_key = self._generate_cache_key(prompt, context)
            cache_data = {
                "response": response,
                "cached_at": datetime.utcnow().isoformat(),
                "ttl": self.ttl
            }
            await self.redis.setex(
                cache_key, 
                self.ttl, 
                json.dumps(cache_data, default=str)
            )
        except Exception as e:
            logger.warning("Cache storage failed", error=str(e))


class PromptManager:
    """Template-based prompt engineering system."""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, str]:
        """Initialize prompt templates for different use cases."""
        return {
            "system": """You are FloatChat, an AI assistant specialized in ARGO oceanographic data analysis. 
You help users explore ocean temperature, salinity, and biogeochemical measurements from autonomous floats.

Key capabilities:
- Answer questions about ARGO float data and ocean conditions
- Generate SQL queries for oceanographic data retrieval
- Explain oceanographic phenomena and measurements
- Provide data visualization recommendations
- Support both English and Hindi languages

Guidelines:
- Be accurate and scientific in your responses
- Explain technical terms clearly
- Suggest relevant visualizations when appropriate
- Ask clarifying questions when queries are ambiguous
- Always cite data sources and limitations""",
            
            "query_analysis": """Analyze this user query about oceanographic data:
Query: "{query}"

Context: {context}

Please identify:
1. Intent: What does the user want to know or do?
2. Entities: Locations, dates, parameters, measurements mentioned
3. Spatial scope: Geographic area of interest
4. Temporal scope: Time period of interest
5. Data requirements: What ARGO data would be needed?
6. Visualization: What charts/maps would be helpful?

Respond in JSON format with these fields: intent, entities, spatial_scope, temporal_scope, data_requirements, visualization_suggestions.""",
            
            "sql_generation": """Generate a PostgreSQL query to retrieve ARGO float data based on this request:

User Query: "{query}"
Intent: {intent}
Entities: {entities}
Spatial Scope: {spatial_scope}
Temporal Scope: {temporal_scope}

Database Schema:
- argo_floats: wmo_id, platform_number, deployment_date, deployment_latitude, deployment_longitude, status, total_profiles
- argo_profiles: float_id, cycle_number, profile_date, latitude, longitude, max_pressure, min_temperature, max_temperature, min_salinity, max_salinity, has_temperature, has_salinity, has_oxygen
- argo_measurements: profile_id, pressure, depth, temperature, salinity, oxygen, nitrate, ph, chlorophyll_a

Generate a valid PostgreSQL query with PostGIS spatial functions where needed. Include proper JOINs, WHERE clauses, and LIMIT for performance.""",
            
            "response_generation": """Generate a helpful response to the user's oceanographic query:

User Query: "{query}"
Query Results: {results}
Context: {context}

Guidelines:
- Explain the data in accessible terms
- Highlight key findings and patterns
- Suggest follow-up questions or analyses
- Recommend appropriate visualizations
- Include data quality notes and limitations
- Be conversational but scientifically accurate

Response should be informative, engaging, and actionable.""",
            
            "multilingual": """Translate this oceanographic response to {target_language}:

Original Response: "{response}"

Requirements:
- Maintain scientific accuracy
- Use appropriate oceanographic terminology
- Keep technical terms with explanations
- Preserve data values and units
- Adapt cultural context appropriately"""
        }
    
    def build_prompt(
        self, 
        template_name: str, 
        **kwargs
    ) -> str:
        """Build prompt from template with parameters."""
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        try:
            return self.templates[template_name].format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing parameter {e} for template {template_name}")
    
    def add_context(self, prompt: str, context: ConversationContext) -> str:
        """Add conversation context to prompt."""
        if not context.messages:
            return prompt
        
        context_str = "\n\nConversation History:\n"
        for msg in context.messages[-6:]:  # Last 3 exchanges
            role_label = "User" if msg.role == "user" else "Assistant"
            context_str += f"{role_label}: {msg.content}\n"
        
        return f"{prompt}{context_str}\nCurrent Query:"


class GeminiClient:
    """Async HTTP client for Google Gemini Studio API."""
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "gemini-1.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def generate_content(
        self,
        prompt: str,
        context_messages: List[Dict[str, Any]] = None,
        generation_config: Dict[str, Any] = None,
        correlation_id: str = None
    ) -> Dict[str, Any]:
        """Generate content using Gemini API with retry logic."""
        
        url = f"{self.base_url}/models/{self.model}:generateContent"
        
        # Prepare request payload
        contents = []
        
        # Add context messages if provided
        if context_messages:
            contents.extend(context_messages)
        
        # Add current prompt
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })
        
        # Default generation configuration
        default_config = {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.8,
            "maxOutputTokens": 4096,
        }
        
        if generation_config:
            default_config.update(generation_config)
        
        payload = {
            "contents": contents,
            "generationConfig": default_config
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        if correlation_id:
            headers["x-correlation-id"] = correlation_id
        
        try:
            logger.info(
                "Sending request to Gemini API",
                model=self.model,
                prompt_length=len(prompt),
                context_messages_count=len(context_messages or []),
                correlation_id=correlation_id
            )
            
            response = await self.client.post(
                url,
                json=payload,
                headers=headers
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(
                "Gemini API response received",
                status_code=response.status_code,
                correlation_id=correlation_id
            )
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "Gemini API HTTP error",
                status_code=e.response.status_code,
                error_detail=e.response.text,
                correlation_id=correlation_id
            )
            
            if e.response.status_code == 429:
                raise RateLimitError(
                    message="Gemini API rate limit exceeded",
                    correlation_id=correlation_id
                )
            elif e.response.status_code in [401, 403]:
                raise AIServiceError(
                    message="Gemini API authentication failed",
                    service="gemini",
                    correlation_id=correlation_id
                )
            else:
                raise AIServiceError(
                    message=f"Gemini API error: {e.response.status_code}",
                    service="gemini",
                    correlation_id=correlation_id
                )
        
        except httpx.RequestError as e:
            logger.error(
                "Gemini API request error",
                error=str(e),
                correlation_id=correlation_id
            )
            raise AIServiceError(
                message="Failed to connect to Gemini API",
                service="gemini",
                correlation_id=correlation_id
            )


class ConversationManager:
    """Manages conversation contexts and history."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.active_conversations: Dict[str, ConversationContext] = {}
    
    def create_conversation(
        self,
        user_id: str = None,
        session_metadata: Dict[str, Any] = None
    ) -> str:
        """Create a new conversation."""
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        
        context = ConversationContext(
            conversation_id=conversation_id,
            session_metadata=session_metadata or {}
        )
        
        if user_id:
            context.session_metadata["user_id"] = user_id
        
        self.active_conversations[conversation_id] = context
        return conversation_id
    
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation context."""
        # Check active conversations first
        if conversation_id in self.active_conversations:
            return self.active_conversations[conversation_id]
        
        # Try to load from Redis
        try:
            cached_data = await self.redis.get(f"conversation:{conversation_id}")
            if cached_data:
                data = json.loads(cached_data)
                context = ConversationContext(
                    conversation_id=conversation_id,
                    messages=[
                        ConversationMessage(**msg) for msg in data.get("messages", [])
                    ],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    last_activity=datetime.fromisoformat(data["last_activity"]),
                    user_preferences=data.get("user_preferences", {}),
                    session_metadata=data.get("session_metadata", {})
                )
                self.active_conversations[conversation_id] = context
                return context
        except Exception as e:
            logger.warning("Failed to load conversation from cache", error=str(e))
        
        return None
    
    async def save_conversation(self, context: ConversationContext):
        """Save conversation to Redis."""
        try:
            data = {
                "conversation_id": context.conversation_id,
                "messages": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "metadata": msg.metadata
                    }
                    for msg in context.messages
                ],
                "created_at": context.created_at.isoformat(),
                "last_activity": context.last_activity.isoformat(),
                "user_preferences": context.user_preferences,
                "session_metadata": context.session_metadata
            }
            
            await self.redis.setex(
                f"conversation:{context.conversation_id}",
                86400,  # 24 hours TTL
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.error("Failed to save conversation", error=str(e))
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ):
        """Add message to conversation."""
        context = await self.get_conversation(conversation_id)
        if context:
            context.add_message(role, content, metadata)
            await self.save_conversation(context)
    
    def cleanup_old_conversations(self, max_age_hours: int = 24):
        """Clean up old conversations from memory."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        conversations_to_remove = [
            conv_id for conv_id, context in self.active_conversations.items()
            if context.last_activity < cutoff_time
        ]
        
        for conv_id in conversations_to_remove:
            del self.active_conversations[conv_id]
        
        logger.info(
            "Cleaned up old conversations",
            removed_count=len(conversations_to_remove)
        )


class GeminiService:
    """Main service class for Gemini API integration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.rate_limiter = RateLimiter(
            max_requests=self.settings.gemini_rate_limit,
            time_window=self.settings.gemini_rate_window
        )
        self.prompt_manager = PromptManager()
        
        # Initialize Redis for caching and conversation management
        self.redis_client = None
        self.response_cache = None
        self.conversation_manager = None
        
        # Gemini client will be initialized per request
        self._client = None
    
    async def initialize(self):
        """Initialize Redis connections and services."""
        try:
            self.redis_client = redis.from_url(
                self.settings.redis_url,
                decode_responses=True
            )
            
            # Test Redis connection
            await self.redis_client.ping()
            
            self.response_cache = ResponseCache(
                self.redis_client,
                ttl=self.settings.cache_ttl
            )
            
            self.conversation_manager = ConversationManager(self.redis_client)
            
            logger.info("Gemini service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Gemini service", error=str(e))
            raise AIServiceError(
                message="Failed to initialize AI service",
                service="gemini"
            )
    
    async def close(self):
        """Close connections and cleanup."""
        if self.redis_client:
            await self.redis_client.close()
        if self._client:
            await self._client.__aexit__(None, None, None)
    
    async def _get_client(self) -> GeminiClient:
        """Get or create Gemini client."""
        if not self._client:
            if not self.settings.gemini_api_key:
                raise AIServiceError(
                    message="Gemini API key not configured",
                    service="gemini"
                )
            
            self._client = await GeminiClient(
                api_key=self.settings.gemini_api_key,
                model=self.settings.gemini_model
            ).__aenter__()
        
        return self._client
    
    async def process_query(
        self,
        query: str,
        conversation_id: str = None,
        user_preferences: Dict[str, Any] = None,
        correlation_id: str = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query with full context management.
        
        Args:
            query: User's natural language query
            conversation_id: Optional conversation ID for context
            user_preferences: User preferences (language, etc.)
            correlation_id: Request correlation ID
            
        Returns:
            Dict containing response, metadata, and conversation info
        """
        correlation_id = correlation_id or f"gemini_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(
                "Processing query with Gemini",
                query_length=len(query),
                conversation_id=conversation_id,
                correlation_id=correlation_id
            )
            
            # Check rate limiting
            if not await self.rate_limiter.acquire():
                wait_time = self.rate_limiter.time_until_available()
                raise RateLimitError(
                    message=f"Rate limit exceeded. Try again in {wait_time:.1f} seconds",
                    correlation_id=correlation_id
                )
            
            # Get or create conversation context
            if conversation_id:
                context = await self.conversation_manager.get_conversation(conversation_id)
            else:
                conversation_id = self.conversation_manager.create_conversation(
                    session_metadata={"preferences": user_preferences or {}}
                )
                context = await self.conversation_manager.get_conversation(conversation_id)
            
            # Check cache for similar queries
            cache_context = json.dumps(context.get_context_messages(3), default=str)
            cached_response = await self.response_cache.get(query, cache_context)
            
            if cached_response:
                logger.info(
                    "Returning cached response",
                    correlation_id=correlation_id
                )
                return {
                    "response": cached_response["response"],
                    "conversation_id": conversation_id,
                    "cached": True,
                    "correlation_id": correlation_id
                }
            
            # Build prompt with context
            system_prompt = self.prompt_manager.build_prompt("system")
            contextualized_prompt = self.prompt_manager.add_context(query, context)
            
            # Prepare context messages for API
            context_messages = [
                {"role": "user", "parts": [{"text": system_prompt}]},
                {"role": "model", "parts": [{"text": "I understand. I'm FloatChat, ready to help with ARGO oceanographic data analysis."}]}
            ]
            context_messages.extend(context.get_context_messages())
            
            # Generate response
            client = await self._get_client()
            
            generation_config = {
                "temperature": self.settings.gemini_temperature,
                "topP": self.settings.gemini_top_p,
                "topK": self.settings.gemini_top_k,
                "maxOutputTokens": self.settings.gemini_max_tokens
            }
            
            result = await client.generate_content(
                prompt=contextualized_prompt,
                context_messages=context_messages,
                generation_config=generation_config,
                correlation_id=correlation_id
            )
            
            # Extract response text
            response_text = self._extract_response_text(result)
            
            # Add messages to conversation
            await self.conversation_manager.add_message(
                conversation_id, "user", query
            )
            await self.conversation_manager.add_message(
                conversation_id, "model", response_text
            )
            
            # Cache response
            response_data = {
                "text": response_text,
                "metadata": {
                    "model": self.settings.gemini_model,
                    "generation_config": generation_config,
                    "processing_time": time.time()
                }
            }
            
            await self.response_cache.set(query, response_data, cache_context)
            
            logger.info(
                "Query processed successfully",
                response_length=len(response_text),
                correlation_id=correlation_id
            )
            
            return {
                "response": response_text,
                "conversation_id": conversation_id,
                "metadata": response_data["metadata"],
                "cached": False,
                "correlation_id": correlation_id
            }
            
        except (RateLimitError, AIServiceError):
            raise
        except Exception as e:
            logger.error(
                "Query processing failed",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise AIServiceError(
                message="Failed to process query",
                service="gemini",
                correlation_id=correlation_id
            )
    
    def _extract_response_text(self, gemini_response: Dict[str, Any]) -> str:
        """Extract text from Gemini API response."""
        try:
            candidates = gemini_response.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in response")
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            
            if not parts:
                raise ValueError("No parts in response content")
            
            return parts[0].get("text", "")
            
        except Exception as e:
            logger.error("Failed to extract response text", error=str(e))
            raise AIServiceError(
                message="Invalid response format from Gemini API",
                service="gemini"
            )
    
    async def analyze_query_intent(
        self,
        query: str,
        correlation_id: str = None
    ) -> Dict[str, Any]:
        """Analyze query intent and extract entities."""
        try:
            prompt = self.prompt_manager.build_prompt(
                "query_analysis",
                query=query,
                context="ARGO oceanographic data analysis"
            )
            
            client = await self._get_client()
            result = await client.generate_content(
                prompt=prompt,
                generation_config={"temperature": 0.3},  # Lower temperature for analysis
                correlation_id=correlation_id
            )
            
            response_text = self._extract_response_text(result)
            
            # Try to parse JSON response
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback to text response
                return {
                    "intent": "general_query",
                    "analysis": response_text,
                    "entities": [],
                    "spatial_scope": None,
                    "temporal_scope": None
                }
                
        except Exception as e:
            logger.error("Query intent analysis failed", error=str(e))
            return {
                "intent": "unknown",
                "error": str(e),
                "entities": [],
                "spatial_scope": None,
                "temporal_scope": None
            }
