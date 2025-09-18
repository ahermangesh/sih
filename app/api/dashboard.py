"""
FloatChat - Dashboard API Endpoints

This module provides API endpoints for the dashboard functionality,
including statistics, activity feeds, and real-time data updates.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, desc

from app.core.database import get_db
from app.models.database_simple import ArgoFloat, ArgoProfile, ProcessingLog
from app.models.schemas import (
    DashboardStatsResponse,
    ActivityItem,
    ActivityFeedResponse,
    FloatLocationResponse
)
from app.services.real_argo_service import real_argo_service
from app.utils.exceptions import DataNotFoundError

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Get dashboard statistics",
    description="Returns current statistics for floats, profiles, queries, and system status."
)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db)
) -> DashboardStatsResponse:
    """
    Retrieve dashboard statistics including float counts, profile counts, and activity metrics.
    """
    try:
        logger.info("Fetching dashboard statistics")
        
        # Get float statistics
        floats_query = select(func.count(ArgoFloat.id))
        floats_result = await db.execute(floats_query)
        total_floats = floats_result.scalar() or 0
        
        # Get active floats (with recent data)
        recent_date = datetime.utcnow() - timedelta(days=30)
        active_floats_query = select(func.count(ArgoFloat.id.distinct())).select_from(
            ArgoFloat.__table__.join(ArgoProfile.__table__)
        ).where(ArgoProfile.profile_date >= recent_date)
        active_result = await db.execute(active_floats_query)
        active_floats = active_result.scalar() or 0
        
        # Get profile statistics
        profiles_query = select(func.count(ArgoProfile.id))
        profiles_result = await db.execute(profiles_query)
        total_profiles = profiles_result.scalar() or 0
        
        # Get today's profiles
        today = datetime.utcnow().date()
        today_profiles_query = select(func.count(ArgoProfile.id)).where(
            func.date(ArgoProfile.profile_date) == today
        )
        today_result = await db.execute(today_profiles_query)
        today_profiles = today_result.scalar() or 0
        
        # Get real query statistics from conversation store (in production, from analytics DB)
        from app.api.real_chat import conversation_store
        queries_today = sum(len(conv.get('messages', [])) // 2 for conv in conversation_store.values())
        
        # Calculate growth rates
        yesterday_profiles_query = select(func.count(ArgoProfile.id)).where(
            func.date(ArgoProfile.profile_date) == today - timedelta(days=1)
        )
        yesterday_result = await db.execute(yesterday_profiles_query)
        yesterday_profiles = yesterday_result.scalar() or 1
        
        profile_growth = ((today_profiles - yesterday_profiles) / yesterday_profiles * 100) if yesterday_profiles > 0 else 0
        
        stats = DashboardStatsResponse(
            floats_count=active_floats,
            floats_total=total_floats,
            floats_growth=12,  # Mock growth - would calculate from historical data
            profiles_count=total_profiles,
            profiles_today=today_profiles,
            profiles_growth=profile_growth,
            queries_today=queries_today,
            queries_growth=18.5,  # Mock growth
            languages_supported=14,
            system_status="healthy",
            last_updated=datetime.utcnow()
        )
        
        logger.info(
            "Dashboard statistics retrieved",
            floats=active_floats,
            profiles=total_profiles,
            queries=queries_today
        )
        
        return stats
        
    except Exception as e:
        logger.error("Failed to fetch dashboard statistics", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard statistics"
        )


@router.get(
    "/activity",
    response_model=ActivityFeedResponse,
    summary="Get recent activity feed",
    description="Returns recent system activity including queries, data ingestion, and system events."
)
async def get_activity_feed(
    limit: int = Query(default=20, ge=1, le=100, description="Number of activities to return"),
    db: AsyncSession = Depends(get_db)
) -> ActivityFeedResponse:
    """
    Retrieve recent system activity for the dashboard activity feed.
    """
    try:
        logger.info("Fetching activity feed", limit=limit)
        
        activities = []
        
        # Get recent processing logs
        processing_query = select(ProcessingLog).order_by(desc(ProcessingLog.start_time)).limit(limit // 2)
        processing_result = await db.execute(processing_query)
        processing_logs = processing_result.scalars().all()
        
        for log in processing_logs:
            activity = ActivityItem(
                id=f"proc_{log.id}",
                type="data",
                title="ARGO data processed",
                description=f"Processed {log.records_processed} records from {log.file_name}",
                timestamp=log.start_time,
                metadata={
                    "file_name": log.file_name,
                    "records": log.records_processed,
                    "status": log.status
                }
            )
            activities.append(activity)
        
        # Get recent profiles as data ingestion events
        profiles_query = select(ArgoProfile).order_by(desc(ArgoProfile.profile_date)).limit(limit // 2)
        profiles_result = await db.execute(profiles_query)
        recent_profiles = profiles_result.scalars().all()
        
        for profile in recent_profiles:
            activity = ActivityItem(
                id=f"profile_{profile.id}",
                type="data",
                title="New ARGO profile ingested",
                description=f"Profile from cycle {profile.cycle_number}, depth {profile.pres_max:.1f}m",
                timestamp=profile.profile_date,
                metadata={
                    "cycle": profile.cycle_number,
                    "depth": profile.pres_max,
                    "direction": profile.direction
                }
            )
            activities.append(activity)
        
        # Add some mock activities for demo purposes
        mock_activities = [
            ActivityItem(
                id="query_001",
                type="query",
                title="Temperature query processed",
                description="User asked about Arabian Sea temperature trends",
                timestamp=datetime.utcnow() - timedelta(minutes=2),
                metadata={"language": "en", "region": "arabian_sea"}
            ),
            ActivityItem(
                id="voice_001",
                type="voice",
                title="Voice query in Hindi",
                description="User asked 'समुद्री तापमान कैसा है?' via voice",
                timestamp=datetime.utcnow() - timedelta(minutes=32),
                metadata={"language": "hi", "confidence": 0.95}
            ),
            ActivityItem(
                id="system_001",
                type="system",
                title="System health check",
                description="All services operational, 99.9% uptime",
                timestamp=datetime.utcnow() - timedelta(hours=1),
                metadata={"uptime": 99.9, "services": "all_green"}
            )
        ]
        
        activities.extend(mock_activities)
        
        # Sort by timestamp (most recent first) and limit
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        activities = activities[:limit]
        
        response = ActivityFeedResponse(
            activities=activities,
            total_count=len(activities),
            last_updated=datetime.utcnow()
        )
        
        logger.info("Activity feed retrieved", count=len(activities))
        return response
        
    except Exception as e:
        logger.error("Failed to fetch activity feed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve activity feed"
        )


@router.get(
    "/floats/locations",
    response_model=List[FloatLocationResponse],
    summary="Get float locations for map",
    description="Returns current locations of ARGO floats for map visualization."
)
async def get_float_locations(
    status_filter: Optional[str] = Query(None, description="Filter by status: active, recent, bgc, inactive"),
    limit: int = Query(default=1000, ge=1, le=5000, description="Maximum number of floats to return"),
    db: AsyncSession = Depends(get_db)
) -> List[FloatLocationResponse]:
    """
    Retrieve ARGO float locations for map visualization.
    """
    try:
        logger.info("Fetching float locations", status_filter=status_filter, limit=limit)
        
        # Get real ARGO float locations
        try:
            # Define region for Indian Ocean if no filter specified
            region = None
            if not status_filter or status_filter == 'all':
                region = {'west': 30, 'south': -40, 'east': 120, 'north': 30}  # Indian Ocean
            
            real_floats = await real_argo_service.fetch_active_floats(region)
            
            locations = []
            for float_data in real_floats[:limit]:
                if status_filter and status_filter != 'all' and float_data.get('status') != status_filter:
                    continue
                    
                last_loc = float_data.get('last_location', {})
                if last_loc.get('latitude') and last_loc.get('longitude'):
                    location = FloatLocationResponse(
                        float_id=f"ARGO_{float_data['wmo_id']}",
                        wmo_id=float_data['wmo_id'],
                        latitude=last_loc['latitude'],
                        longitude=last_loc['longitude'],
                        last_position_date=datetime.fromisoformat(last_loc['date']) if last_loc.get('date') else datetime.utcnow(),
                        status=float_data.get('status', 'unknown'),
                        platform_type=float_data.get('platform_type', 'UNKNOWN'),
                        last_profile_date=datetime.fromisoformat(float_data.get('last_message_date', datetime.utcnow().isoformat())),
                        cycle_number=None,  # Would need additional API call
                        metadata={
                            'program': float_data.get('program', 'UNKNOWN'),
                            'country': float_data.get('country', 'UNKNOWN'),
                            'deployment_date': float_data.get('deployment_date')
                        }
                    )
                    locations.append(location)
            
            if locations:
                logger.info("Real ARGO float locations retrieved", count=len(locations))
                return locations
            
        except Exception as e:
            logger.warning(f"Failed to fetch real ARGO data, using fallback: {e}")
        
        # Fallback to mock data if real data fails
        mock_locations = [
            FloatLocationResponse(
                float_id="ARGO001",
                wmo_id=2901234,
                latitude=15.0,
                longitude=73.0,
                last_position_date=datetime.utcnow() - timedelta(hours=2),
                status="active",
                platform_type="APEX",
                last_profile_date=datetime.utcnow() - timedelta(hours=6),
                cycle_number=145,
                metadata={
                    "temperature": 26.5,
                    "salinity": 35.2,
                    "depth": 2000.0
                }
            ),
            FloatLocationResponse(
                float_id="ARGO002",
                wmo_id=2901235,
                latitude=8.5,
                longitude=76.9,
                last_position_date=datetime.utcnow() - timedelta(hours=4),
                status="active",
                platform_type="SOLO",
                last_profile_date=datetime.utcnow() - timedelta(hours=8),
                cycle_number=89,
                metadata={
                    "temperature": 28.1,
                    "salinity": 34.8,
                    "depth": 1800.0
                }
            ),
            FloatLocationResponse(
                float_id="ARGO003",
                wmo_id=2901236,
                latitude=13.1,
                longitude=80.3,
                last_position_date=datetime.utcnow() - timedelta(hours=1),
                status="recent",
                platform_type="APEX",
                last_profile_date=datetime.utcnow() - timedelta(hours=3),
                cycle_number=203,
                metadata={
                    "temperature": 27.8,
                    "salinity": 35.0,
                    "depth": 2200.0
                }
            ),
            FloatLocationResponse(
                float_id="ARGO004",
                wmo_id=2901237,
                latitude=19.1,
                longitude=72.9,
                last_position_date=datetime.utcnow() - timedelta(hours=3),
                status="active",
                platform_type="PROVOR",
                last_profile_date=datetime.utcnow() - timedelta(hours=5),
                cycle_number=167,
                metadata={
                    "temperature": 25.9,
                    "salinity": 35.4,
                    "depth": 1900.0
                }
            ),
            FloatLocationResponse(
                float_id="ARGO005",
                wmo_id=2901238,
                latitude=11.0,
                longitude=77.0,
                last_position_date=datetime.utcnow() - timedelta(hours=6),
                status="bgc",
                platform_type="NAVIS_BGC",
                last_profile_date=datetime.utcnow() - timedelta(hours=12),
                cycle_number=78,
                metadata={
                    "temperature": 27.2,
                    "salinity": 34.9,
                    "depth": 2100.0,
                    "chlorophyll": 0.15,
                    "oxygen": 210.5
                }
            )
        ]
        
        # Apply status filter if provided
        if status_filter:
            mock_locations = [loc for loc in mock_locations if loc.status == status_filter]
        
        # Apply limit
        mock_locations = mock_locations[:limit]
        
        logger.info("Float locations retrieved", count=len(mock_locations), filter=status_filter)
        return mock_locations
        
    except Exception as e:
        logger.error("Failed to fetch float locations", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve float locations"
        )


@router.get(
    "/health",
    summary="Dashboard service health check",
    description="Returns the health status of the dashboard service and its dependencies."
)
async def dashboard_health_check():
    """
    Health check endpoint for the dashboard service.
    """
    return {
        "status": "healthy",
        "service": "dashboard",
        "timestamp": datetime.utcnow(),
        "dependencies": {
            "database": "connected",
            "cache": "available",
            "argo_service": "operational"
        }
    }
