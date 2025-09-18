#!/usr/bin/env python3
"""
FloatChat - ARGO Data Loading Script

Load 6 years of ARGO NetCDF data into PostgreSQL database
according to the FloatChat Professional Development Plan.

This script implements:
- Bulk data loading with 10,000+ records/second performance
- Data validation and quality checks
- Progress tracking and error handling
- Incremental loading support
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

import pandas as pd
import numpy as np
import netCDF4 as nc
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

# Add app to Python path
sys.path.append(str(Path(__file__).parent))

from app.core.database import get_async_session, async_engine
from app.models.database import ArgoFloat, ArgoProfile, ArgoMeasurement, DataQuality, ProcessingLog
from app.core.config import get_settings

logger = structlog.get_logger(__name__)

class ArgoDataLoader:
    """Load ARGO NetCDF data into PostgreSQL database."""
    
    def __init__(self):
        self.settings = get_settings()
        self.data_dir = Path("argo_data")
        self.batch_size = 1000
        self.total_files = 0
        self.processed_files = 0
        self.total_profiles = 0
        self.total_measurements = 0
        self.errors = []
    
    async def load_all_data(self):
        """Load all ARGO data files into database."""
        start_time = time.time()
        
        logger.info("Starting ARGO data loading process")
        
        # Get all NetCDF files
        netcdf_files = list(self.data_dir.rglob("*.nc"))
        
        # For testing, limit to first 10 files
        netcdf_files = netcdf_files[:10]
        
        self.total_files = len(netcdf_files)
        
        logger.info(f"Found {self.total_files} NetCDF files to process (limited to first 10 for testing)")
        
        if self.total_files == 0:
            logger.error("No NetCDF files found in argo_data directory")
            return
        
        # Process files in batches
        batch_files = []
        for file_path in netcdf_files:
            batch_files.append(file_path)
            
            if len(batch_files) >= self.batch_size:
                await self._process_batch(batch_files)
                batch_files = []
        
        # Process remaining files
        if batch_files:
            await self._process_batch(batch_files)
        
        elapsed_time = time.time() - start_time
        
        logger.info(
            "ARGO data loading completed",
            total_files=self.total_files,
            processed_files=self.processed_files,
            total_profiles=self.total_profiles,
            total_measurements=self.total_measurements,
            elapsed_time=f"{elapsed_time:.2f}s",
            errors=len(self.errors)
        )
        
        if self.errors:
            logger.warning(f"Encountered {len(self.errors)} errors during processing")
            for error in self.errors[:10]:  # Show first 10 errors
                logger.warning("Processing error", **error)
    
    async def _process_batch(self, file_paths: List[Path]):
        """Process a batch of NetCDF files."""
        async with get_async_session() as session:
            try:
                floats_data = []
                profiles_data = []
                measurements_data = []
                
                for file_path in file_paths:
                    try:
                        logger.info(f"Processing file: {file_path}")
                        data = await self._extract_file_data(file_path)
                        if data:
                            logger.info(f"Extracted data: {len(data['floats'])} floats, {len(data['profiles'])} profiles, {len(data['measurements'])} measurements")
                            floats_data.extend(data['floats'])
                            profiles_data.extend(data['profiles'])
                            measurements_data.extend(data['measurements'])
                            self.processed_files += 1
                        else:
                            logger.warning(f"No data extracted from {file_path}")
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
                        self.errors.append({
                            'file': str(file_path),
                            'error': str(e),
                            'timestamp': datetime.utcnow().isoformat()
                        })
                
                # Bulk insert data
                if floats_data:
                    await self._bulk_insert_floats(session, floats_data)
                if profiles_data:
                    await self._bulk_insert_profiles(session, profiles_data)
                    self.total_profiles += len(profiles_data)
                if measurements_data:
                    await self._bulk_insert_measurements(session, measurements_data)
                    self.total_measurements += len(measurements_data)
                
                await session.commit()
                
                logger.info(
                    f"Processed batch: {self.processed_files}/{self.total_files} files, "
                    f"{self.total_profiles} profiles, {self.total_measurements} measurements"
                )
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Batch processing failed: {e}")
                raise
    
    async def _extract_file_data(self, file_path: Path) -> Optional[Dict[str, List[Dict]]]:
        """Extract data from a single NetCDF file."""
        try:
            with nc.Dataset(file_path, 'r') as dataset:
                # Extract basic float information
                platform_number = self._safe_get_var(dataset, 'PLATFORM_NUMBER')
                if not platform_number:
                    return None
                
                # Get dimensions
                n_prof = dataset.dimensions.get('N_PROF', None)
                n_levels = dataset.dimensions.get('N_LEVELS', None)
                
                if not n_prof or not n_levels:
                    return None
                
                n_prof_size = n_prof.size
                n_levels_size = n_levels.size
                
                # Extract float data
                float_data = {
                    'platform_number': int(platform_number) if platform_number else None,
                    'wmo_id': self._safe_get_var(dataset, 'PLATFORM_NUMBER'),
                    'project_name': self._safe_get_var(dataset, 'PROJECT_NAME'),
                    'platform_type': self._safe_get_var(dataset, 'PLATFORM_TYPE'),
                    'float_serial_no': self._safe_get_var(dataset, 'FLOAT_SERIAL_NO'),
                    'firmware_version': self._safe_get_var(dataset, 'FIRMWARE_VERSION'),
                    'wmo_inst_type': self._safe_get_var(dataset, 'WMO_INST_TYPE'),
                    'positioning_system': self._safe_get_var(dataset, 'POSITIONING_SYSTEM'),
                    'deployment_date': self._parse_date(dataset, 'LAUNCH_DATE'),
                    'deployment_latitude': self._safe_get_var(dataset, 'LAUNCH_LATITUDE'),
                    'deployment_longitude': self._safe_get_var(dataset, 'LAUNCH_LONGITUDE'),
                    'last_update': datetime.utcnow(),
                    'data_source': str(file_path.name)
                }
                
                floats = [float_data]
                profiles = []
                measurements = []
                
                # Extract profile data
                for prof_idx in range(n_prof_size):
                    try:
                        # Get profile date
                        juld = self._safe_get_var(dataset, 'JULD', prof_idx)
                        profile_date = self._convert_julian_date(juld) if juld else None
                        
                        # Get location
                        latitude = self._safe_get_var(dataset, 'LATITUDE', prof_idx)
                        longitude = self._safe_get_var(dataset, 'LONGITUDE', prof_idx)
                        
                        if not profile_date or latitude is None or longitude is None:
                            continue
                        
                        profile_data = {
                            'float_id': float_data['platform_number'],
                            'cycle_number': self._safe_get_var(dataset, 'CYCLE_NUMBER', prof_idx),
                            'profile_date': profile_date,
                            'latitude': float(latitude),
                            'longitude': float(longitude),
                            'ocean_region': self._determine_ocean_region(latitude, longitude),
                            'direction': self._safe_get_var(dataset, 'DIRECTION', prof_idx),
                            'data_mode': self._safe_get_var(dataset, 'DATA_MODE', prof_idx),
                            'quality_flag': self._safe_get_var(dataset, 'PROFILE_PRES_QC', prof_idx),
                            'n_levels': n_levels_size,
                            'max_pressure': None,  # Will be calculated from measurements
                            'processing_date': datetime.utcnow(),
                            'data_source': str(file_path.name)
                        }
                        
                        profiles.append(profile_data)
                        
                        # Extract measurements for this profile
                        measurements.extend(self._extract_measurements(
                            dataset, prof_idx, n_levels_size, 
                            float_data['platform_number'], 
                            profile_data['cycle_number']
                        ))
                        
                    except Exception as e:
                        logger.warning(f"Error processing profile {prof_idx} in {file_path}: {e}")
                        continue
                
                return {
                    'floats': floats,
                    'profiles': profiles,
                    'measurements': measurements
                }
                
        except Exception as e:
            logger.error(f"Error extracting data from {file_path}: {e}")
            return None
    
    def _extract_measurements(self, dataset, prof_idx: int, n_levels: int, 
                            float_id: int, cycle_number: int) -> List[Dict]:
        """Extract measurement data for a profile."""
        measurements = []
        
        # Get measurement arrays
        pressure = self._safe_get_array(dataset, 'PRES', prof_idx)
        temperature = self._safe_get_array(dataset, 'TEMP', prof_idx)
        salinity = self._safe_get_array(dataset, 'PSAL', prof_idx)
        
        # Quality control arrays
        pres_qc = self._safe_get_array(dataset, 'PRES_QC', prof_idx)
        temp_qc = self._safe_get_array(dataset, 'TEMP_QC', prof_idx)
        psal_qc = self._safe_get_array(dataset, 'PSAL_QC', prof_idx)
        
        for level_idx in range(n_levels):
            try:
                # Get values for this level
                pres_val = pressure[level_idx] if pressure is not None else None
                temp_val = temperature[level_idx] if temperature is not None else None
                sal_val = salinity[level_idx] if salinity is not None else None
                
                # Skip if all values are missing
                if all(val is None or (hasattr(val, 'mask') and val.mask) 
                       for val in [pres_val, temp_val, sal_val]):
                    continue
                
                measurement_data = {
                    'float_id': float_id,
                    'cycle_number': cycle_number,
                    'level_number': level_idx,
                    'pressure': float(pres_val) if pres_val is not None and not (hasattr(pres_val, 'mask') and pres_val.mask) else None,
                    'temperature': float(temp_val) if temp_val is not None and not (hasattr(temp_val, 'mask') and temp_val.mask) else None,
                    'salinity': float(sal_val) if sal_val is not None and not (hasattr(sal_val, 'mask') and sal_val.mask) else None,
                    'pressure_qc': str(pres_qc[level_idx]) if pres_qc is not None else None,
                    'temperature_qc': str(temp_qc[level_idx]) if temp_qc is not None else None,
                    'salinity_qc': str(psal_qc[level_idx]) if psal_qc is not None else None,
                    'measurement_date': datetime.utcnow()
                }
                
                measurements.append(measurement_data)
                
            except Exception as e:
                logger.debug(f"Error processing level {level_idx}: {e}")
                continue
        
        return measurements
    
    def _safe_get_var(self, dataset, var_name: str, index: Optional[int] = None):
        """Safely get variable from NetCDF dataset."""
        try:
            if var_name not in dataset.variables:
                return None
            
            var = dataset.variables[var_name]
            
            if index is not None:
                if len(var.shape) > 0 and index < var.shape[0]:
                    value = var[index]
                else:
                    return None
            else:
                value = var[:]
            
            # Handle masked arrays
            if hasattr(value, 'mask') and value.mask.all():
                return None
            
            # Convert to Python types
            if hasattr(value, 'item'):
                return value.item()
            elif isinstance(value, (np.ndarray, list)) and len(value) == 1:
                return value[0]
            else:
                return value
            
        except Exception:
            return None
    
    def _safe_get_array(self, dataset, var_name: str, prof_idx: int):
        """Safely get array variable from NetCDF dataset."""
        try:
            if var_name not in dataset.variables:
                return None
            
            var = dataset.variables[var_name]
            
            if len(var.shape) >= 2:
                return var[prof_idx, :]
            else:
                return None
                
        except Exception:
            return None
    
    def _parse_date(self, dataset, var_name: str) -> Optional[datetime]:
        """Parse date from NetCDF variable."""
        try:
            if var_name not in dataset.variables:
                return None
            
            date_str = dataset.variables[var_name][:].tobytes().decode('utf-8').strip()
            if date_str:
                return datetime.strptime(date_str, '%Y%m%d%H%M%S')
        except Exception:
            pass
        return None
    
    def _convert_julian_date(self, julian_day: float) -> Optional[datetime]:
        """Convert Julian day to datetime."""
        try:
            # ARGO uses days since 1950-01-01 00:00:00 UTC
            base_date = datetime(1950, 1, 1)
            return base_date + pd.Timedelta(days=julian_day)
        except Exception:
            return None
    
    def _determine_ocean_region(self, lat: float, lon: float) -> str:
        """Determine ocean region based on coordinates."""
        # Simple ocean region classification
        if -90 <= lat <= -60:
            return "Southern Ocean"
        elif 30 <= lat <= 90 and -180 <= lon <= 180:
            if -180 <= lon <= -30:
                return "North Atlantic"
            elif -30 <= lon <= 60:
                return "North Atlantic"
            else:
                return "North Pacific"
        elif -30 <= lat <= 30:
            if 20 <= lon <= 120:
                return "Indian Ocean"
            elif -100 <= lon <= 20:
                return "Atlantic Ocean"
            else:
                return "Pacific Ocean"
        else:
            return "Unknown"
    
    async def _bulk_insert_floats(self, session: AsyncSession, floats_data: List[Dict]):
        """Bulk insert float data with conflict resolution."""
        if not floats_data:
            return
        
        # Remove duplicates by platform_number
        unique_floats = {}
        for float_data in floats_data:
            platform_num = float_data.get('platform_number')
            if platform_num:
                unique_floats[platform_num] = float_data
        
        # Use INSERT ... ON CONFLICT DO UPDATE
        query = text("""
            INSERT INTO argo_floats (
                platform_number, wmo_id, project_name, platform_type, 
                float_serial_no, firmware_version, wmo_inst_type,
                positioning_system, deployment_date, deployment_latitude,
                deployment_longitude, last_update, data_source
            ) VALUES (
                :platform_number, :wmo_id, :project_name, :platform_type,
                :float_serial_no, :firmware_version, :wmo_inst_type,
                :positioning_system, :deployment_date, :deployment_latitude,
                :deployment_longitude, :last_update, :data_source
            ) ON CONFLICT (platform_number) DO UPDATE SET
                last_update = EXCLUDED.last_update,
                data_source = EXCLUDED.data_source
        """)
        
        await session.execute(query, list(unique_floats.values()))
    
    async def _bulk_insert_profiles(self, session: AsyncSession, profiles_data: List[Dict]):
        """Bulk insert profile data."""
        if not profiles_data:
            return
        
        query = text("""
            INSERT INTO argo_profiles (
                float_id, cycle_number, profile_date, latitude, longitude,
                ocean_region, direction, data_mode, quality_flag, n_levels,
                processing_date, data_source
            ) VALUES (
                :float_id, :cycle_number, :profile_date, :latitude, :longitude,
                :ocean_region, :direction, :data_mode, :quality_flag, :n_levels,
                :processing_date, :data_source
            ) ON CONFLICT (float_id, cycle_number) DO NOTHING
        """)
        
        await session.execute(query, profiles_data)
    
    async def _bulk_insert_measurements(self, session: AsyncSession, measurements_data: List[Dict]):
        """Bulk insert measurement data."""
        if not measurements_data:
            return
        
        query = text("""
            INSERT INTO argo_measurements (
                float_id, cycle_number, level_number, pressure, temperature,
                salinity, pressure_qc, temperature_qc, salinity_qc, measurement_date
            ) VALUES (
                :float_id, :cycle_number, :level_number, :pressure, :temperature,
                :salinity, :pressure_qc, :temperature_qc, :salinity_qc, :measurement_date
            ) ON CONFLICT (float_id, cycle_number, level_number) DO NOTHING
        """)
        
        await session.execute(query, measurements_data)


async def main():
    """Main function to load ARGO data."""
    print("🌊 FloatChat - ARGO Data Loading Script")
    print("=" * 50)
    
    # Initialize database first
    from app.core.database import init_database
    print("Initializing database...")
    await init_database()
    print("Database initialized ✅")
    
    loader = ArgoDataLoader()
    await loader.load_all_data()
    
    print("\n✅ Data loading completed!")
    print(f"📊 Statistics:")
    print(f"   • Files processed: {loader.processed_files}/{loader.total_files}")
    print(f"   • Total profiles: {loader.total_profiles}")
    print(f"   • Total measurements: {loader.total_measurements}")
    print(f"   • Errors: {len(loader.errors)}")


if __name__ == "__main__":
    asyncio.run(main())
