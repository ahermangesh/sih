#!/usr/bin/env python3
"""
Test ChromaDB temporal coverage more thoroughly
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import chromadb
import pandas as pd
from datetime import datetime

def check_temporal_coverage():
    """Check temporal coverage in ChromaDB with specific queries."""
    print(f"🔍 DETAILED CHROMADB TEMPORAL ANALYSIS")
    print("=" * 60)
    
    try:
        client = chromadb.PersistentClient(path="./data/chromadb")
        collection = client.get_collection("argo_metadata")
        
        total_count = collection.count()
        print(f"📊 Total documents: {total_count:,}")
        
        # Query for October 2024 specifically
        print(f"\n🎯 SEARCHING FOR OCTOBER 2024 DATA...")
        oct_2024_results = collection.query(
            query_texts=["October 2024 temperature salinity profile"],
            n_results=100,
            where={"date": {"$gte": "2024-10-01"}}
        )
        
        print(f"✅ Found {len(oct_2024_results['ids'][0])} October 2024+ results")
        
        # Show sample results
        for i in range(min(5, len(oct_2024_results['ids'][0]))):
            meta = oct_2024_results['metadatas'][0][i]
            doc = oct_2024_results['documents'][0][i]
            print(f"   {i+1}. {meta['date']} - Float {meta['float_wmo_id']}")
            print(f"      {doc[:80]}...")
        
        # Try different date formats
        print(f"\n🔍 CHECKING DATE RANGE COVERAGE...")
        
        # Get documents by year
        years_to_check = ['2020', '2021', '2022', '2023', '2024']
        for year in years_to_check:
            try:
                year_results = collection.query(
                    query_texts=[f"{year} oceanographic data"],
                    n_results=10,
                    where={"date": {"$gte": f"{year}-01-01", "$lt": f"{int(year)+1}-01-01"}}
                )
                
                count = len(year_results['ids'][0])
                print(f"   {year}: {count} samples found")
                
                if count > 0:
                    dates = [meta['date'] for meta in year_results['metadatas'][0]]
                    print(f"      Date range: {min(dates)} to {max(dates)}")
                    
            except Exception as e:
                print(f"   {year}: Error - {e}")
        
        # Try to get a broader sample
        print(f"\n📊 LARGE SAMPLE ANALYSIS...")
        large_sample = collection.get(limit=5000)
        
        if large_sample['metadatas']:
            dates = [meta['date'] for meta in large_sample['metadatas']]
            dates_df = pd.to_datetime(dates)
            
            print(f"   Sample size: {len(dates)}")
            print(f"   Date range: {dates_df.min()} to {dates_df.max()}")
            
            # Count by year
            year_counts = dates_df.groupby(dates_df.dt.year).size()
            print(f"   Year distribution:")
            for year, count in year_counts.items():
                print(f"      {year}: {count:,} profiles")
            
            # Check months in 2024
            dates_2024 = dates_df[dates_df.dt.year == 2024]
            if len(dates_2024) > 0:
                month_counts = dates_2024.groupby(dates_2024.dt.month).size()
                print(f"   2024 monthly distribution:")
                for month, count in month_counts.items():
                    month_name = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month-1]
                    print(f"      {month_name} 2024: {count:,} profiles")
                    
                # Check October specifically
                oct_2024 = dates_2024[dates_2024.dt.month == 10]
                print(f"\n🎯 October 2024 in ChromaDB: {len(oct_2024):,} profiles")
                if len(oct_2024) > 0:
                    print(f"   Date range: {oct_2024.min()} to {oct_2024.max()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_query_processing():
    """Test how queries are processed."""
    print(f"\n🔍 TESTING QUERY PROCESSING")
    print("=" * 60)
    
    try:
        client = chromadb.PersistentClient(path="./data/chromadb")
        collection = client.get_collection("argo_metadata")
        
        # Test different query types
        test_queries = [
            "October 2024 temperature data",
            "temperature profile October 2024",
            "ARGO float data from October 2024",
            "oceanographic measurements October 2024",
            "salinity temperature October 2024"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            
            results = collection.query(
                query_texts=[query],
                n_results=10
            )
            
            found_oct = 0
            for meta in results['metadatas'][0]:
                if '2024-10' in meta['date']:
                    found_oct += 1
            
            print(f"   Results: {len(results['ids'][0])}")
            print(f"   October 2024 results: {found_oct}")
            
            # Show top result
            if results['metadatas'][0]:
                top_meta = results['metadatas'][0][0]
                top_doc = results['documents'][0][0]
                print(f"   Top result: {top_meta['date']} - Float {top_meta['float_wmo_id']}")
                print(f"   Content: {top_doc[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run analysis."""
    print("🔍 CHROMADB TEMPORAL COVERAGE ANALYSIS")
    print("=" * 70)
    
    coverage_ok = check_temporal_coverage()
    query_ok = test_query_processing()
    
    print(f"\n📊 RESULTS")
    print("=" * 30)
    print(f"Temporal Coverage: {'✅ OK' if coverage_ok else '❌ FAILED'}")
    print(f"Query Processing: {'✅ OK' if query_ok else '❌ FAILED'}")

if __name__ == "__main__":
    main()