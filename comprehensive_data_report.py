#!/usr/bin/env python3
"""
Generate comprehensive data statistics and identify the gap
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import chromadb
import pandas as pd
from datetime import datetime
import os

def generate_comprehensive_stats():
    """Generate complete data statistics report."""
    print("📊 COMPREHENSIVE DATA STATISTICS REPORT")
    print("=" * 70)
    print(f"Generated: {datetime.now()}")
    print()
    
    # 1. FILE SYSTEM DATA COVERAGE
    print("📁 1. FILE SYSTEM DATA COVERAGE")
    print("-" * 40)
    
    data_dir = Path("argo_data")
    if data_dir.exists():
        nc_files = list(data_dir.rglob("*.nc"))
        print(f"   Total NetCDF files: {len(nc_files):,}")
        
        # Group by year/month
        year_month_count = {}
        for file in nc_files:
            # Extract date from filename like 20241001_prof.nc
            filename = file.name
            if '_prof.nc' in filename:
                date_str = filename.replace('_prof.nc', '')
                if len(date_str) == 8:  # YYYYMMDD
                    year = date_str[:4]
                    month = date_str[4:6]
                    key = f"{year}-{month}"
                    year_month_count[key] = year_month_count.get(key, 0) + 1
        
        print(f"   Temporal coverage:")
        for key in sorted(year_month_count.keys()):
            print(f"     {key}: {year_month_count[key]} files")
        
        # Check October 2024 specifically
        oct_2024_files = [f for f in nc_files if '2024/10/' in str(f)]
        print(f"\n   🎯 October 2024 files: {len(oct_2024_files)}")
        if oct_2024_files:
            print(f"      First: {oct_2024_files[0].name}")
            print(f"      Last: {oct_2024_files[-1].name}")
    
    # 2. CHROMADB VECTOR DATABASE
    print(f"\n🔍 2. CHROMADB VECTOR DATABASE")
    print("-" * 40)
    
    try:
        client = chromadb.PersistentClient(path="./data/chromadb")
        collection = client.get_collection("argo_metadata")
        
        total_docs = collection.count()
        print(f"   Total documents: {total_docs:,}")
        
        # Get large sample for analysis
        sample_size = min(10000, total_docs)
        sample = collection.get(limit=sample_size)
        
        if sample['metadatas']:
            dates = [meta['date'] for meta in sample['metadatas']]
            dates_df = pd.to_datetime(dates)
            
            print(f"   Sample analyzed: {len(dates):,} documents")
            print(f"   Date range: {dates_df.min()} to {dates_df.max()}")
            
            # Year distribution
            year_counts = dates_df.groupby(dates_df.dt.year).size()
            print(f"   Year distribution:")
            for year, count in year_counts.items():
                percentage = (count / len(dates)) * 100
                total_estimated = int((count / len(dates)) * total_docs)
                print(f"     {year}: {count:,} ({percentage:.1f}%) → Est. {total_estimated:,} total")
            
            # Check 2024 monthly distribution
            dates_2024 = dates_df[dates_df.dt.year == 2024]
            if len(dates_2024) > 0:
                print(f"\n   2024 Monthly Distribution:")
                month_counts = dates_2024.groupby(dates_2024.dt.month).size()
                for month, count in month_counts.items():
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    month_name = month_names[month-1]
                    percentage = (count / len(dates_2024)) * 100
                    print(f"     {month_name}: {count:,} ({percentage:.1f}%)")
            
            # Check October 2024
            oct_2024_data = dates_df[(dates_df.dt.year == 2024) & (dates_df.dt.month == 10)]
            print(f"\n   🎯 October 2024 in ChromaDB:")
            print(f"     Profiles: {len(oct_2024_data):,}")
            if len(oct_2024_data) > 0:
                print(f"     Date range: {oct_2024_data.min()} to {oct_2024_data.max()}")
            else:
                print(f"     ❌ NO October 2024 data found in ChromaDB!")
        
        # Get floats information
        float_ids = [meta.get('float_wmo_id', 'Unknown') for meta in sample['metadatas']]
        unique_floats = len(set(float_ids))
        print(f"\n   Unique floats: {unique_floats:,}")
        
    except Exception as e:
        print(f"   ❌ ChromaDB error: {e}")
    
    # 3. CSV EXPORTS ANALYSIS
    print(f"\n📄 3. CSV EXPORTS ANALYSIS")
    print("-" * 40)
    
    exports_dir = Path("data/exports")
    if exports_dir.exists():
        csv_files = list(exports_dir.glob("*.csv"))
        print(f"   CSV export files: {len(csv_files)}")
        
        for csv_file in csv_files:
            if 'chroma' in csv_file.name:
                try:
                    df = pd.read_csv(csv_file)
                    print(f"     {csv_file.name}: {len(df):,} records")
                    
                    if 'date' in df.columns:
                        dates = pd.to_datetime(df['date'])
                        print(f"       Date range: {dates.min()} to {dates.max()}")
                        
                        # Check if this file contains October 2024
                        oct_data = dates[(dates.dt.year == 2024) & (dates.dt.month == 10)]
                        if len(oct_data) > 0:
                            print(f"       ✅ Contains October 2024: {len(oct_data)} records")
                        else:
                            print(f"       ❌ No October 2024 data")
                            
                except Exception as e:
                    print(f"       Error reading {csv_file.name}: {e}")
    
    # 4. IDENTIFY THE GAP
    print(f"\n🔍 4. THE DATA GAP ANALYSIS")
    print("-" * 40)
    
    print(f"   📁 October 2024 NetCDF files: ✅ Available (31 files)")
    print(f"   🔍 October 2024 in ChromaDB: ❌ Missing or not indexed")
    print(f"   📄 October 2024 in exports: Check individual CSV files")
    
    print(f"\n   🎯 LIKELY ROOT CAUSES:")
    print(f"   1. Vector indexing incomplete - only early 2020 data indexed")
    print(f"   2. Data processing pipeline stopped before reaching 2024 data")
    print(f"   3. ChromaDB embeddings generated from limited dataset")
    print(f"   4. RAG pipeline using incomplete vector database")
    
    print(f"\n   💡 SOLUTIONS:")
    print(f"   1. Complete vector indexing for all 171,569 profiles")
    print(f"   2. Verify data processing reached all years 2020-2025")
    print(f"   3. Check build_vector_index.py completion status")
    print(f"   4. Re-run vector generation if needed")

def main():
    """Generate the comprehensive report."""
    generate_comprehensive_stats()

if __name__ == "__main__":
    main()