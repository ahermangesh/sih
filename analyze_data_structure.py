#!/usr/bin/env python3
"""
Examine NetCDF file structure and ChromaDB coverage
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import netCDF4 as nc
import pandas as pd
import numpy as np
from datetime import datetime
import chromadb

def examine_netcdf_file(file_path):
    """Examine the structure of a NetCDF file."""
    print(f"\n🔍 EXAMINING NETCDF FILE: {file_path}")
    print("=" * 60)
    
    try:
        with nc.Dataset(file_path, 'r') as dataset:
            print(f"✅ File opened successfully")
            print(f"📁 File format: {dataset.file_format}")
            print(f"📊 Dataset dimensions: {list(dataset.dimensions.keys())}")
            
            # Show all variables
            print(f"\n📋 Variables ({len(dataset.variables)}):")
            for var_name, var in dataset.variables.items():
                print(f"   {var_name}: {var.shape} - {getattr(var, 'long_name', 'No description')}")
            
            # Check for key oceanographic variables
            key_vars = ['TEMP', 'PSAL', 'PRES', 'LATITUDE', 'LONGITUDE', 'JULD', 'STATION_PARAMETERS']
            print(f"\n🌊 Key Oceanographic Variables:")
            for var in key_vars:
                if var in dataset.variables:
                    data = dataset.variables[var]
                    print(f"   ✅ {var}: {data.shape}")
                    if var == 'JULD' and len(data) > 0:
                        # Show date range
                        dates = nc.num2date(data[:], data.units)
                        print(f"      Date range: {dates.min()} to {dates.max()}")
                    elif var in ['TEMP', 'PSAL', 'PRES'] and len(data) > 0:
                        # Show data range
                        valid_data = data[~data.mask] if hasattr(data, 'mask') else data[:]
                        if len(valid_data) > 0:
                            print(f"      Range: {valid_data.min():.2f} to {valid_data.max():.2f}")
                else:
                    print(f"   ❌ {var}: Missing")
            
            # Extract float information
            if 'PLATFORM_NUMBER' in dataset.variables:
                platform = dataset.variables['PLATFORM_NUMBER'][:]
                if hasattr(platform, 'data'):
                    platform = platform.data
                print(f"\n🚢 Platform/Float ID: {platform}")
            
            # Check profiles count
            if 'N_PROF' in dataset.dimensions:
                n_profiles = dataset.dimensions['N_PROF'].size
                print(f"📊 Number of profiles: {n_profiles}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error examining NetCDF file: {e}")
        return False

def check_chromadb_coverage():
    """Check ChromaDB temporal coverage."""
    print(f"\n🔍 CHECKING CHROMADB TEMPORAL COVERAGE")
    print("=" * 60)
    
    try:
        client = chromadb.PersistentClient(path="./data/chromadb")
        collection = client.get_collection("argo_metadata")
        
        # Get all documents
        total_count = collection.count()
        print(f"📊 Total documents in ChromaDB: {total_count:,}")
        
        # Sample larger batch to check temporal coverage
        sample_size = min(1000, total_count)
        sample = collection.get(limit=sample_size)
        
        # Extract dates from metadata
        dates = []
        for metadata in sample['metadatas']:
            if 'date' in metadata:
                dates.append(metadata['date'])
        
        if dates:
            dates = pd.to_datetime(dates)
            print(f"\n📅 Temporal Coverage (from {len(dates)} samples):")
            print(f"   Earliest: {dates.min()}")
            print(f"   Latest: {dates.max()}")
            print(f"   Span: {(dates.max() - dates.min()).days} days")
            
            # Group by year-month
            year_month = dates.dt.to_period('M')
            coverage = year_month.value_counts().sort_index()
            print(f"\n📊 Monthly Distribution:")
            for period, count in coverage.head(10).items():
                print(f"   {period}: {count} profiles")
            
            # Check October 2024 specifically
            oct_2024 = dates[dates.dt.to_period('M') == '2024-10']
            print(f"\n🎯 October 2024 in ChromaDB: {len(oct_2024)} profiles")
            
            # Check if we have recent data
            recent = dates[dates >= '2024-10-01']
            print(f"🔄 Data from Oct 2024 onwards: {len(recent)} profiles")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB error: {e}")
        return False

def check_july_csv():
    """Examine the July 2024 CSV export."""
    print(f"\n🔍 ANALYZING JULY 2024 CSV EXPORT")
    print("=" * 60)
    
    try:
        df = pd.read_csv("data/exports/chroma_2024-07.csv")
        print(f"📊 CSV Records: {len(df):,}")
        print(f"📅 Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Check unique floats
        unique_floats = df['metadata.float_wmo_id'].nunique()
        print(f"🚢 Unique floats in July 2024: {unique_floats}")
        
        # Check geographic coverage
        print(f"🌍 Geographic coverage:")
        print(f"   Latitude: {df['metadata.latitude'].min():.2f} to {df['metadata.latitude'].max():.2f}")
        print(f"   Longitude: {df['metadata.longitude'].min():.2f} to {df['metadata.longitude'].max():.2f}")
        
        # Sample some documents
        print(f"\n📄 Sample Documents:")
        for i in range(min(3, len(df))):
            doc = df.iloc[i]
            print(f"   {i+1}. Float {doc['metadata.float_wmo_id']} on {doc['date']}")
            print(f"      Location: ({doc['metadata.latitude']:.2f}, {doc['metadata.longitude']:.2f})")
            print(f"      Summary: {doc['document'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ CSV analysis error: {e}")
        return False

def main():
    """Run all analyses."""
    print("🔍 NETCDF AND CHROMADB ANALYSIS")
    print("=" * 70)
    
    # Examine the NetCDF file
    netcdf_file = "argo_data/2024/10/20241001_prof.nc"
    netcdf_ok = examine_netcdf_file(netcdf_file)
    
    # Check ChromaDB coverage
    chromadb_ok = check_chromadb_coverage()
    
    # Analyze July CSV
    csv_ok = check_july_csv()
    
    print(f"\n📊 ANALYSIS SUMMARY")
    print("=" * 30)
    print(f"NetCDF Analysis: {'✅ OK' if netcdf_ok else '❌ FAILED'}")
    print(f"ChromaDB Analysis: {'✅ OK' if chromadb_ok else '❌ FAILED'}")
    print(f"CSV Analysis: {'✅ OK' if csv_ok else '❌ FAILED'}")
    
    print(f"\n💡 INSIGHTS:")
    print("1. ChromaDB contains 171,569 total documents")
    print("2. Each document is a profile summary with rich metadata")
    print("3. NetCDF files contain raw measurement data")
    print("4. The gap might be in how queries are processed or embeddings searched")

if __name__ == "__main__":
    main()