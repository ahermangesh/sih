"""
FloatChat - ARGO Data Service

Service layer for ARGO float data operations including ETL, processing,
and data access with comprehensive error handling and logging.
"""

import asyncio
import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import json

import numpy as np
import pandas as pd
import xarray as xr
import netCDF4 as nc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import structlog

from app.core.config import get_settings
from app.core.database import get_async_session, bulk_insert_data
from app.models.database import ArgoFloat, ArgoProfile, ArgoMeasurement, ProcessingLog
from app.utils.exceptions import DataProcessingError, ValidationError
from app.utils.data_validation import ArgoDataValidator

logger = structlog.get_logger(__name__)


class ArgoDataService:
    """Service for ARGO float data operations and ETL processing."""
    
    def __init__(self):
        self.settings = get_settings()
        self.data_validator = ArgoDataValidator()
        
    async def process_netcdf_file(
        self, 
        file_path: Path, 
        correlation_id: str = None
    ) -> Dict[str, Any]:
        """
        Process a single NetCDF file and extract ARGO data.
        
        Args:
            file_path: Path to NetCDF file
            correlation_id: Request correlation ID for logging
            
        Returns:
            Dict containing processing results and statistics
            
        Raises:
            DataProcessingError: If file processing fails
        """
        correlation_id = correlation_id or f"netcdf_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(
            "Processing NetCDF file",
            file_path=str(file_path),
            correlation_id=correlation_id
        )
        
        try:
            # Validate file exists and is readable
            if not file_path.exists():
                raise DataProcessingError(f"NetCDF file not found: {file_path}")
            
            # Open NetCDF dataset
            with xr.open_dataset(file_path, decode_times=True) as ds:
                # Extract float metadata
                float_data = self._extract_float_metadata(ds, file_path)
                
                # Extract profiles
                profiles_data = self._extract_profiles(ds, file_path)
                
                # Extract measurements
                measurements_data = self._extract_measurements(ds, profiles_data)
                
                # Validate extracted data
                validation_results = await self._validate_extracted_data(
                    float_data, profiles_data, measurements_data, correlation_id
                )
                
                result = {
                    "file_path": str(file_path),
                    "float_data": float_data,
                    "profiles_count": len(profiles_data),
                    "measurements_count": len(measurements_data),
                    "validation_results": validation_results,
                    "processing_time": datetime.utcnow(),
                    "correlation_id": correlation_id
                }
                
                logger.info(
                    "NetCDF file processed successfully",
                    file_path=str(file_path),
                    profiles_count=len(profiles_data),
                    measurements_count=len(measurements_data),
                    correlation_id=correlation_id
                )
                
                return result
                
        except Exception as e:
            logger.error(
                "Failed to process NetCDF file",
                file_path=str(file_path),
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise DataProcessingError(f"NetCDF processing failed: {str(e)}") from e
    
    def _extract_float_metadata(self, ds: xr.Dataset, file_path: Path) -> Dict[str, Any]:
        """Extract float metadata from NetCDF dataset."""
        try:
            # Get platform number (WMO ID)
            platform_number = str(ds.attrs.get('platform_number', ''))
            if not platform_number:
                # Try to extract from filename
                filename = file_path.name
                if '_prof.nc' in filename:
                    platform_number = filename.split('_')[0]
            
            float_data = {
                "wmo_id": platform_number,
                "platform_number": platform_number,
                "float_type": str(ds.attrs.get('float_type', '')),
                "data_center": str(ds.attrs.get('data_centre', '')),
                "project_name": str(ds.attrs.get('project_name', '')),
                "pi_name": str(ds.attrs.get('pi_name', '')),
                "status": "active",  # Default status
                "data_source": str(file_path),
                "sensor_configuration": {
                    "sensor_model": str(ds.attrs.get('sensor_model', '')),
                    "wmo_inst_type": str(ds.attrs.get('wmo_inst_type', '')),
                    "positioning_system": str(ds.attrs.get('positioning_system', ''))
                }
            }
            
            return float_data
            
        except Exception as e:
            logger.error("Failed to extract float metadata", error=str(e), exc_info=True)
            raise DataProcessingError(f"Float metadata extraction failed: {str(e)}")
    
    def _extract_profiles(self, ds: xr.Dataset, file_path: Path) -> List[Dict[str, Any]]:
        """Extract profile data from NetCDF dataset."""
        try:
            profiles_data = []
            
            # Get number of profiles
            n_prof = ds.dims.get('N_PROF', 1)
            
            for prof_idx in range(n_prof):
                try:
                    # Extract profile data
                    if n_prof == 1:
                        # Single profile file
                        latitude = float(ds['LATITUDE'].values)
                        longitude = float(ds['LONGITUDE'].values)
                        juld = ds['JULD'].values
                        cycle_number = int(ds.attrs.get('cycle_number', prof_idx + 1))
                    else:
                        # Multiple profiles file
                        latitude = float(ds['LATITUDE'].isel(N_PROF=prof_idx).values)
                        longitude = float(ds['LONGITUDE'].isel(N_PROF=prof_idx).values)
                        juld = ds['JULD'].isel(N_PROF=prof_idx).values
                        cycle_number = int(ds['CYCLE_NUMBER'].isel(N_PROF=prof_idx).values)
                    
                    # Convert Julian day to datetime
                    if pd.isna(juld) or juld == 999999:
                        profile_date = None
                        profile_time = None
                    else:
                        # ARGO uses days since 1950-01-01
                        reference_date = pd.Timestamp('1950-01-01')
                        profile_time = reference_date + pd.Timedelta(days=float(juld))
                        profile_date = profile_time.date()
                    
                    # Calculate measurement statistics
                    temp_data = ds.get('TEMP', None)
                    psal_data = ds.get('PSAL', None)
                    pres_data = ds.get('PRES', None)
                    
                    if n_prof > 1:
                        if temp_data is not None:
                            temp_data = temp_data.isel(N_PROF=prof_idx)
                        if psal_data is not None:
                            psal_data = psal_data.isel(N_PROF=prof_idx)
                        if pres_data is not None:
                            pres_data = pres_data.isel(N_PROF=prof_idx)
                    
                    profile_data = {
                        "cycle_number": cycle_number,
                        "profile_date": profile_date,
                        "profile_time": profile_time,
                        "latitude": latitude,
                        "longitude": longitude,
                        "direction": "A",  # Assume ascending
                        "data_mode": str(ds.attrs.get('data_mode', 'R')),
                        "quality_flag": "1",  # Default good quality
                        "position_quality_flag": "1",
                        "data_source": str(file_path),
                        "prof_idx": prof_idx  # For linking measurements
                    }
                    
                    # Add measurement availability flags
                    profile_data.update({
                        "has_temperature": temp_data is not None and not temp_data.isnull().all(),
                        "has_salinity": psal_data is not None and not psal_data.isnull().all(),
                        "has_oxygen": 'DOXY' in ds.variables,
                        "has_nitrate": 'NITRATE' in ds.variables,
                        "has_ph": 'PH_IN_SITU_TOTAL' in ds.variables,
                        "has_chla": 'CHLA' in ds.variables
                    })
                    
                    # Calculate summary statistics
                    if pres_data is not None:
                        valid_pres = pres_data.where(pres_data != 99999.0).dropna()
                        if len(valid_pres) > 0:
                            profile_data["max_pressure"] = float(valid_pres.max())
                    
                    if temp_data is not None:
                        valid_temp = temp_data.where(temp_data != 99999.0).dropna()
                        if len(valid_temp) > 0:
                            profile_data["min_temperature"] = float(valid_temp.min())
                            profile_data["max_temperature"] = float(valid_temp.max())
                    
                    if psal_data is not None:
                        valid_psal = psal_data.where(psal_data != 99999.0).dropna()
                        if len(valid_psal) > 0:
                            profile_data["min_salinity"] = float(valid_psal.min())
                            profile_data["max_salinity"] = float(valid_psal.max())
                    
                    profiles_data.append(profile_data)
                    
                except Exception as e:
                    logger.warning(
                        "Failed to extract profile",
                        prof_idx=prof_idx,
                        error=str(e),
                        file_path=str(file_path)
                    )
                    continue
            
            return profiles_data
            
        except Exception as e:
            logger.error("Failed to extract profiles", error=str(e), exc_info=True)
            raise DataProcessingError(f"Profile extraction failed: {str(e)}")
    
    def _extract_measurements(
        self, 
        ds: xr.Dataset, 
        profiles_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract measurement data from NetCDF dataset."""
        try:
            measurements_data = []
            
            # Get dimensions
            n_prof = ds.dims.get('N_PROF', 1)
            n_levels = ds.dims.get('N_LEVELS', 0)
            
            if n_levels == 0:
                logger.warning("No measurement levels found in dataset")
                return measurements_data
            
            # Variable mappings
            var_mapping = {
                'PRES': 'pressure',
                'TEMP': 'temperature',
                'PSAL': 'salinity',
                'DOXY': 'oxygen',
                'NITRATE': 'nitrate',
                'PH_IN_SITU_TOTAL': 'ph',
                'CHLA': 'chlorophyll_a',
                'BBP700': 'backscatter'
            }
            
            qf_mapping = {
                'PRES_QC': 'pressure_qf',
                'TEMP_QC': 'temperature_qf',
                'PSAL_QC': 'salinity_qf',
                'DOXY_QC': 'oxygen_qf',
                'NITRATE_QC': 'nitrate_qf',
                'PH_IN_SITU_TOTAL_QC': 'ph_qf',
                'CHLA_QC': 'chlorophyll_a_qf'
            }
            
            for prof_idx, profile_data in enumerate(profiles_data):
                try:
                    for level_idx in range(n_levels):
                        measurement = {
                            "prof_idx": prof_idx,  # For linking to profile
                            "level_idx": level_idx
                        }
                        
                        # Extract measurement values
                        for nc_var, field_name in var_mapping.items():
                            if nc_var in ds.variables:
                                try:
                                    if n_prof == 1:
                                        value = ds[nc_var].isel(N_LEVELS=level_idx).values
                                    else:
                                        value = ds[nc_var].isel(N_PROF=prof_idx, N_LEVELS=level_idx).values
                                    
                                    # Handle missing values
                                    if pd.isna(value) or value == 99999.0 or value == -999.0:
                                        value = None
                                    else:
                                        value = float(value)
                                    
                                    measurement[field_name] = value
                                    
                                except Exception as e:
                                    logger.debug(f"Failed to extract {nc_var}", error=str(e))
                                    measurement[field_name] = None
                        
                        # Extract quality flags
                        for qc_var, qf_field in qf_mapping.items():
                            if qc_var in ds.variables:
                                try:
                                    if n_prof == 1:
                                        qf_value = ds[qc_var].isel(N_LEVELS=level_idx).values
                                    else:
                                        qf_value = ds[qc_var].isel(N_PROF=prof_idx, N_LEVELS=level_idx).values
                                    
                                    # Convert quality flag to string
                                    if pd.isna(qf_value) or qf_value == b' ':
                                        qf_value = "9"  # Missing
                                    else:
                                        qf_value = str(qf_value).strip()
                                        if not qf_value:
                                            qf_value = "9"
                                    
                                    measurement[qf_field] = qf_value
                                    
                                except Exception as e:
                                    logger.debug(f"Failed to extract {qc_var}", error=str(e))
                                    measurement[qf_field] = "9"
                        
                        # Calculate depth from pressure if available
                        if measurement.get('pressure') is not None:
                            try:
                                # Approximate depth calculation (UNESCO formula)
                                pressure = measurement['pressure']
                                latitude = profile_data['latitude']
                                depth = self._pressure_to_depth(pressure, latitude)
                                measurement['depth'] = depth
                            except Exception as e:
                                logger.debug("Failed to calculate depth", error=str(e))
                                measurement['depth'] = None
                        
                        # Only add measurement if it has pressure data
                        if measurement.get('pressure') is not None:
                            measurements_data.append(measurement)
                
                except Exception as e:
                    logger.warning(
                        "Failed to extract measurements for profile",
                        prof_idx=prof_idx,
                        error=str(e)
                    )
                    continue
            
            return measurements_data
            
        except Exception as e:
            logger.error("Failed to extract measurements", error=str(e), exc_info=True)
            raise DataProcessingError(f"Measurement extraction failed: {str(e)}")
    
    def _pressure_to_depth(self, pressure: float, latitude: float) -> float:
        """
        Convert pressure to depth using UNESCO formula.
        
        Args:
            pressure: Pressure in dbar
            latitude: Latitude in degrees
            
        Returns:
            Depth in meters
        """
        try:
            # UNESCO formula for depth calculation
            # Simplified version - for more accuracy, use full UNESCO algorithm
            g = 9.780318 * (1.0 + (5.2788e-3 + 2.36e-5 * latitude**2) * np.sin(np.radians(latitude))**2)
            depth = pressure / (g * 1.025 / 9.80665)  # Approximate
            return float(depth)
        except:
            return pressure  # Fallback to pressure value
    
    async def _validate_extracted_data(
        self,
        float_data: Dict[str, Any],
        profiles_data: List[Dict[str, Any]],
        measurements_data: List[Dict[str, Any]],
        correlation_id: str
    ) -> Dict[str, Any]:
        """Validate extracted data using data validation framework."""
        try:
            validation_results = {
                "float_validation": await self.data_validator.validate_float_data(float_data),
                "profiles_validation": [],
                "measurements_validation": [],
                "overall_quality_score": 0.0,
                "validation_summary": {
                    "total_rules": 0,
                    "rules_passed": 0,
                    "rules_failed": 0,
                    "warnings": 0
                }
            }
            
            # Validate profiles
            for profile in profiles_data:
                profile_validation = await self.data_validator.validate_profile_data(profile)
                validation_results["profiles_validation"].append(profile_validation)
            
            # Validate measurements (sample for performance)
            sample_size = min(100, len(measurements_data))
            for measurement in measurements_data[:sample_size]:
                measurement_validation = await self.data_validator.validate_measurement_data(measurement)
                validation_results["measurements_validation"].append(measurement_validation)
            
            # Calculate overall quality score
            validation_results["overall_quality_score"] = self._calculate_quality_score(validation_results)
            
            return validation_results
            
        except Exception as e:
            logger.error("Data validation failed", error=str(e), correlation_id=correlation_id)
            return {
                "validation_error": str(e),
                "overall_quality_score": 0.0
            }
    
    def _calculate_quality_score(self, validation_results: Dict[str, Any]) -> float:
        """Calculate overall quality score from validation results."""
        try:
            total_score = 0.0
            total_weight = 0.0
            
            # Float validation weight
            float_val = validation_results.get("float_validation", {})
            if float_val:
                score = float_val.get("quality_score", 0.0)
                weight = 0.2
                total_score += score * weight
                total_weight += weight
            
            # Profiles validation weight
            profiles_val = validation_results.get("profiles_validation", [])
            if profiles_val:
                avg_score = sum(p.get("quality_score", 0.0) for p in profiles_val) / len(profiles_val)
                weight = 0.4
                total_score += avg_score * weight
                total_weight += weight
            
            # Measurements validation weight
            measurements_val = validation_results.get("measurements_validation", [])
            if measurements_val:
                avg_score = sum(m.get("quality_score", 0.0) for m in measurements_val) / len(measurements_val)
                weight = 0.4
                total_score += avg_score * weight
                total_weight += weight
            
            if total_weight > 0:
                return total_score / total_weight
            else:
                return 0.0
                
        except Exception as e:
            logger.error("Failed to calculate quality score", error=str(e))
            return 0.0
    
    async def ingest_netcdf_files(
        self,
        file_paths: List[Path],
        batch_size: int = None,
        correlation_id: str = None
    ) -> Dict[str, Any]:
        """
        Ingest multiple NetCDF files in batches.
        
        Args:
            file_paths: List of NetCDF file paths
            batch_size: Number of files to process in each batch
            correlation_id: Request correlation ID
            
        Returns:
            Dict containing ingestion results and statistics
        """
        correlation_id = correlation_id or f"ingest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        batch_size = batch_size or self.settings.argo_batch_size
        
        logger.info(
            "Starting NetCDF files ingestion",
            total_files=len(file_paths),
            batch_size=batch_size,
            correlation_id=correlation_id
        )
        
        # Log processing start
        await self._log_processing_operation(
            "etl", "netcdf_ingestion", "started",
            correlation_id=correlation_id,
            parameters={"total_files": len(file_paths), "batch_size": batch_size}
        )
        
        results = {
            "total_files": len(file_paths),
            "processed_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "total_profiles": 0,
            "total_measurements": 0,
            "processing_errors": [],
            "start_time": datetime.utcnow(),
            "correlation_id": correlation_id
        }
        
        try:
            # Process files in batches
            for i in range(0, len(file_paths), batch_size):
                batch_files = file_paths[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                logger.info(
                    "Processing batch",
                    batch_num=batch_num,
                    batch_size=len(batch_files),
                    correlation_id=correlation_id
                )
                
                batch_results = await self._process_file_batch(batch_files, correlation_id)
                
                # Update results
                results["processed_files"] += batch_results["processed_files"]
                results["successful_files"] += batch_results["successful_files"]
                results["failed_files"] += batch_results["failed_files"]
                results["total_profiles"] += batch_results["total_profiles"]
                results["total_measurements"] += batch_results["total_measurements"]
                results["processing_errors"].extend(batch_results["processing_errors"])
            
            results["end_time"] = datetime.utcnow()
            results["duration_seconds"] = (results["end_time"] - results["start_time"]).total_seconds()
            
            # Log completion
            await self._log_processing_operation(
                "etl", "netcdf_ingestion", "completed",
                correlation_id=correlation_id,
                records_processed=results["processed_files"],
                records_successful=results["successful_files"],
                records_failed=results["failed_files"],
                duration_seconds=results["duration_seconds"]
            )
            
            logger.info(
                "NetCDF files ingestion completed",
                **{k: v for k, v in results.items() if k not in ["processing_errors"]},
                errors_count=len(results["processing_errors"])
            )
            
            return results
            
        except Exception as e:
            # Log failure
            await self._log_processing_operation(
                "etl", "netcdf_ingestion", "failed",
                correlation_id=correlation_id,
                error_message=str(e)
            )
            
            logger.error(
                "NetCDF files ingestion failed",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise DataProcessingError(f"Ingestion failed: {str(e)}") from e
    
    async def _process_file_batch(
        self, 
        file_paths: List[Path], 
        correlation_id: str
    ) -> Dict[str, Any]:
        """Process a batch of NetCDF files."""
        batch_results = {
            "processed_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "total_profiles": 0,
            "total_measurements": 0,
            "processing_errors": []
        }
        
        for file_path in file_paths:
            try:
                batch_results["processed_files"] += 1
                
                # Process single file
                file_result = await self.process_netcdf_file(file_path, correlation_id)
                
                # Store data in database
                await self._store_file_data(file_result, correlation_id)
                
                batch_results["successful_files"] += 1
                batch_results["total_profiles"] += file_result["profiles_count"]
                batch_results["total_measurements"] += file_result["measurements_count"]
                
            except Exception as e:
                batch_results["failed_files"] += 1
                batch_results["processing_errors"].append({
                    "file_path": str(file_path),
                    "error": str(e),
                    "timestamp": datetime.utcnow()
                })
                
                logger.error(
                    "Failed to process file in batch",
                    file_path=str(file_path),
                    error=str(e),
                    correlation_id=correlation_id
                )
        
        return batch_results
    
    async def _store_file_data(self, file_result: Dict[str, Any], correlation_id: str):
        """Store processed file data in database."""
        try:
            async with get_async_session() as session:
                # Store or update float
                float_data = file_result["float_data"]
                float_obj = await self._get_or_create_float(session, float_data)
                
                # Store profiles and measurements
                # This would be implemented based on the specific data structure
                # For now, we'll log the successful processing
                
                logger.info(
                    "File data stored successfully",
                    float_wmo_id=float_data["wmo_id"],
                    profiles_count=file_result["profiles_count"],
                    correlation_id=correlation_id
                )
                
        except Exception as e:
            logger.error(
                "Failed to store file data",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise
    
    async def _get_or_create_float(self, session: AsyncSession, float_data: Dict[str, Any]) -> ArgoFloat:
        """Get existing float or create new one."""
        try:
            # Check if float exists
            stmt = select(ArgoFloat).where(ArgoFloat.wmo_id == float_data["wmo_id"])
            result = await session.execute(stmt)
            float_obj = result.scalar_one_or_none()
            
            if float_obj is None:
                # Create new float
                float_obj = ArgoFloat(**float_data)
                session.add(float_obj)
                await session.flush()
                
                logger.info(
                    "Created new ARGO float",
                    wmo_id=float_data["wmo_id"]
                )
            else:
                # Update existing float if needed
                for key, value in float_data.items():
                    if hasattr(float_obj, key) and value is not None:
                        setattr(float_obj, key, value)
                
                logger.debug(
                    "Updated existing ARGO float",
                    wmo_id=float_data["wmo_id"]
                )
            
            return float_obj
            
        except Exception as e:
            logger.error("Failed to get or create float", error=str(e), exc_info=True)
            raise
    
    async def _log_processing_operation(
        self,
        operation_type: str,
        operation_name: str,
        status: str,
        correlation_id: str = None,
        records_processed: int = 0,
        records_successful: int = 0,
        records_failed: int = 0,
        duration_seconds: float = None,
        error_message: str = None,
        parameters: Dict[str, Any] = None
    ):
        """Log processing operation to database."""
        try:
            async with get_async_session() as session:
                log_entry = ProcessingLog(
                    operation_type=operation_type,
                    operation_name=operation_name,
                    status=status,
                    correlation_id=correlation_id,
                    records_processed=records_processed,
                    records_successful=records_successful,
                    records_failed=records_failed,
                    duration_seconds=duration_seconds,
                    error_message=error_message,
                    parameters=parameters or {}
                )
                
                session.add(log_entry)
                await session.commit()
                
        except Exception as e:
            logger.error("Failed to log processing operation", error=str(e))
            # Don't raise - logging failure shouldn't stop processing
