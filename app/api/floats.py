"""
FloatChat - ARGO Float Data API

RESTful API endpoints for accessing ARGO float data including floats, profiles,
and measurements with comprehensive filtering and search capabilities.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
import structlog

from app.core.database import get_async_db
from app.models.database import ArgoFloat, ArgoProfile, ArgoMeasurement, DataQuality
from app.models.schemas import (
    FloatResponse, FloatListResponse, ProfileResponse, ProfileListResponse,
    MeasurementResponse, MeasurementListResponse, FloatSearchQuery,
    ProfileSearchQuery, DataQualityResponse
)
from app.services.argo_service import ArgoDataService
from app.utils.exceptions import DataNotFoundError, ValidationError

logger = structlog.get_logger(__name__)
router = APIRouter()


# =============================================================================
# FLOAT ENDPOINTS
# =============================================================================

@router.get("/", response_model=FloatListResponse)
async def list_floats(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    status: Optional[str] = Query(None, description="Filter by float status"),
    data_center: Optional[str] = Query(None, description="Filter by data center"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    db: AsyncSession = Depends(get_async_db)
) -> FloatListResponse:
    """
    Get list of ARGO floats with optional filtering.
    
    Returns paginated list of floats with basic metadata.
    """
    try:
        logger.info(
            "Listing ARGO floats",
            skip=skip,
            limit=limit,
            status=status,
            data_center=data_center,
            project_name=project_name
        )
        
        # Build query with filters
        query = select(ArgoFloat)
        
        if status:
            query = query.where(ArgoFloat.status == status)
        if data_center:
            query = query.where(ArgoFloat.data_center.ilike(f"%{data_center}%"))
        if project_name:
            query = query.where(ArgoFloat.project_name.ilike(f"%{project_name}%"))
        
        # Add pagination
        query = query.offset(skip).limit(limit).order_by(ArgoFloat.wmo_id)
        
        # Execute query
        result = await db.execute(query)
        floats = result.scalars().all()
        
        # Get total count for pagination
        count_query = select(func.count(ArgoFloat.id))
        if status:
            count_query = count_query.where(ArgoFloat.status == status)
        if data_center:
            count_query = count_query.where(ArgoFloat.data_center.ilike(f"%{data_center}%"))
        if project_name:
            count_query = count_query.where(ArgoFloat.project_name.ilike(f"%{project_name}%"))
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        logger.info(
            "ARGO floats retrieved",
            count=len(floats),
            total_count=total_count
        )
        
        return FloatListResponse(
            floats=[FloatResponse.from_orm(float_obj) for float_obj in floats],
            total_count=total_count,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.error("Failed to list ARGO floats", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ARGO floats"
        )


@router.get("/{wmo_id}", response_model=FloatResponse)
async def get_float(
    wmo_id: str = Path(..., description="WMO ID of the float"),
    db: AsyncSession = Depends(get_async_db)
) -> FloatResponse:
    """
    Get detailed information about a specific ARGO float.
    
    Returns complete float metadata and summary statistics.
    """
    try:
        logger.info("Retrieving ARGO float", wmo_id=wmo_id)
        
        # Query float with profile count
        query = (
            select(ArgoFloat)
            .options(selectinload(ArgoFloat.profiles))
            .where(ArgoFloat.wmo_id == wmo_id)
        )
        
        result = await db.execute(query)
        float_obj = result.scalar_one_or_none()
        
        if not float_obj:
            raise DataNotFoundError(
                message=f"ARGO float not found: {wmo_id}",
                resource_type="float",
                resource_id=wmo_id
            )
        
        logger.info(
            "ARGO float retrieved",
            wmo_id=wmo_id,
            profiles_count=len(float_obj.profiles)
        )
        
        return FloatResponse.from_orm(float_obj)
        
    except DataNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ARGO float not found: {wmo_id}"
        )
    except Exception as e:
        logger.error("Failed to get ARGO float", wmo_id=wmo_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ARGO float"
        )


@router.post("/search", response_model=FloatListResponse)
async def search_floats(
    search_query: FloatSearchQuery,
    db: AsyncSession = Depends(get_async_db)
) -> FloatListResponse:
    """
    Search ARGO floats with advanced filtering options.
    
    Supports spatial, temporal, and metadata-based filtering.
    """
    try:
        logger.info("Searching ARGO floats", search_criteria=search_query.dict())
        
        # Build complex query
        query = select(ArgoFloat)
        
        # Spatial filtering
        if search_query.bbox:
            west, south, east, north = search_query.bbox
            query = query.where(
                and_(
                    ArgoFloat.deployment_latitude >= south,
                    ArgoFloat.deployment_latitude <= north,
                    ArgoFloat.deployment_longitude >= west,
                    ArgoFloat.deployment_longitude <= east
                )
            )
        
        # Temporal filtering
        if search_query.deployment_date_start:
            query = query.where(ArgoFloat.deployment_date >= search_query.deployment_date_start)
        if search_query.deployment_date_end:
            query = query.where(ArgoFloat.deployment_date <= search_query.deployment_date_end)
        
        # Status filtering
        if search_query.status:
            query = query.where(ArgoFloat.status.in_(search_query.status))
        
        # Metadata filtering
        if search_query.float_types:
            query = query.where(ArgoFloat.float_type.in_(search_query.float_types))
        if search_query.data_centers:
            query = query.where(ArgoFloat.data_center.in_(search_query.data_centers))
        if search_query.project_names:
            query = query.where(ArgoFloat.project_name.in_(search_query.project_names))
        
        # Quality filtering
        if search_query.min_profiles:
            query = query.where(ArgoFloat.total_profiles >= search_query.min_profiles)
        
        # Add pagination and ordering
        query = query.offset(search_query.skip).limit(search_query.limit)
        query = query.order_by(ArgoFloat.wmo_id)
        
        # Execute search
        result = await db.execute(query)
        floats = result.scalars().all()
        
        logger.info(
            "ARGO float search completed",
            results_count=len(floats),
            search_criteria=search_query.dict()
        )
        
        return FloatListResponse(
            floats=[FloatResponse.from_orm(float_obj) for float_obj in floats],
            total_count=len(floats),  # TODO: Implement proper count query
            skip=search_query.skip,
            limit=search_query.limit
        )
        
    except Exception as e:
        logger.error("ARGO float search failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Float search failed"
        )


# =============================================================================
# PROFILE ENDPOINTS
# =============================================================================

@router.get("/{wmo_id}/profiles", response_model=ProfileListResponse)
async def get_float_profiles(
    wmo_id: str = Path(..., description="WMO ID of the float"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    date_start: Optional[date] = Query(None, description="Start date filter"),
    date_end: Optional[date] = Query(None, description="End date filter"),
    data_mode: Optional[str] = Query(None, description="Data mode filter (R/A/D)"),
    db: AsyncSession = Depends(get_async_db)
) -> ProfileListResponse:
    """
    Get profiles for a specific ARGO float.
    
    Returns paginated list of profiles with optional date filtering.
    """
    try:
        logger.info(
            "Retrieving float profiles",
            wmo_id=wmo_id,
            skip=skip,
            limit=limit,
            date_start=date_start,
            date_end=date_end
        )
        
        # Verify float exists
        float_query = select(ArgoFloat).where(ArgoFloat.wmo_id == wmo_id)
        float_result = await db.execute(float_query)
        float_obj = float_result.scalar_one_or_none()
        
        if not float_obj:
            raise DataNotFoundError(
                message=f"ARGO float not found: {wmo_id}",
                resource_type="float",
                resource_id=wmo_id
            )
        
        # Build profiles query
        query = (
            select(ArgoProfile)
            .where(ArgoProfile.float_id == float_obj.id)
        )
        
        # Apply filters
        if date_start:
            query = query.where(ArgoProfile.profile_date >= date_start)
        if date_end:
            query = query.where(ArgoProfile.profile_date <= date_end)
        if data_mode:
            query = query.where(ArgoProfile.data_mode == data_mode)
        
        # Add pagination and ordering
        query = query.offset(skip).limit(limit).order_by(ArgoProfile.profile_date.desc())
        
        # Execute query
        result = await db.execute(query)
        profiles = result.scalars().all()
        
        logger.info(
            "Float profiles retrieved",
            wmo_id=wmo_id,
            profiles_count=len(profiles)
        )
        
        return ProfileListResponse(
            profiles=[ProfileResponse.from_orm(profile) for profile in profiles],
            total_count=len(profiles),  # TODO: Implement proper count
            skip=skip,
            limit=limit,
            float_wmo_id=wmo_id
        )
        
    except DataNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ARGO float not found: {wmo_id}"
        )
    except Exception as e:
        logger.error(
            "Failed to get float profiles",
            wmo_id=wmo_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profiles"
        )


@router.get("/{wmo_id}/profiles/{cycle_number}", response_model=ProfileResponse)
async def get_profile(
    wmo_id: str = Path(..., description="WMO ID of the float"),
    cycle_number: int = Path(..., description="Profile cycle number"),
    db: AsyncSession = Depends(get_async_db)
) -> ProfileResponse:
    """
    Get detailed information about a specific profile.
    
    Returns complete profile metadata and measurement summary.
    """
    try:
        logger.info(
            "Retrieving profile",
            wmo_id=wmo_id,
            cycle_number=cycle_number
        )
        
        # Query profile with float and measurements
        query = (
            select(ArgoProfile)
            .options(
                selectinload(ArgoProfile.float),
                selectinload(ArgoProfile.measurements)
            )
            .join(ArgoFloat)
            .where(
                and_(
                    ArgoFloat.wmo_id == wmo_id,
                    ArgoProfile.cycle_number == cycle_number
                )
            )
        )
        
        result = await db.execute(query)
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise DataNotFoundError(
                message=f"Profile not found: {wmo_id} cycle {cycle_number}",
                resource_type="profile",
                resource_id=f"{wmo_id}/{cycle_number}"
            )
        
        logger.info(
            "Profile retrieved",
            wmo_id=wmo_id,
            cycle_number=cycle_number,
            measurements_count=len(profile.measurements)
        )
        
        return ProfileResponse.from_orm(profile)
        
    except DataNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found: {wmo_id} cycle {cycle_number}"
        )
    except Exception as e:
        logger.error(
            "Failed to get profile",
            wmo_id=wmo_id,
            cycle_number=cycle_number,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        )


# =============================================================================
# MEASUREMENT ENDPOINTS
# =============================================================================

@router.get("/{wmo_id}/profiles/{cycle_number}/measurements", response_model=MeasurementListResponse)
async def get_profile_measurements(
    wmo_id: str = Path(..., description="WMO ID of the float"),
    cycle_number: int = Path(..., description="Profile cycle number"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(1000, ge=1, le=5000, description="Number of records to return"),
    min_pressure: Optional[float] = Query(None, description="Minimum pressure filter"),
    max_pressure: Optional[float] = Query(None, description="Maximum pressure filter"),
    parameters: Optional[List[str]] = Query(None, description="Parameters to include"),
    db: AsyncSession = Depends(get_async_db)
) -> MeasurementListResponse:
    """
    Get measurements for a specific profile.
    
    Returns detailed measurement data with optional pressure filtering.
    """
    try:
        logger.info(
            "Retrieving profile measurements",
            wmo_id=wmo_id,
            cycle_number=cycle_number,
            min_pressure=min_pressure,
            max_pressure=max_pressure,
            parameters=parameters
        )
        
        # Find profile
        profile_query = (
            select(ArgoProfile)
            .join(ArgoFloat)
            .where(
                and_(
                    ArgoFloat.wmo_id == wmo_id,
                    ArgoProfile.cycle_number == cycle_number
                )
            )
        )
        
        profile_result = await db.execute(profile_query)
        profile = profile_result.scalar_one_or_none()
        
        if not profile:
            raise DataNotFoundError(
                message=f"Profile not found: {wmo_id} cycle {cycle_number}",
                resource_type="profile",
                resource_id=f"{wmo_id}/{cycle_number}"
            )
        
        # Build measurements query
        query = (
            select(ArgoMeasurement)
            .where(ArgoMeasurement.profile_id == profile.id)
        )
        
        # Apply pressure filters
        if min_pressure is not None:
            query = query.where(ArgoMeasurement.pressure >= min_pressure)
        if max_pressure is not None:
            query = query.where(ArgoMeasurement.pressure <= max_pressure)
        
        # Add pagination and ordering
        query = query.offset(skip).limit(limit).order_by(ArgoMeasurement.pressure)
        
        # Execute query
        result = await db.execute(query)
        measurements = result.scalars().all()
        
        logger.info(
            "Profile measurements retrieved",
            wmo_id=wmo_id,
            cycle_number=cycle_number,
            measurements_count=len(measurements)
        )
        
        return MeasurementListResponse(
            measurements=[MeasurementResponse.from_orm(m) for m in measurements],
            total_count=len(measurements),  # TODO: Implement proper count
            skip=skip,
            limit=limit,
            float_wmo_id=wmo_id,
            cycle_number=cycle_number
        )
        
    except DataNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found: {wmo_id} cycle {cycle_number}"
        )
    except Exception as e:
        logger.error(
            "Failed to get profile measurements",
            wmo_id=wmo_id,
            cycle_number=cycle_number,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve measurements"
        )


# =============================================================================
# DATA QUALITY ENDPOINTS
# =============================================================================

@router.get("/{wmo_id}/profiles/{cycle_number}/quality", response_model=DataQualityResponse)
async def get_profile_quality(
    wmo_id: str = Path(..., description="WMO ID of the float"),
    cycle_number: int = Path(..., description="Profile cycle number"),
    db: AsyncSession = Depends(get_async_db)
) -> DataQualityResponse:
    """
    Get data quality assessment for a specific profile.
    
    Returns quality scores, validation results, and anomaly detection.
    """
    try:
        logger.info(
            "Retrieving profile quality",
            wmo_id=wmo_id,
            cycle_number=cycle_number
        )
        
        # Find profile with quality records
        query = (
            select(ArgoProfile)
            .options(selectinload(ArgoProfile.quality_records))
            .join(ArgoFloat)
            .where(
                and_(
                    ArgoFloat.wmo_id == wmo_id,
                    ArgoProfile.cycle_number == cycle_number
                )
            )
        )
        
        result = await db.execute(query)
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise DataNotFoundError(
                message=f"Profile not found: {wmo_id} cycle {cycle_number}",
                resource_type="profile",
                resource_id=f"{wmo_id}/{cycle_number}"
            )
        
        # Get latest quality record
        quality_record = None
        if profile.quality_records:
            quality_record = max(profile.quality_records, key=lambda q: q.assessment_date)
        
        if not quality_record:
            # Generate quality assessment on demand
            argo_service = ArgoDataService()
            # This would trigger quality assessment
            # For now, return basic response
            return DataQualityResponse(
                float_wmo_id=wmo_id,
                cycle_number=cycle_number,
                overall_quality_score=0.0,
                quality_message="Quality assessment not available"
            )
        
        logger.info(
            "Profile quality retrieved",
            wmo_id=wmo_id,
            cycle_number=cycle_number,
            quality_score=quality_record.overall_quality_score
        )
        
        return DataQualityResponse.from_orm(quality_record)
        
    except DataNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found: {wmo_id} cycle {cycle_number}"
        )
    except Exception as e:
        logger.error(
            "Failed to get profile quality",
            wmo_id=wmo_id,
            cycle_number=cycle_number,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quality information"
        )
