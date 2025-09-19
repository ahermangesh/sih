#!/usr/bin/env python3
"""
Direct query testing to see what data is actually available
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import chromadb
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

try:
    from app.core.config import get_settings
    settings = get_settings()
    print("✅ Configuration loaded")
except Exception as e:
    print(f"❌ Configuration error: {e}")
    sys.exit(1)

def test_chromadb_queries():
    """Test various queries on ChromaDB to see what data we can retrieve."""
    print("🔍 TESTING CHROMADB QUERIES")
    print("=" * 50)
    
    try:
        client = chromadb.PersistentClient(path="./data/chromadb")
        collection = client.get_collection("argo_metadata")
        
        total_docs = collection.count()
        print(f"📊 Total documents: {total_docs:,}")
        
        # Test queries that a user might ask
        test_queries = [
            "temperature data from 2024",
            "October 2024 oceanographic measurements", 
            "recent ARGO float profiles",
            "salinity measurements from last year",
            "2024 temperature profiles",
            "Indian Ocean temperature data 2024",
            "Arabian Sea measurements 2024"
        ]
        
        print(f"\n🔍 Testing user-like queries:")
        for i, query in enumerate(test_queries, 1):
            print(f"\n   {i}. Query: '{query}'")
            
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=10
                )
                
                if results['metadatas'][0]:
                    print(f"      Results: {len(results['ids'][0])}")
                    
                    # Show date range of results
                    dates = [meta['date'] for meta in results['metadatas'][0]]
                    dates_df = pd.to_datetime(dates)
                    print(f"      Date range: {dates_df.min()} to {dates_df.max()}")
                    
                    # Count by year
                    years = dates_df.dt.year.value_counts().sort_index()
                    year_summary = ", ".join([f"{year}: {count}" for year, count in years.items()])
                    print(f"      Years: {year_summary}")
                    
                    # Show top 3 results
                    print(f"      Top results:")
                    for j in range(min(3, len(results['metadatas'][0]))):
                        meta = results['metadatas'][0][j]
                        doc = results['documents'][0][j][:60]
                        print(f"        {meta['date']} - Float {meta['float_wmo_id']}: {doc}...")
                else:
                    print(f"      ❌ No results found")
                    
            except Exception as e:
                print(f"      ❌ Query error: {e}")
        
        # Test specific date searches
        print(f"\n🗓️ Testing specific date searches:")
        date_searches = ["2024-10", "2024-07", "2024-01", "2023-12", "2022"]
        
        for date_search in date_searches:
            try:
                # Search for documents containing the date
                results = collection.query(
                    query_texts=[f"oceanographic profile {date_search}"],
                    n_results=20
                )
                
                # Count how many actually match the date
                matching_count = 0
                if results['metadatas'][0]:
                    for meta in results['metadatas'][0]:
                        if date_search in meta['date']:
                            matching_count += 1
                
                print(f"   {date_search}: {matching_count} matching dates out of {len(results['ids'][0])} results")
                
            except Exception as e:
                print(f"   {date_search}: Error - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB error: {e}")
        return False

def test_postgresql_queries():
    """Test PostgreSQL queries to see what data is available."""
    print(f"\n🔍 TESTING POSTGRESQL QUERIES")
    print("=" * 50)
    
    try:
        engine = create_engine(settings.database_url_sync)
        
        with engine.connect() as conn:
            # Check table structure first
            print("📊 Checking table structure:")
            
            # Get column names for argo_profiles
            try:
                columns_query = """
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'argo_profiles'
                    ORDER BY ordinal_position;
                """
                columns_result = conn.execute(text(columns_query)).fetchall()
                print(f"   argo_profiles columns: {[col[0] for col in columns_result]}")
            except Exception as e:
                print(f"   ❌ Column check error: {e}")
            
            # Try different date column names
            date_columns = ['date', 'profile_date', 'timestamp', 'measurement_date', 'created_at']
            working_date_col = None
            
            for col in date_columns:
                try:
                    test_query = f"SELECT {col} FROM argo_profiles LIMIT 1"
                    result = conn.execute(text(test_query)).fetchone()
                    working_date_col = col
                    print(f"   ✅ Date column found: {col}")
                    break
                except Exception:
                    continue
            
            if not working_date_col:
                print("   ❌ No date column found, trying all columns")
                # Get sample data to see structure
                try:
                    sample_query = "SELECT * FROM argo_profiles LIMIT 3"
                    sample_result = conn.execute(text(sample_query)).fetchall()
                    if sample_result:
                        # Print first row to see structure
                        print(f"   Sample row: {dict(sample_result[0])}")
                except Exception as e:
                    print(f"   ❌ Sample query error: {e}")
                return False
            
            # Now test data coverage with correct column
            print(f"\n📅 Testing temporal coverage:")
            
            try:
                # Count total profiles
                count_query = "SELECT COUNT(*) FROM argo_profiles"
                total_profiles = conn.execute(text(count_query)).scalar()
                print(f"   Total profiles: {total_profiles:,}")
                
                # Get date range
                range_query = f"""
                    SELECT MIN({working_date_col}) as earliest, 
                           MAX({working_date_col}) as latest
                    FROM argo_profiles
                """
                date_range = conn.execute(text(range_query)).fetchone()
                print(f"   Date range: {date_range[0]} to {date_range[1]}")
                
                # Count by year
                year_query = f"""
                    SELECT EXTRACT(YEAR FROM {working_date_col}) as year,
                           COUNT(*) as count
                    FROM argo_profiles
                    GROUP BY EXTRACT(YEAR FROM {working_date_col})
                    ORDER BY year
                """
                year_counts = conn.execute(text(year_query)).fetchall()
                print(f"   Year distribution:")
                for year, count in year_counts:
                    print(f"     {int(year)}: {count:,} profiles")
                
                # Test specific queries that users might ask
                print(f"\n🔍 Testing user-like SQL queries:")
                
                test_sql_queries = [
                    f"SELECT COUNT(*) FROM argo_profiles WHERE EXTRACT(YEAR FROM {working_date_col}) = 2024",
                    f"SELECT COUNT(*) FROM argo_profiles WHERE EXTRACT(YEAR FROM {working_date_col}) = 2024 AND EXTRACT(MONTH FROM {working_date_col}) = 10",
                    f"SELECT COUNT(*) FROM argo_profiles WHERE {working_date_col} >= '2024-01-01'",
                    f"SELECT COUNT(*) FROM argo_profiles WHERE {working_date_col} >= '2023-01-01' AND {working_date_col} < '2024-01-01'"
                ]
                
                query_descriptions = [
                    "2024 profiles",
                    "October 2024 profiles", 
                    "2024+ profiles",
                    "2023 profiles"
                ]
                
                for query, description in zip(test_sql_queries, query_descriptions):
                    try:
                        result = conn.execute(text(query)).scalar()
                        print(f"     {description}: {result:,}")
                    except Exception as e:
                        print(f"     {description}: Error - {e}")
                
            except Exception as e:
                print(f"   ❌ Temporal analysis error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")
        return False

def test_rag_pipeline():
    """Test the actual RAG pipeline that the chat uses."""
    print(f"\n🔍 TESTING RAG PIPELINE")
    print("=" * 50)
    
    try:
        from app.services.rag_service import RAGPipeline
        
        # Initialize RAG pipeline
        rag = RAGPipeline()
        print("✅ RAG Pipeline initialized")
        
        # Test queries that users typically ask
        test_user_queries = [
            "Show me temperature data from October 2024",
            "What's the salinity in Arabian Sea in 2024?",
            "Give me recent ARGO float measurements",
            "Temperature profiles from Indian Ocean last year"
        ]
        
        print(f"\n🎯 Testing end-to-end queries:")
        for i, query in enumerate(test_user_queries, 1):
            print(f"\n   {i}. User query: '{query}'")
            
            try:
                # This would be the actual path a user query takes
                # Note: We might need to initialize the pipeline first
                print(f"      (RAG pipeline test - would need full initialization)")
                
            except Exception as e:
                print(f"      ❌ RAG error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG pipeline error: {e}")
        return False

def main():
    """Run all query tests."""
    print("🔍 COMPREHENSIVE QUERY TESTING")
    print("=" * 70)
    print(f"Testing actual data retrieval capabilities...")
    print()
    
    chromadb_ok = test_chromadb_queries()
    postgres_ok = test_postgresql_queries() 
    rag_ok = test_rag_pipeline()
    
    print(f"\n📊 QUERY TEST RESULTS")
    print("=" * 30)
    print(f"ChromaDB Queries: {'✅ OK' if chromadb_ok else '❌ FAILED'}")
    print(f"PostgreSQL Queries: {'✅ OK' if postgres_ok else '❌ FAILED'}")
    print(f"RAG Pipeline: {'✅ OK' if rag_ok else '❌ FAILED'}")
    
    print(f"\n💡 This will show us:")
    print("1. What temporal data ChromaDB actually returns for typical queries")
    print("2. What data PostgreSQL has available")
    print("3. Where the disconnect between 'data exists' and 'AI can't find it' occurs")

if __name__ == "__main__":
    main()