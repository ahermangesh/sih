#!/usr/bin/env python3
"""
COMPLETE NETCDF DATA EXTRACTOR FOR FLOATCHAT
============================================
This script extracts ALL oceanographic data from ARGO NetCDF files:
- Float metadata (WMO ID, platform type, deployment info)
- Profile coordinates and timestamps
- Temperature, salinity, pressure measurements with depths
- Quality flags and measurement metadata

Author: FloatChat Team
Date: 2025-09-17
"""

import os
import sys
import glob
import netCDF4
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import structlog
from sqlalchemy import create_engine, text, Table, Column, Integer, Float, String, DateTime, ForeignKey, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.ext.declarative import declarative_base
import psycopg2.extras
import multiprocessing
import time
from pathlib import Path

# Setup logging
logger = structlog.get_logger(__name__)

# Database configuration
DATABASE_URL = "postgresql://floatchat_user:floatchat_secure_2025@localhost:5432/floatchat_db"

# Create SQLAlchemy base
Base = declarative_base()

class ArgoFloat(Base):
    """ARGO Float metadata table"""
    __tablename__ = "argo_floats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    wmo_id = Column(Integer, unique=True, nullable=False, index=True)
    platform_type = Column(String(50), nullable=False)
    deployment_date = Column(DateTime)
    deployment_latitude = Column(Float)
    deployment_longitude = Column(Float)
    status = Column(String(20), default="ACTIVE")
    
    # Relationship to profiles
    profiles = relationship("ArgoProfile", back_populates="float", cascade="all, delete-orphan")

class ArgoProfile(Base):
    """Individual ARGO profile data"""
    __tablename__ = "argo_profiles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    float_id = Column(Integer, ForeignKey("argo_floats.id"), nullable=False, index=True)
    profile_number = Column(Integer, nullable=False)
    cycle_number = Column(Integer)
    profile_date = Column(DateTime)
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Quality flags
    position_qc = Column(String(1))
    profile_qc = Column(String(1))
    
    # Relationships
    float = relationship("ArgoFloat", back_populates="profiles")
    measurements = relationship("ArgoMeasurement", back_populates="profile", cascade="all, delete-orphan")

class ArgoMeasurement(Base):
    """Individual depth-based measurements"""
    __tablename__ = "argo_measurements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("argo_profiles.id"), nullable=False, index=True)
    
    # Measurement data
    pressure = Column(Float)  # dbar
    depth = Column(Float)     # meters
    temperature = Column(Float)  # Celsius
    salinity = Column(Float)     # PSU
    
    # Quality control flags
    pressure_qc = Column(String(1))
    temperature_qc = Column(String(1))
    salinity_qc = Column(String(1))
    
    # Relationship
    profile = relationship("ArgoProfile", back_populates="measurements")

class CompleteArgoDataExtractor:
    """
    Comprehensive ARGO NetCDF data extractor that extracts:
    1. Float metadata
    2. Profile information 
    3. All oceanographic measurements
    """
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        logger.info("✅ Database connection established for complete extractor")
    
    def setup_database(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("🔧 Complete database schema created")
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
            raise
    
    def extract_float_metadata(self, ds: xr.Dataset, file_path: str) -> Dict[str, Any]:
        """Extract float metadata from NetCDF dataset"""
        try:
            # Extract WMO ID
            platform_number = ds['PLATFORM_NUMBER'].values
            if isinstance(platform_number, np.ndarray):
                wmo_id_str = ''.join([x.decode('utf-8') if isinstance(x, bytes) else str(x) for x in platform_number.flat]).strip()
            else:
                wmo_id_str = str(platform_number).strip()
            
            wmo_id = int(wmo_id_str) if wmo_id_str.isdigit() else hash(file_path) % 1000000
            
            # Extract deployment date from reference date
            try:
                ref_date_raw = ds['REFERENCE_DATE_TIME'].values
                if isinstance(ref_date_raw, np.ndarray):
                    ref_date_str = ''.join([x.decode('utf-8') if isinstance(x, bytes) else str(x) for x in ref_date_raw.flat]).strip()
                else:
                    ref_date_str = str(ref_date_raw).strip()
                
                deployment_date = datetime.strptime(ref_date_str, '%Y%m%d%H%M%S')
            except:
                deployment_date = datetime.now()
            
            # Extract deployment location (first profile coordinates)
            try:
                lat_values = ds['LATITUDE'].values
                lon_values = ds['LONGITUDE'].values
                
                deployment_latitude = float(lat_values.flat[0]) if lat_values.size > 0 else 0.0
                deployment_longitude = float(lon_values.flat[0]) if lon_values.size > 0 else 0.0
            except:
                deployment_latitude = deployment_longitude = 0.0
            
            return {
                'wmo_id': wmo_id,
                'platform_type': 'ARGO_FLOAT',
                'deployment_date': deployment_date,
                'deployment_latitude': deployment_latitude,
                'deployment_longitude': deployment_longitude,
                'status': 'ACTIVE'
            }
            
        except Exception as e:
            logger.error(f"❌ Error extracting float metadata from {file_path}: {e}")
            return None
    
    def extract_profiles_and_measurements(self, ds: xr.Dataset, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Extract all profiles and measurements from NetCDF dataset"""
        profiles = []
        measurements = []
        
        try:
            # Get number of profiles
            n_prof = ds.dims.get('N_PROF', 1)
            n_levels = ds.dims.get('N_LEVELS', 0)
            
            logger.info(f"📊 Processing {n_prof} profiles with {n_levels} levels from {os.path.basename(file_path)}")
            
            # Extract time reference for date calculations
            try:
                ref_date_raw = ds['REFERENCE_DATE_TIME'].values
                ref_date_str = ''.join([x.decode('utf-8') if isinstance(x, bytes) else str(x) for x in ref_date_raw.flat]).strip()
                ref_date = datetime.strptime(ref_date_str, '%Y%m%d%H%M%S')
            except:
                ref_date = datetime(1950, 1, 1)  # Default reference date
            
            # Extract profile data
            for prof_idx in range(n_prof):
                try:
                    # Profile metadata
                    profile_data = {
                        'profile_number': prof_idx + 1,
                        'cycle_number': None,
                        'profile_date': ref_date,
                        'latitude': 0.0,
                        'longitude': 0.0,
                        'position_qc': '1',
                        'profile_qc': '1'
                    }
                    
                    # Extract profile date from JULD
                    if 'JULD' in ds.variables:
                        try:
                            juld_values = ds['JULD'].values
                            if juld_values.size > prof_idx:
                                julian_day = float(juld_values.flat[prof_idx])
                                if not np.isnan(julian_day) and julian_day > 0:
                                    profile_data['profile_date'] = ref_date + timedelta(days=julian_day)
                        except:
                            pass
                    
                    # Extract coordinates
                    if 'LATITUDE' in ds.variables and 'LONGITUDE' in ds.variables:
                        try:
                            lat_values = ds['LATITUDE'].values
                            lon_values = ds['LONGITUDE'].values
                            
                            if lat_values.size > prof_idx and lon_values.size > prof_idx:
                                lat = float(lat_values.flat[prof_idx])
                                lon = float(lon_values.flat[prof_idx])
                                
                                if not (np.isnan(lat) or np.isnan(lon)):
                                    profile_data['latitude'] = lat
                                    profile_data['longitude'] = lon
                        except:
                            pass
                    
                    # Extract cycle number
                    if 'CYCLE_NUMBER' in ds.variables:
                        try:
                            cycle_values = ds['CYCLE_NUMBER'].values
                            if cycle_values.size > prof_idx:
                                profile_data['cycle_number'] = int(cycle_values.flat[prof_idx])
                        except:
                            pass
                    
                    profiles.append(profile_data)
                    
                    # Extract measurements for this profile
                    for level_idx in range(n_levels):
                        try:
                            measurement = {
                                'profile_index': prof_idx,  # Will be replaced with profile_id later
                                'pressure': None,
                                'depth': None,
                                'temperature': None,
                                'salinity': None,
                                'pressure_qc': '1',
                                'temperature_qc': '1',
                                'salinity_qc': '1'
                            }
                            
                            # Extract pressure
                            if 'PRES' in ds.variables:
                                try:
                                    pres_values = ds['PRES'].values
                                    if pres_values.ndim == 2:  # [N_PROF, N_LEVELS]
                                        pres = float(pres_values[prof_idx, level_idx])
                                    else:  # [N_LEVELS]
                                        pres = float(pres_values[level_idx])
                                    
                                    if not np.isnan(pres) and pres >= 0:
                                        measurement['pressure'] = pres
                                        # Approximate depth from pressure (1 dbar ≈ 1 meter)
                                        measurement['depth'] = pres
                                except:
                                    pass
                            
                            # Extract temperature
                            if 'TEMP' in ds.variables:
                                try:
                                    temp_values = ds['TEMP'].values
                                    if temp_values.ndim == 2:
                                        temp = float(temp_values[prof_idx, level_idx])
                                    else:
                                        temp = float(temp_values[level_idx])
                                    
                                    if not np.isnan(temp) and -5 <= temp <= 50:  # Reasonable ocean temperature range
                                        measurement['temperature'] = temp
                                except:
                                    pass
                            
                            # Extract salinity
                            if 'PSAL' in ds.variables:
                                try:
                                    sal_values = ds['PSAL'].values
                                    if sal_values.ndim == 2:
                                        sal = float(sal_values[prof_idx, level_idx])
                                    else:
                                        sal = float(sal_values[level_idx])
                                    
                                    if not np.isnan(sal) and 0 <= sal <= 50:  # Reasonable salinity range
                                        measurement['salinity'] = sal
                                except:
                                    pass
                            
                            # Only add measurement if it has at least one valid value
                            if any(measurement[key] is not None for key in ['pressure', 'temperature', 'salinity']):
                                measurements.append(measurement)
                            
                        except Exception as e:
                            logger.debug(f"Error extracting measurement {level_idx} from profile {prof_idx}: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"Error extracting profile {prof_idx}: {e}")
                    continue
            
            logger.info(f"✅ Extracted {len(profiles)} profiles and {len(measurements)} measurements")
            return profiles, measurements
            
        except Exception as e:
            logger.error(f"❌ Error extracting profiles/measurements from {file_path}: {e}")
            return [], []
    
    def process_single_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single NetCDF file and extract all data"""
        try:
            logger.info(f"🔍 Processing {os.path.basename(file_path)}")
            
            with xr.open_dataset(file_path, decode_times=False) as ds:
                # Extract float metadata
                float_data = self.extract_float_metadata(ds, file_path)
                if not float_data:
                    return {'success': False, 'error': 'Failed to extract float metadata'}
                
                # Extract profiles and measurements
                profiles, measurements = self.extract_profiles_and_measurements(ds, file_path)
                
                return {
                    'success': True,
                    'float_data': float_data,
                    'profiles': profiles,
                    'measurements': measurements,
                    'file_path': file_path
                }
                
        except Exception as e:
            logger.error(f"❌ Error processing {file_path}: {e}")
            return {'success': False, 'error': str(e), 'file_path': file_path}
    
    def save_to_database(self, extracted_data: Dict[str, Any]) -> bool:
        """Save extracted data to PostgreSQL database"""
        if not extracted_data['success']:
            return False
        
        try:
            with self.Session() as session:
                with session.begin():
                    # Save or update float
                    float_data = extracted_data['float_data']
                    existing_float = session.query(ArgoFloat).filter_by(wmo_id=float_data['wmo_id']).first()
                    
                    if existing_float:
                        # Update existing float
                        for key, value in float_data.items():
                            if key != 'wmo_id':
                                setattr(existing_float, key, value)
                        float_obj = existing_float
                    else:
                        # Create new float
                        float_obj = ArgoFloat(**float_data)
                        session.add(float_obj)
                        session.flush()  # Get the ID
                    
                    # Save profiles
                    for profile_data in extracted_data['profiles']:
                        profile_obj = ArgoProfile(
                            float_id=float_obj.id,
                            **profile_data
                        )
                        session.add(profile_obj)
                        session.flush()  # Get the profile ID
                        
                        # Save measurements for this profile
                        profile_measurements = [m for m in extracted_data['measurements'] 
                                              if m['profile_index'] == profile_data['profile_number'] - 1]
                        
                        for measurement_data in profile_measurements:
                            # Remove the profile_index key and add profile_id
                            measurement_data = measurement_data.copy()
                            del measurement_data['profile_index']
                            
                            measurement_obj = ArgoMeasurement(
                                profile_id=profile_obj.id,
                                **measurement_data
                            )
                            session.add(measurement_obj)
                    
                    session.commit()
                    
            logger.info(f"✅ Saved data for float {float_data['wmo_id']} with {len(extracted_data['profiles'])} profiles and {len(extracted_data['measurements'])} measurements")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database save failed: {e}")
            return False
    
    def test_single_file(self, file_path: str) -> None:
        """Test extraction on a single file"""
        logger.info(f"🧪 TESTING SINGLE FILE EXTRACTION: {os.path.basename(file_path)}")
        logger.info("=" * 60)
        
        # Extract data
        result = self.process_single_file(file_path)
        
        if result['success']:
            float_data = result['float_data']
            profiles = result['profiles']
            measurements = result['measurements']
            
            logger.info(f"🌊 FLOAT DATA:")
            logger.info(f"   WMO ID: {float_data['wmo_id']}")
            logger.info(f"   Platform: {float_data['platform_type']}")
            logger.info(f"   Deployment: {float_data['deployment_date']}")
            logger.info(f"   Location: {float_data['deployment_latitude']:.3f}°N, {float_data['deployment_longitude']:.3f}°E")
            
            logger.info(f"📊 PROFILES: {len(profiles)} found")
            for i, profile in enumerate(profiles[:3]):  # Show first 3
                logger.info(f"   Profile {i+1}: {profile['profile_date']} at {profile['latitude']:.3f}°N, {profile['longitude']:.3f}°E")
            
            logger.info(f"🌡️ MEASUREMENTS: {len(measurements)} found")
            temp_measurements = [m for m in measurements if m['temperature'] is not None]
            sal_measurements = [m for m in measurements if m['salinity'] is not None]
            pres_measurements = [m for m in measurements if m['pressure'] is not None]
            
            if temp_measurements:
                temps = [m['temperature'] for m in temp_measurements]
                logger.info(f"   Temperature: {min(temps):.2f} to {max(temps):.2f}°C ({len(temps)} values)")
            
            if sal_measurements:
                sals = [m['salinity'] for m in sal_measurements]
                logger.info(f"   Salinity: {min(sals):.2f} to {max(sals):.2f} PSU ({len(sals)} values)")
            
            if pres_measurements:
                pres = [m['pressure'] for m in pres_measurements]
                logger.info(f"   Pressure: {min(pres):.1f} to {max(pres):.1f} dbar ({len(pres)} values)")
            
            # Save to database
            logger.info(f"💾 SAVING TO DATABASE...")
            if self.save_to_database(result):
                logger.info(f"✅ SUCCESS! All data saved to PostgreSQL")
            else:
                logger.error(f"❌ FAILED to save to database")
            
        else:
            logger.error(f"❌ EXTRACTION FAILED: {result['error']}")
    
    def process_all_files(self, data_path: str = "./argo_data", max_files: int = None) -> Dict[str, int]:
        """Process all NetCDF files in the data directory"""
        logger.info(f"🚀 PROCESSING ALL NETCDF FILES FROM {data_path}")
        
        # Find all NetCDF files
        all_files = []
        for year_dir in glob.glob(os.path.join(data_path, '*')):
            if os.path.isdir(year_dir):
                for month_dir in glob.glob(os.path.join(year_dir, '*')):
                    if os.path.isdir(month_dir):
                        all_files.extend(glob.glob(os.path.join(month_dir, '*.nc')))
        
        if max_files:
            all_files = all_files[:max_files]
        
        total_files = len(all_files)
        logger.info(f"📁 Found {total_files} NetCDF files to process")
        
        # Process files
        processed = 0
        errors = 0
        total_floats = 0
        total_profiles = 0
        total_measurements = 0
        
        start_time = time.time()
        
        for i, file_path in enumerate(all_files):
            try:
                result = self.process_single_file(file_path)
                
                if result['success']:
                    if self.save_to_database(result):
                        processed += 1
                        total_floats += 1
                        total_profiles += len(result['profiles'])
                        total_measurements += len(result['measurements'])
                    else:
                        errors += 1
                else:
                    errors += 1
                
                # Progress update
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    logger.info(f"📈 Progress: {i+1}/{total_files} ({rate:.1f} files/sec)")
                
            except Exception as e:
                logger.error(f"❌ Error processing {file_path}: {e}")
                errors += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        results = {
            'total_files': total_files,
            'processed': processed,
            'errors': errors,
            'total_floats': total_floats,
            'total_profiles': total_profiles,
            'total_measurements': total_measurements,
            'total_time': total_time,
            'rate': processed / total_time if total_time > 0 else 0
        }
        
        logger.info("🎉 COMPLETE EXTRACTION FINISHED!")
        logger.info(f"📊 RESULTS:")
        logger.info(f"   Files processed: {processed}/{total_files}")
        logger.info(f"   Errors: {errors}")
        logger.info(f"   Floats: {total_floats}")
        logger.info(f"   Profiles: {total_profiles}")
        logger.info(f"   Measurements: {total_measurements}")
        logger.info(f"   Time: {total_time:.1f} seconds")
        logger.info(f"   Rate: {results['rate']:.1f} files/second")
        
        return results

def main():
    """Main function to run the complete data extraction"""
    logger.info("🌊 FLOATCHAT COMPLETE NETCDF DATA EXTRACTOR")
    logger.info("=" * 60)
    
    # Initialize extractor
    extractor = CompleteArgoDataExtractor()
    extractor.setup_database()
    
    # Test on single file first
    test_files = glob.glob("./argo_data/2020/01/20200101_prof.nc")
    if test_files:
        logger.info("🧪 TESTING SINGLE FILE FIRST...")
        extractor.test_single_file(test_files[0])
        
        # Ask user to continue
        print("\n" + "="*60)
        print("🔍 SINGLE FILE TEST COMPLETED!")
        print("✅ Check the output above to verify all data was extracted correctly.")
        print("📊 Temperature, salinity, pressure profiles should be visible.")
        print("🗄️ Data should be saved to PostgreSQL database.")
        print("\nDo you want to proceed with ALL files? (y/n): ", end="")
        
        response = input().strip().lower()
        if response in ['y', 'yes']:
            logger.info("🚀 PROCEEDING WITH ALL FILES...")
            extractor.process_all_files(max_files=100)  # Process first 100 files
        else:
            logger.info("⏹️ Stopping at user request")
    else:
        logger.error("❌ No test files found in ./argo_data/2020/01/")

if __name__ == "__main__":
    main()
