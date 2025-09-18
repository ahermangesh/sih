#!/usr/bin/env python3
"""
Enhanced ARGO Data Processor - Extracts REAL oceanographic data from NetCDF files.

This version extracts:
- Real coordinates (latitude, longitude)
- Temperature profiles with depth
- Salinity profiles with depth  
- Pressure measurements
- Profile timestamps
- Multiple profiles per float
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import netCDF4 as nc
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import logging

from app.core.config import get_settings
from app.models.database_simple import ArgoFloat, ArgoProfile, ArgoMeasurement, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
engine = create_engine(settings.database_url_sync)
Session = sessionmaker(bind=engine)

class EnhancedArgoProcessor:
    """Enhanced processor that extracts real oceanographic data."""
    
    def __init__(self):
        self.session = Session()
        self.processed_floats = 0
        self.processed_profiles = 0
        self.processed_measurements = 0
        
    def extract_real_data_from_netcdf(self, file_path: Path) -> dict:
        """Extract comprehensive oceanographic data from NetCDF file."""
        try:
            with nc.Dataset(str(file_path), 'r') as dataset:
                data = {
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'floats': [],
                    'profiles': [],
                    'measurements': []
                }
                
                # Get dimensions
                n_prof = dataset.dimensions['N_PROF'].size if 'N_PROF' in dataset.dimensions else 1
                n_levels = dataset.dimensions['N_LEVELS'].size if 'N_LEVELS' in dataset.dimensions else 0
                
                logger.info(f"Processing {file_path.name}: {n_prof} profiles, {n_levels} levels")
                
                # Extract platform numbers (WMO IDs)
                if 'PLATFORM_NUMBER' in dataset.variables:
                    platform_nums = dataset.variables['PLATFORM_NUMBER'][:]
                    if hasattr(platform_nums[0], 'tobytes'):
                        # Handle string arrays
                        wmo_ids = [int(''.join(char.decode() for char in row if char != b' ').strip()) 
                                 for row in platform_nums]
                    else:
                        wmo_ids = [int(platform_nums[0])] * n_prof
                else:
                    # Generate from filename if not available
                    base_wmo = hash(file_path.name) % 1000000
                    wmo_ids = [base_wmo] * n_prof
                
                # Extract coordinates
                latitudes = dataset.variables['LATITUDE'][:] if 'LATITUDE' in dataset.variables else np.full(n_prof, 0.0)
                longitudes = dataset.variables['LONGITUDE'][:] if 'LONGITUDE' in dataset.variables else np.full(n_prof, 0.0)
                
                # Extract timestamps
                if 'JULD' in dataset.variables:
                    julian_days = dataset.variables['JULD'][:]
                    # Convert Julian days to datetime (ARGO uses days since 1950-01-01)
                    reference_date = datetime(1950, 1, 1)
                    timestamps = []
                    for jd in julian_days:
                        if not np.isnan(jd) and jd > 0:
                            try:
                                timestamp = reference_date + timedelta(days=float(jd))
                                timestamps.append(timestamp)
                            except:
                                timestamps.append(None)
                        else:
                            timestamps.append(None)
                else:
                    timestamps = [None] * n_prof
                
                # Extract measurement data
                temp_data = dataset.variables['TEMP'][:] if 'TEMP' in dataset.variables else None
                sal_data = dataset.variables['PSAL'][:] if 'PSAL' in dataset.variables else None
                pres_data = dataset.variables['PRES'][:] if 'PRES' in dataset.variables else None
                
                # Process each profile
                for prof_idx in range(n_prof):
                    wmo_id = wmo_ids[prof_idx] if prof_idx < len(wmo_ids) else wmo_ids[0]
                    lat = float(latitudes[prof_idx]) if not np.isnan(latitudes[prof_idx]) else 0.0
                    lon = float(longitudes[prof_idx]) if not np.isnan(longitudes[prof_idx]) else 0.0
                    timestamp = timestamps[prof_idx] if prof_idx < len(timestamps) else None
                    
                    # Create float record
                    float_data = {
                        'wmo_id': wmo_id,
                        'latitude': lat,
                        'longitude': lon,
                        'timestamp': timestamp,
                        'file_name': file_path.name
                    }
                    data['floats'].append(float_data)
                    
                    # Create profile record
                    profile_data = {
                        'wmo_id': wmo_id,
                        'profile_index': prof_idx,
                        'latitude': lat,
                        'longitude': lon,
                        'timestamp': timestamp,
                        'measurements': []
                    }
                    
                    # Extract measurements for this profile
                    if temp_data is not None and sal_data is not None and pres_data is not None:
                        for level_idx in range(n_levels):
                            try:
                                temp = float(temp_data[prof_idx, level_idx]) if not np.isnan(temp_data[prof_idx, level_idx]) else None
                                sal = float(sal_data[prof_idx, level_idx]) if not np.isnan(sal_data[prof_idx, level_idx]) else None
                                pres = float(pres_data[prof_idx, level_idx]) if not np.isnan(pres_data[prof_idx, level_idx]) else None
                                
                                if temp is not None or sal is not None or pres is not None:
                                    measurement = {
                                        'wmo_id': wmo_id,
                                        'profile_index': prof_idx,
                                        'level_index': level_idx,
                                        'pressure': pres,
                                        'temperature': temp,
                                        'salinity': sal
                                    }
                                    profile_data['measurements'].append(measurement)
                                    data['measurements'].append(measurement)
                            except:
                                continue
                    
                    data['profiles'].append(profile_data)
                
                return data
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return None
    
    def save_enhanced_data(self, data: dict) -> bool:
        """Save enhanced data to database."""
        try:
            # Save or update float records with real coordinates
            for float_data in data['floats']:
                existing_float = self.session.query(ArgoFloat).filter_by(wmo_id=float_data['wmo_id']).first()
                
                if existing_float:
                    # Update with real coordinates if we have them
                    if float_data['latitude'] != 0.0 or float_data['longitude'] != 0.0:
                        existing_float.deployment_latitude = float_data['latitude']
                        existing_float.deployment_longitude = float_data['longitude']
                        if float_data['timestamp']:
                            existing_float.deployment_date = float_data['timestamp']
                else:
                    # Create new float record
                    new_float = ArgoFloat(
                        wmo_id=float_data['wmo_id'],
                        platform_type="ARGO_FLOAT",
                        deployment_latitude=float_data['latitude'],
                        deployment_longitude=float_data['longitude'],
                        deployment_date=float_data['timestamp'],
                        status="ACTIVE"
                    )
                    self.session.add(new_float)
                    self.processed_floats += 1
            
            # Save profile records (if we had the table)
            # For now, we'll just count them
            self.processed_profiles += len(data['profiles'])
            
            # Save measurement records (if we had the table)
            # For now, we'll just count them  
            self.processed_measurements += len(data['measurements'])
            
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Database save error: {e}")
            self.session.rollback()
            return False
    
    def process_sample_files(self, max_files: int = 10):
        """Process a sample of files with enhanced extraction."""
        data_dir = Path("./argo_data")
        nc_files = list(data_dir.rglob("*.nc"))[:max_files]
        
        logger.info(f"Processing {len(nc_files)} sample files with enhanced extraction...")
        
        successful = 0
        failed = 0
        
        for file_path in nc_files:
            data = self.extract_real_data_from_netcdf(file_path)
            if data and self.save_enhanced_data(data):
                successful += 1
                if successful % 5 == 0:
                    logger.info(f"Processed {successful}/{len(nc_files)} files")
            else:
                failed += 1
        
        logger.info(f"Enhanced processing complete!")
        logger.info(f"✅ Successful: {successful}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"🌊 Floats processed: {self.processed_floats}")
        logger.info(f"📊 Profiles found: {self.processed_profiles}")
        logger.info(f"🔬 Measurements found: {self.processed_measurements}")
        
        return {
            'successful': successful,
            'failed': failed,
            'floats': self.processed_floats,
            'profiles': self.processed_profiles,
            'measurements': self.processed_measurements
        }
    
    def close(self):
        """Close database session."""
        self.session.close()

def main():
    print("🌊 ENHANCED ARGO DATA EXTRACTION")
    print("=" * 40)
    print("Extracting REAL oceanographic data from NetCDF files...")
    
    processor = EnhancedArgoProcessor()
    
    try:
        # Process sample files to update coordinates and extract real data
        results = processor.process_sample_files(max_files=20)
        
        print("\n🎯 ENHANCED EXTRACTION RESULTS:")
        print(f"✅ Files processed: {results['successful']}")
        print(f"🌊 ARGO floats: {results['floats']}")
        print(f"📊 Profiles: {results['profiles']}")
        print(f"🔬 Measurements: {results['measurements']}")
        
        # Verify coordinates were updated
        session = Session()
        coord_check = session.execute("""
            SELECT 
                COUNT(CASE WHEN deployment_latitude != 0 OR deployment_longitude != 0 THEN 1 END) as with_coords,
                COUNT(*) as total,
                MIN(deployment_latitude) as min_lat,
                MAX(deployment_latitude) as max_lat,
                MIN(deployment_longitude) as min_lon,
                MAX(deployment_longitude) as max_lon
            FROM argo_floats
        """).fetchone()
        session.close()
        
        print(f"\n🗺️ COORDINATE UPDATE RESULTS:")
        print(f"📍 Records with real coordinates: {coord_check[0]}/{coord_check[1]}")
        print(f"🌍 Latitude range: {coord_check[2]:.2f}° to {coord_check[3]:.2f}°")
        print(f"🌍 Longitude range: {coord_check[4]:.2f}° to {coord_check[5]:.2f}°")
        
        if coord_check[0] > 0:
            print("🎉 SUCCESS! Real coordinates extracted from NetCDF files!")
        else:
            print("⚠️ Coordinates still not extracted properly")
            
    finally:
        processor.close()

if __name__ == "__main__":
    main()
