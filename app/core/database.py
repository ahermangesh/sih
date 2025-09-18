"""
FloatChat - Database Connection and Session Management

Handles PostgreSQL connections with PostGIS support, connection pooling,
and async/sync session management.
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional, Any
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, MetaData, event, text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import text
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

# Database metadata and base model
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# Global engine and session maker instances
async_engine: Optional[AsyncEngine] = None
async_session_maker: Optional[async_sessionmaker] = None
sync_engine = None
sync_session_maker = None


def create_sync_engine():
    """Create synchronous database engine with connection pooling."""
    settings = get_settings()
    
    engine = create_engine(
        settings.database_url_sync,
        poolclass=QueuePool,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=3600,   # Recycle connections every hour
        echo=settings.debug and settings.is_development,  # Log SQL in development
    )
    
    # Add PostGIS extension check
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set up PostGIS extension on connection."""
        if 'postgresql' in str(engine.url):
            with dbapi_connection.cursor() as cursor:
                # Enable PostGIS extension if not exists
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
                dbapi_connection.commit()
    
    return engine


def create_async_database_engine():
    """Create asynchronous database engine with connection pooling."""
    settings = get_settings()
    
    # Convert to async URL if needed
    database_url = settings.database_url
    if not database_url.startswith('postgresql+asyncpg://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')
    
    engine = create_async_engine(
        database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.debug and settings.is_development,
    )
    
    return engine


async def init_database():
    """Initialize database connections and create tables."""
    global async_engine, async_session_maker, sync_engine, sync_session_maker
    
    try:
        logger.info("Initializing database connections")
        
        # Create async engine and session maker
        async_engine = create_async_database_engine()
        async_session_maker = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )
        
        # Create sync engine and session maker
        sync_engine = create_sync_engine()
        sync_session_maker = sessionmaker(
            bind=sync_engine,
            autoflush=True,
            autocommit=False
        )
        
        # Test async connection and enable PostGIS
        try:
            async with async_engine.begin() as conn:
                # Enable PostGIS extensions
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology;"))
                logger.info("PostGIS extensions enabled successfully")
        except Exception as e:
            logger.warning(f"PostGIS extensions not available: {e}")
            logger.info("Continuing without PostGIS - spatial features will be limited")
        
        # Test connection separately
        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value == 1:
                logger.info("Database connection established successfully")
            else:
                raise Exception("Database connection test failed")
        
        # Create tables
        await create_tables()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e), exc_info=True)
        raise


async def create_tables():
    """Create database tables if they don't exist."""
    try:
        logger.info("Creating database tables")
        
        # Import all models to ensure they're registered
        from app.models.database import (
            ArgoFloat, ArgoProfile, ArgoMeasurement, 
            DataQuality, ProcessingLog
        )
        
        async with async_engine.begin() as conn:
            # First create tables only (without indexes)
            try:
                await conn.run_sync(Base.metadata.create_all, checkfirst=True)
                logger.info("Database tables created successfully")
            except Exception as table_error:
                logger.warning(f"Table creation issue (continuing): {table_error}")
                
                # Try creating indexes manually with IF NOT EXISTS
                try:
                    await conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_argo_profiles_float_cycle ON argo_profiles (float_id, cycle_number);
                        CREATE INDEX IF NOT EXISTS idx_argo_profiles_date ON argo_profiles (profile_date);
                        CREATE INDEX IF NOT EXISTS idx_argo_profiles_location ON argo_profiles USING gist (location);
                        CREATE INDEX IF NOT EXISTS idx_argo_profiles_data_mode ON argo_profiles (data_mode);
                    """))
                    logger.info("Manual index creation completed")
                except Exception as index_error:
                    logger.warning(f"Manual index creation failed (continuing): {index_error}")
        
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e), exc_info=True)
        # Don't raise - let the server start anyway
        logger.warning("Continuing server startup despite database table creation issues")


async def close_database():
    """Close database connections."""
    global async_engine, sync_engine
    
    try:
        logger.info("Closing database connections")
        
        if async_engine:
            await async_engine.dispose()
            logger.info("Async database engine disposed")
        
        if sync_engine:
            sync_engine.dispose()
            logger.info("Sync database engine disposed")
            
        logger.info("Database connections closed successfully")
        
    except Exception as e:
        logger.error("Error closing database connections", error=str(e), exc_info=True)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session with automatic cleanup.
    
    Usage:
        async with get_async_session() as session:
            # Use session here
            result = await session.execute(select(ArgoFloat))
    
    Yields:
        AsyncSession: Database session
    """
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error", error=str(e), exc_info=True)
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """
    Get synchronous database session.
    
    Note: Remember to close the session after use.
    
    Returns:
        Session: Database session
    """
    if sync_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    return sync_session_maker()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting async database session.
    
    Usage:
        @app.get("/floats")
        async def get_floats(db: AsyncSession = Depends(get_async_db)):
            # Use db session here
    
    Yields:
        AsyncSession: Database session
    """
    async with get_async_session() as session:
        yield session


def get_sync_db() -> Session:
    """
    Get synchronous database session for FastAPI dependency.
    
    Returns:
        Session: Database session
    """
    session = get_sync_session()
    try:
        yield session
    finally:
        session.close()


# Alias for backward compatibility
get_db = get_async_db


async def check_database_health() -> dict[str, Any]:
    """
    Check database health and return status information.
    
    Returns:
        dict: Database health status
    """
    try:
        async with get_async_session() as session:
            # Test basic query
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            # Test PostGIS extension
            postgis_result = await session.execute(text("SELECT PostGIS_Version()"))
            postgis_version = postgis_result.scalar()
            
            # Get connection pool stats
            pool_stats = {
                "pool_size": async_engine.pool.size(),
                "checked_in": async_engine.pool.checkedin(),
                "checked_out": async_engine.pool.checkedout(),
                "overflow": async_engine.pool.overflow(),
                "invalid": async_engine.pool.invalid(),
            }
            
            return {
                "status": "healthy",
                "connection_test": test_value == 1,
                "postgis_version": postgis_version,
                "pool_stats": pool_stats,
                "engine_url": str(async_engine.url).replace(async_engine.url.password, "***"),
            }
            
    except Exception as e:
        logger.error("Database health check failed", error=str(e), exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "connection_test": False,
        }


async def execute_raw_query(query: str, params: dict = None) -> Any:
    """
    Execute raw SQL query with parameters.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        Query result
    """
    async with get_async_session() as session:
        result = await session.execute(text(query), params or {})
        return result


async def get_database_stats() -> dict[str, Any]:
    """
    Get database statistics and information.
    
    Returns:
        dict: Database statistics
    """
    try:
        stats = {}
        
        async with get_async_session() as session:
            # Get table row counts
            tables = ['argo_floats', 'argo_profiles', 'argo_measurements']
            for table in tables:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                stats[f"{table}_count"] = result.scalar()
            
            # Get database size
            result = await session.execute(text(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            ))
            stats["database_size"] = result.scalar()
            
            # Get recent activity
            result = await session.execute(text(
                "SELECT COUNT(*) FROM argo_profiles WHERE created_at > NOW() - INTERVAL '24 hours'"
            ))
            stats["profiles_last_24h"] = result.scalar()
            
        return stats
        
    except Exception as e:
        logger.error("Failed to get database stats", error=str(e), exc_info=True)
        return {"error": str(e)}


# Utility functions for database operations
async def bulk_insert_data(session: AsyncSession, model_class, data_list: list[dict]):
    """
    Bulk insert data for better performance.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        data_list: List of dictionaries with data to insert
    """
    try:
        objects = [model_class(**data) for data in data_list]
        session.add_all(objects)
        await session.flush()
        logger.info(f"Bulk inserted {len(objects)} {model_class.__name__} records")
        
    except Exception as e:
        logger.error(f"Bulk insert failed for {model_class.__name__}", error=str(e), exc_info=True)
        raise


async def truncate_table(session: AsyncSession, table_name: str):
    """
    Truncate table for testing or data cleanup.
    
    Args:
        session: Database session
        table_name: Name of table to truncate
    """
    try:
        await session.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))
        await session.commit()
        logger.warning(f"Table {table_name} truncated")
        
    except Exception as e:
        logger.error(f"Failed to truncate table {table_name}", error=str(e), exc_info=True)
        raise
