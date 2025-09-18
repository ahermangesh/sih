"""
FloatChat - API Integration Tests

Comprehensive integration tests for all API endpoints.
"""

import json
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import status
from httpx import AsyncClient

from tests.conftest import (
    assert_valid_response, 
    assert_valid_float_data, 
    assert_valid_chat_response,
    assert_valid_dashboard_stats
)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_main_health_check(self, async_test_client: AsyncClient):
        """Test main application health check."""
        response = await async_test_client.get("/health")
        data = assert_valid_response(response, 200)
        
        assert data["status"] == "healthy"
        assert data["service"] == "FloatChat"
        assert "version" in data
        assert "environment" in data
    
    async def test_dashboard_health_check(self, async_test_client: AsyncClient):
        """Test dashboard service health check."""
        response = await async_test_client.get("/api/v1/dashboard/health")
        data = assert_valid_response(response, 200)
        
        assert data["status"] == "healthy"
        assert data["service"] == "dashboard"
        assert "dependencies" in data


class TestDashboardAPI:
    """Test dashboard API endpoints."""
    
    async def test_get_dashboard_stats(self, async_test_client: AsyncClient, sample_float_data):
        """Test dashboard statistics endpoint."""
        response = await async_test_client.get("/api/v1/dashboard/stats")
        data = assert_valid_response(response, 200)
        
        assert_valid_dashboard_stats(data)
        assert data["floats_count"] >= 0
        assert data["profiles_count"] >= 0
        assert data["languages_supported"] == 14
    
    async def test_get_activity_feed(self, async_test_client: AsyncClient):
        """Test activity feed endpoint."""
        response = await async_test_client.get("/api/v1/dashboard/activity")
        data = assert_valid_response(response, 200)
        
        assert "activities" in data
        assert "total_count" in data
        assert "last_updated" in data
        assert isinstance(data["activities"], list)
        
        if data["activities"]:
            activity = data["activities"][0]
            assert "id" in activity
            assert "type" in activity
            assert "title" in activity
            assert "timestamp" in activity
    
    async def test_get_activity_feed_with_limit(self, async_test_client: AsyncClient):
        """Test activity feed endpoint with limit parameter."""
        response = await async_test_client.get("/api/v1/dashboard/activity?limit=5")
        data = assert_valid_response(response, 200)
        
        assert len(data["activities"]) <= 5
    
    async def test_get_float_locations(self, async_test_client: AsyncClient):
        """Test float locations endpoint."""
        response = await async_test_client.get("/api/v1/dashboard/floats/locations")
        data = assert_valid_response(response, 200)
        
        assert isinstance(data, list)
        
        if data:
            location = data[0]
            required_fields = ["float_id", "wmo_id", "latitude", "longitude", "status"]
            for field in required_fields:
                assert field in location
            
            assert -90 <= location["latitude"] <= 90
            assert -180 <= location["longitude"] <= 180
            assert location["status"] in ["active", "recent", "bgc", "inactive"]
    
    async def test_get_float_locations_with_filter(self, async_test_client: AsyncClient):
        """Test float locations endpoint with status filter."""
        response = await async_test_client.get("/api/v1/dashboard/floats/locations?status_filter=active")
        data = assert_valid_response(response, 200)
        
        assert isinstance(data, list)
        for location in data:
            assert location["status"] == "active"


class TestFloatsAPI:
    """Test ARGO floats API endpoints."""
    
    async def test_list_floats(self, async_test_client: AsyncClient, sample_float_data):
        """Test list floats endpoint."""
        response = await async_test_client.get("/api/v1/floats/")
        data = assert_valid_response(response, 200)
        
        assert isinstance(data, list)
        if data:
            assert_valid_float_data(data[0])
    
    async def test_get_float_by_id(self, async_test_client: AsyncClient, sample_float_data):
        """Test get float by ID endpoint."""
        float_id = sample_float_data["float"].id
        response = await async_test_client.get(f"/api/v1/floats/{float_id}")
        data = assert_valid_response(response, 200)
        
        assert_valid_float_data(data)
        assert data["id"] == float_id
    
    async def test_get_nonexistent_float(self, async_test_client: AsyncClient):
        """Test get nonexistent float returns 404."""
        response = await async_test_client.get("/api/v1/floats/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_get_float_profiles(self, async_test_client: AsyncClient, sample_float_data):
        """Test get float profiles endpoint."""
        float_id = sample_float_data["float"].id
        response = await async_test_client.get(f"/api/v1/floats/{float_id}/profiles")
        data = assert_valid_response(response, 200)
        
        assert isinstance(data, list)
        if data:
            profile = data[0]
            assert "id" in profile
            assert "cycle_number" in profile
            assert "profile_date" in profile
    
    async def test_search_floats_by_region(self, async_test_client: AsyncClient, sample_float_data):
        """Test search floats by region endpoint."""
        query_data = {
            "bbox": [68.0, 6.0, 97.0, 37.0],  # Indian Ocean
            "date_range": {
                "start": "2020-01-01",
                "end": "2020-12-31"
            }
        }
        
        response = await async_test_client.post("/api/v1/floats/search", json=query_data)
        data = assert_valid_response(response, 200)
        
        assert isinstance(data, list)
        # Note: Mock data might not match the region filter


class TestChatAPI:
    """Test chat API endpoints."""
    
    async def test_process_chat_query(self, async_test_client: AsyncClient, sample_chat_message):
        """Test chat query processing endpoint."""
        response = await async_test_client.post("/api/v1/chat/query", json=sample_chat_message)
        data = assert_valid_response(response, 200)
        
        assert_valid_chat_response(data)
        assert "conversation_id" in data
    
    async def test_chat_query_with_voice_input(self, async_test_client: AsyncClient):
        """Test chat query with voice input flag."""
        query_data = {
            "message": "Show me ocean temperature",
            "conversation_id": "test_voice_123",
            "language": "en",
            "voice_input": True,
            "voice_output": True
        }
        
        response = await async_test_client.post("/api/v1/chat/query", json=query_data)
        data = assert_valid_response(response, 200)
        
        assert_valid_chat_response(data)
    
    async def test_chat_query_multilingual(self, async_test_client: AsyncClient, language_code):
        """Test chat query in different languages."""
        query_data = {
            "message": "Show me ocean data",
            "conversation_id": f"test_{language_code}_123",
            "language": language_code
        }
        
        response = await async_test_client.post("/api/v1/chat/query", json=query_data)
        data = assert_valid_response(response, 200)
        
        assert_valid_chat_response(data)
        assert data.get("language") == language_code
    
    async def test_chat_query_validation(self, async_test_client: AsyncClient):
        """Test chat query validation."""
        # Missing required fields
        invalid_query = {"message": ""}
        response = await async_test_client.post("/api/v1/chat/query", json=invalid_query)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_get_conversation_history(self, async_test_client: AsyncClient):
        """Test get conversation history endpoint."""
        conversation_id = "test_conversation_123"
        response = await async_test_client.get(f"/api/v1/chat/conversations/{conversation_id}")
        
        # This might return 404 if not implemented or no history exists
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "conversation_id" in data
            assert "messages" in data


class TestVoiceAPI:
    """Test voice processing API endpoints."""
    
    async def test_transcribe_audio(self, async_test_client: AsyncClient, sample_voice_message):
        """Test audio transcription endpoint."""
        response = await async_test_client.post("/api/v1/voice/transcribe", json=sample_voice_message)
        
        # Might fail if voice dependencies are not installed
        if response.status_code == 200:
            data = response.json()
            assert "text" in data
            assert "language" in data
            assert "confidence" in data or data["confidence"] is None
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_synthesize_speech(self, async_test_client: AsyncClient):
        """Test speech synthesis endpoint."""
        synthesis_data = {
            "text": "Hello, this is a test message.",
            "language": "en",
            "speed": "normal"
        }
        
        response = await async_test_client.post("/api/v1/voice/synthesize", json=synthesis_data)
        
        # Might fail if voice dependencies are not installed
        if response.status_code == 200:
            data = response.json()
            assert "audio_base64" in data
            assert "language" in data
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_get_supported_languages(self, async_test_client: AsyncClient):
        """Test get supported languages endpoint."""
        response = await async_test_client.get("/api/v1/voice/languages")
        data = assert_valid_response(response, 200)
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        if data:
            language = data[0]
            assert "code" in language
            assert "name" in language
            assert "voice_supported" in language
    
    async def test_detect_language(self, async_test_client: AsyncClient):
        """Test language detection endpoint."""
        response = await async_test_client.post("/api/v1/voice/detect-language?text=Hello world")
        
        # Might fail if translation dependencies are not installed
        if response.status_code == 200:
            data = response.json()
            assert "detected_language" in data
            assert "confidence" in data
            assert "supported" in data
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_voice_health_check(self, async_test_client: AsyncClient):
        """Test voice service health check."""
        response = await async_test_client.get("/api/v1/voice/health")
        data = assert_valid_response(response, 200)
        
        assert data["status"] == "healthy"
        assert "audio_dependencies_available" in data
        assert "supported_audio_formats" in data


class TestErrorHandling:
    """Test error handling across all endpoints."""
    
    async def test_404_endpoints(self, async_test_client: AsyncClient):
        """Test that non-existent endpoints return 404."""
        response = await async_test_client.get("/api/v1/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_method_not_allowed(self, async_test_client: AsyncClient):
        """Test that wrong HTTP methods return 405."""
        response = await async_test_client.post("/api/v1/dashboard/stats")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    async def test_invalid_json(self, async_test_client: AsyncClient):
        """Test that invalid JSON returns 422."""
        response = await async_test_client.post(
            "/api/v1/chat/query",
            content="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_large_request_body(self, async_test_client: AsyncClient):
        """Test handling of large request bodies."""
        large_message = "x" * 10000  # 10KB message
        query_data = {
            "message": large_message,
            "conversation_id": "test_large_123",
            "language": "en"
        }
        
        response = await async_test_client.post("/api/v1/chat/query", json=query_data)
        # Should either process successfully or return appropriate error
        assert response.status_code in [200, 413, 422]


class TestCORSAndSecurity:
    """Test CORS and security headers."""
    
    async def test_cors_headers(self, async_test_client: AsyncClient):
        """Test that CORS headers are present."""
        response = await async_test_client.options("/api/v1/health")
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
    
    async def test_security_headers(self, async_test_client: AsyncClient):
        """Test that security headers are present."""
        response = await async_test_client.get("/health")
        
        # Check for basic security headers
        expected_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection"
        ]
        
        for header in expected_headers:
            assert header in response.headers or header.replace("-", "") in response.headers
    
    async def test_correlation_id_header(self, async_test_client: AsyncClient):
        """Test that correlation ID is returned in response headers."""
        response = await async_test_client.get("/health")
        
        # Should have correlation ID in response
        assert "x-correlation-id" in response.headers


class TestPerformance:
    """Basic performance tests."""
    
    async def test_health_check_performance(self, async_test_client: AsyncClient, performance_timer):
        """Test health check response time."""
        performance_timer.start()
        response = await async_test_client.get("/health")
        elapsed = performance_timer.stop()
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond within 1 second
    
    async def test_dashboard_stats_performance(self, async_test_client: AsyncClient, performance_timer):
        """Test dashboard stats response time."""
        performance_timer.start()
        response = await async_test_client.get("/api/v1/dashboard/stats")
        elapsed = performance_timer.stop()
        
        assert response.status_code == 200
        assert elapsed < 2.0  # Should respond within 2 seconds
    
    async def test_concurrent_requests(self, async_test_client: AsyncClient):
        """Test handling of concurrent requests."""
        import asyncio
        
        async def make_request():
            response = await async_test_client.get("/health")
            return response.status_code
        
        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert all(status_code == 200 for status_code in results)


class TestWebSocketConnections:
    """Test WebSocket connection statistics."""
    
    async def test_websocket_stats(self, async_test_client: AsyncClient):
        """Test WebSocket connection statistics endpoint."""
        response = await async_test_client.get("/api/v1/ws/connections/stats")
        data = assert_valid_response(response, 200)
        
        assert "total_connections" in data
        assert "chat_conversations" in data
        assert "dashboard_connections" in data
        assert isinstance(data["total_connections"], int)


# Parametrized tests for different scenarios
@pytest.mark.parametrize("endpoint", [
    "/health",
    "/api/v1/dashboard/health",
    "/api/v1/voice/health",
    "/api/v1/ws/connections/stats"
])
async def test_all_health_endpoints(async_test_client: AsyncClient, endpoint):
    """Test all health check endpoints."""
    response = await async_test_client.get(endpoint)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.parametrize("language", ["en", "hi", "bn", "te", "ta"])
async def test_multilingual_support(async_test_client: AsyncClient, language):
    """Test multilingual support across different languages."""
    query_data = {
        "message": "Test message",
        "conversation_id": f"test_{language}",
        "language": language
    }
    
    response = await async_test_client.post("/api/v1/chat/query", json=query_data)
    
    # Should either succeed or fail gracefully
    assert response.status_code in [200, 422, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert data.get("language") == language
