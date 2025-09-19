#!/usr/bin/env python3
"""
Simplified direct query test focusing on the key issue
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import chromadb
import pandas as pd
from sqlalchemy import create_engine, text

try:
    from app.core.config import get_settings
    settings = get_settings()
    print("✅ Configuration loaded")
except Exception as e:
    print(f"❌ Configuration error: {e}")
    sys.exit(1)

def simple_chromadb_test():
    """Simple ChromaDB test to see what's actually returned."""
    print("🔍 SIMPLE CHROMADB TEST")
    print("=" * 40)
    
    try:
        client = chromadb.PersistentClient(path="./data/chromadb")
        collection = client.get_collection("argo_metadata")
        
        print(f"📊 Total documents: {collection.count():,}")
        
        # Test the exact type of query a user would ask
        user_queries = [
            "October 2024 temperature data",
            "2024 oceanographic data", 
            "recent temperature measurements"
        ]
        
        for query in user_queries:
            print(f"\n🔍 Query: '{query}'")
            
            results = collection.query(
                query_texts=[query],
                n_results=10
            )
            
            print(f"   Results found: {len(results['ids'][0])}")
            
            if results['metadatas'][0]:
                print(f"   Sample results:")
                for i in range(min(5, len(results['metadatas'][0]))):
                    meta = results['metadatas'][0][i]
                    print(f"     {meta['date']} - Float {meta['float_wmo_id']}")
                    
                # Check if any 2024 data
                dates_2024 = [meta['date'] for meta in results['metadatas'][0] if '2024' in meta['date']]
                print(f"   2024 results: {len(dates_2024)}")
                
                # Check if any October 2024 data
                oct_2024 = [meta['date'] for meta in results['metadatas'][0] if '2024-10' in meta['date']]
                print(f"   October 2024 results: {len(oct_2024)}")
        
        # Now let's see if we can directly find some 2024 data
        print(f"\n🎯 DIRECT SEARCH FOR 2024 DATA:")
        
        # Get a larger sample to find 2024 data
        large_sample = collection.get(limit=50000)
        
        if large_sample['metadatas']:
            all_dates = [meta['date'] for meta in large_sample['metadatas']]
            
            # Find 2024 data
            dates_2024 = [date for date in all_dates if '2024' in date]
            print(f"   2024 data found in sample: {len(dates_2024)}")
            
            if dates_2024:
                # Show some examples
                print(f"   Sample 2024 dates:")
                for date in sorted(dates_2024)[:10]:
                    print(f"     {date}")
                
                # Count by month
                monthly_counts = {}
                for date in dates_2024:
                    try:
                        month = date[:7]  # YYYY-MM
                        monthly_counts[month] = monthly_counts.get(month, 0) + 1
                    except:
                        continue
                
                print(f"   2024 monthly distribution:")
                for month in sorted(monthly_counts.keys()):
                    print(f"     {month}: {monthly_counts[month]} profiles")
            
            # Check October specifically
            oct_2024 = [date for date in all_dates if '2024-10' in date]
            print(f"\n   🎯 October 2024 data: {len(oct_2024)}")
            if oct_2024:
                print(f"     Examples: {oct_2024[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def simple_postgres_test():
    """Simple PostgreSQL test."""
    print(f"\n🔍 SIMPLE POSTGRESQL TEST")
    print("=" * 40)
    
    try:
        engine = create_engine(settings.database_url_sync)
        
        with engine.connect() as conn:
            # First, let's see what's in the profiles table
            print("📊 Profile table overview:")
            
            try:
                # Check if we have profile_date column
                count_query = "SELECT COUNT(*) FROM argo_profiles"
                total = conn.execute(text(count_query)).scalar()
                print(f"   Total profiles: {total:,}")
                
                # Try to get date range using profile_date
                date_query = """
                    SELECT MIN(profile_date) as earliest,
                           MAX(profile_date) as latest
                    FROM argo_profiles
                """
                date_result = conn.execute(text(date_query)).fetchone()
                print(f"   Date range: {date_result[0]} to {date_result[1]}")
                
                # Count by year using profile_date
                year_query = """
                    SELECT EXTRACT(YEAR FROM profile_date) as year,
                           COUNT(*) as count
                    FROM argo_profiles
                    WHERE profile_date IS NOT NULL
                    GROUP BY EXTRACT(YEAR FROM profile_date)
                    ORDER BY year
                """
                year_results = conn.execute(text(year_query)).fetchall()
                print(f"   Year distribution:")
                for year, count in year_results:
                    print(f"     {int(year)}: {count:,}")
                
                # Specific check for 2024 and October 2024
                count_2024 = conn.execute(text("""
                    SELECT COUNT(*) FROM argo_profiles 
                    WHERE EXTRACT(YEAR FROM profile_date) = 2024
                """)).scalar()
                print(f"\n   🎯 2024 profiles: {count_2024:,}")
                
                count_oct_2024 = conn.execute(text("""
                    SELECT COUNT(*) FROM argo_profiles 
                    WHERE EXTRACT(YEAR FROM profile_date) = 2024 
                    AND EXTRACT(MONTH FROM profile_date) = 10
                """)).scalar()
                print(f"   🎯 October 2024 profiles: {count_oct_2024:,}")
                
            except Exception as e:
                print(f"   ❌ Query error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")
        return False

def main():
    """Run simple tests."""
    print("🔍 SIMPLIFIED DATA QUERY TEST")
    print("=" * 60)
    print("Testing what users actually get when they query...")
    print()
    
    chromadb_ok = simple_chromadb_test()
    postgres_ok = simple_postgres_test()
    
    print(f"\n📊 KEY FINDINGS")
    print("=" * 30)
    print(f"ChromaDB Test: {'✅ OK' if chromadb_ok else '❌ FAILED'}")
    print(f"PostgreSQL Test: {'✅ OK' if postgres_ok else '❌ FAILED'}")
    
    print(f"\n💡 This test shows:")
    print("1. Whether ChromaDB semantic search returns 2024 data for user queries")
    print("2. Whether PostgreSQL actually has the data we expect")
    print("3. The specific gap between data storage and retrieval")

if __name__ == "__main__":
    main()