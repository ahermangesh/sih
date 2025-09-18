"""
FloatChat - Test Configuration

Pytest configuration and fixtures for comprehensive testing.
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.core.database import get_db, Base
from app.core.config import get_settings
from app.models.database_simple import ArgoFloat, ArgoProfile, ArgoMeasurement, ProcessingLog


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def override_get_db(test_db_session):
    """Override the get_db dependency for testing."""
    async def _override_get_db():
        yield test_db_session
    
    return _override_get_db


@pytest.fixture
def test_app(override_get_db):
    """Create test FastAPI application."""
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def test_client(test_app) -> TestClient:
    """Create test client for synchronous testing."""
    return TestClient(test_app)


@pytest_asyncio.fixture
async def async_test_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for async testing."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def sample_float_data(test_db_session: AsyncSession):
    """Create sample ARGO float data for testing."""
    # Create sample float
    float_data = ArgoFloat(
        wmo_id=2901234,
        platform_type="APEX",
        deployment_date="2020-01-01T00:00:00",
        status="active",
        cycle_number_max=150,
        data_center="INCOIS",
        project_name="Indian Ocean",
        pi_name="Dr. Test Scientist",
        platform_owner="INCOIS",
        dac_format_id="3901234",
        deep_argos=False,
        bgc_argos=False
    )
    
    test_db_session.add(float_data)
    await test_db_session.commit()
    await test_db_session.refresh(float_data)
    
    # Create sample profiles
    profile_data = ArgoProfile(
        float_id=float_data.id,
        cycle_number=1,
        profile_date="2020-01-02T12:00:00",
        direction="A",
        pres_max=2000.0,
        temp_max=28.5,
        psal_max=35.2
    )
    
    test_db_session.add(profile_data)
    await test_db_session.commit()
    await test_db_session.refresh(profile_data)
    
    # Create sample measurements
    measurements = [
        ArgoMeasurement(
            profile_id=profile_data.id,
            pressure=10.0,
            temperature=28.5,
            salinity=35.2
        ),
        ArgoMeasurement(
            profile_id=profile_data.id,
            pressure=100.0,
            temperature=25.8,
            salinity=35.1
        ),
        ArgoMeasurement(
            profile_id=profile_data.id,
            pressure=500.0,
            temperature=15.2,
            salinity=34.8
        )
    ]
    
    for measurement in measurements:
        test_db_session.add(measurement)
    
    await test_db_session.commit()
    
    return {
        "float": float_data,
        "profile": profile_data,
        "measurements": measurements
    }


@pytest.fixture
def mock_gemini_service():
    """Mock Gemini AI service for testing."""
    mock_service = AsyncMock()
    mock_service.generate_response.return_value = {
        "message": "This is a mock AI response for testing.",
        "confidence": 0.95,
        "processing_time": 1.2,
        "metadata": {"model": "gemini-pro", "tokens_used": 150}
    }
    return mock_service


@pytest.fixture
def mock_voice_service():
    """Mock voice processing service for testing."""
    mock_service = MagicMock()
    mock_service.transcribe.return_value = ("This is a mock transcription.", 0.92)
    mock_service.synthesize.return_value = b"mock_audio_data"
    mock_service.audio_dependencies_available = True
    return mock_service


@pytest.fixture
def mock_translation_service():
    """Mock translation service for testing."""
    mock_service = AsyncMock()
    mock_service.detect_language.return_value = {
        "detected_language": "en",
        "confidence": 0.95,
        "supported": True
    }
    mock_service.translate.return_value = "This is a mock translation."
    return mock_service


@pytest.fixture
def sample_chat_message():
    """Sample chat message for testing."""
    return {
        "message": "Show me temperature data from the Arabian Sea",
        "conversation_id": "test_conversation_123",
        "language": "en",
        "include_visualization": True,
        "voice_input": False
    }


@pytest.fixture
def sample_voice_message():
    """Sample voice message for testing."""
    return {
        "audio_base64": "dGVzdF9hdWRpb19kYXRh",  # base64 encoded "test_audio_data"
        "language": "en",
        "engine": "google"
    }


@pytest.fixture
def sample_float_query():
    """Sample float query for testing."""
    return {
        "bbox": [68.0, 6.0, 97.0, 37.0],  # Indian Ocean bounding box
        "date_range": {
            "start": "2020-01-01",
            "end": "2020-12-31"
        },
        "parameters": ["temperature", "salinity"],
        "depth_range": {
            "min": 0,
            "max": 2000
        }
    }


@pytest.fixture
def websocket_test_client(test_app):
    """Create WebSocket test client."""
    return TestClient(test_app)


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.messages_received = []
        self.closed = False
    
    async def accept(self):
        """Mock accept method."""
        pass
    
    async def send_text(self, message: str):
        """Mock send_text method."""
        self.messages_sent.append(message)
    
    async def receive_text(self) -> str:
        """Mock receive_text method."""
        if self.messages_received:
            return self.messages_received.pop(0)
        raise Exception("No messages to receive")
    
    def add_message(self, message: str):
        """Add message to received queue."""
        self.messages_received.append(message)
    
    def close(self):
        """Mock close method."""
        self.closed = True


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket for testing."""
    return MockWebSocket()


@pytest.fixture
def test_settings():
    """Get test settings."""
    settings = get_settings()
    settings.environment = "testing"
    settings.database_url = TEST_DATABASE_URL
    return settings


# Utility functions for testing
def assert_valid_response(response, expected_status: int = 200):
    """Assert that response is valid with expected status."""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.text}"
    
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.text


def assert_valid_float_data(float_data: dict):
    """Assert that float data structure is valid."""
    required_fields = ["id", "wmo_id", "platform_type", "status"]
    for field in required_fields:
        assert field in float_data, f"Missing required field: {field}"
    
    assert isinstance(float_data["wmo_id"], int)
    assert float_data["status"] in ["active", "inactive", "recent"]


def assert_valid_profile_data(profile_data: dict):
    """Assert that profile data structure is valid."""
    required_fields = ["id", "cycle_number", "profile_date", "direction"]
    for field in required_fields:
        assert field in profile_data, f"Missing required field: {field}"
    
    assert isinstance(profile_data["cycle_number"], int)
    assert profile_data["direction"] in ["A", "D"]


def assert_valid_chat_response(response: dict):
    """Assert that chat response structure is valid."""
    required_fields = ["message", "timestamp"]
    for field in required_fields:
        assert field in response, f"Missing required field: {field}"
    
    assert isinstance(response["message"], str)
    assert len(response["message"]) > 0


def assert_valid_dashboard_stats(stats: dict):
    """Assert that dashboard statistics structure is valid."""
    required_fields = [
        "floats_count", "profiles_count", "queries_today", 
        "system_status", "last_updated"
    ]
    for field in required_fields:
        assert field in stats, f"Missing required field: {field}"
    
    assert isinstance(stats["floats_count"], int)
    assert isinstance(stats["profiles_count"], int)
    assert stats["system_status"] in ["healthy", "warning", "error"]


# Async test utilities
async def create_test_data(session: AsyncSession, count: int = 5):
    """Create test data for performance testing."""
    floats = []
    for i in range(count):
        float_data = ArgoFloat(
            wmo_id=2901000 + i,
            platform_type="APEX",
            status="active",
            data_center="TEST",
            project_name="Test Project"
        )
        session.add(float_data)
        floats.append(float_data)
    
    await session.commit()
    return floats


# Performance testing utilities
@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            return self.elapsed()
        
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Parametrized test data
@pytest.fixture(params=["en", "hi", "bn", "te", "ta"])
def language_code(request):
    """Parametrized language codes for multilingual testing."""
    return request.param


@pytest.fixture(params=["temperature", "salinity", "pressure"])
def measurement_parameter(request):
    """Parametrized measurement parameters for testing."""
    return request.param


@pytest.fixture(params=["APEX", "SOLO", "PROVOR", "NAVIS_BGC"])
def platform_type(request):
    """Parametrized platform types for testing."""
    return request.param
