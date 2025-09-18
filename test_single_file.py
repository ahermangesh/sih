#!/usr/bin/env python3
"""
Quick test to process a single NetCDF file and verify everything works.
"""

import sys
import os
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent))

import netCDF4 as nc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from app.core.config import get_settings
    from app.models.database_simple import ArgoFloat, Base
    settings = get_settings()
    print("✅ Configuration loaded successfully")
except Exception as e:
    print(f"❌ Configuration error: {e}")
    sys.exit(1)

def test_database_connection():
    """Test database connection."""
    try:
        engine = create_engine(settings.database_url_sync)
        connection = engine.connect()
        connection.close()
        print("✅ Database connection successful")
        return engine
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def test_netcdf_parsing():
    """Test parsing a single NetCDF file."""
    try:
        # Find first NetCDF file
        data_dir = Path("./argo_data")
        nc_files = list(data_dir.rglob("*.nc"))
        if not nc_files:
            print("❌ No NetCDF files found")
            return None
        
        test_file = nc_files[0]
        print(f"📁 Testing file: {test_file}")
        
        with nc.Dataset(str(test_file), 'r') as dataset:
            print(f"✅ NetCDF file opened successfully")
            print(f"📊 Dimensions: {dict(dataset.dimensions.items())}")
            print(f"📈 Variables: {list(dataset.variables.keys())[:10]}...")  # First 10 variables
            return test_file
    except Exception as e:
        print(f"❌ NetCDF parsing failed: {e}")
        return None

def test_database_write(engine):
    """Test writing to database."""
    try:
        # Create tables
        Base.metadata.create_all(engine)
        print("✅ Database tables created")
        
        # Test insert
        Session = sessionmaker(bind=engine)
        session = Session()
        
        test_float = ArgoFloat(
            wmo_id=999999,
            platform_type="TEST_FLOAT",
            status="ACTIVE",
            deployment_latitude=0.0,
            deployment_longitude=0.0
        )
        
        session.add(test_float)
        session.commit()
        
        # Verify insert
        count = session.query(ArgoFloat).count()
        session.close()
        
        print(f"✅ Database write successful - {count} records")
        return True
    except Exception as e:
        print(f"❌ Database write failed: {e}")
        return False

def main():
    print("🧪 FLOATCHAT SYSTEM TEST")
    print("=" * 30)
    
    # Test 1: Database connection
    print("\n🔗 Testing database connection...")
    engine = test_database_connection()
    if not engine:
        return
    
    # Test 2: NetCDF parsing
    print("\n📊 Testing NetCDF file parsing...")
    test_file = test_netcdf_parsing()
    if not test_file:
        return
    
    # Test 3: Database write
    print("\n💾 Testing database write...")
    if not test_database_write(engine):
        return
    
    print("\n🎉 ALL TESTS PASSED!")
    print("🚀 Ready to process all 2,056 files!")

if __name__ == "__main__":
    main()
