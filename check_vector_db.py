#!/usr/bin/env python3
"""
Check Vector Database and PostgreSQL Contents
Verify what data is actually available for the LLM to fetch.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import chromadb
from chromadb.config import Settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pandas as pd
import json

try:
    from app.core.config import get_settings
    from app.models.database_simple import ArgoFloat, ArgoProfile, ArgoMeasurement
    settings = get_settings()
    print("✅ Configuration loaded successfully")
except Exception as e:
    print(f"❌ Configuration error: {e}")
    sys.exit(1)

def check_chromadb():
    """Check ChromaDB collections and contents."""
    print("\n🔍 CHECKING CHROMADB VECTOR DATABASE")
    print("=" * 50)
    
    try:
        # Connect to ChromaDB
        client = chromadb.PersistentClient(path="./data/chromadb")
        print("✅ Connected to ChromaDB")
        
        # List all collections
        collections = client.list_collections()
        print(f"📁 Found {len(collections)} collections:")
        
        for collection in collections:
            print(f"\n📊 Collection: {collection.name}")
            print(f"   ID: {collection.id}")
            print(f"   Metadata: {collection.metadata}")
            
            # Get collection details
            col = client.get_collection(collection.name)
            count = col.count()
            print(f"   Document Count: {count}")
            
            if count > 0:
                # Get sample documents
                sample = col.peek(limit=5)
                print(f"   Sample Documents: {len(sample['ids'])}")
                
                # Show sample metadata
                if sample['metadatas']:
                    print("   Sample Metadata:")
                    for i, metadata in enumerate(sample['metadatas'][:3]):
                        print(f"     Doc {i+1}: {metadata}")
                
                # Check for temporal coverage
                if sample['metadatas']:
                    dates = []
                    for meta in sample['metadatas']:
                        if 'date' in meta:
                            dates.append(meta['date'])
                        elif 'timestamp' in meta:
                            dates.append(meta['timestamp'])
                    
                    if dates:
                        print(f"   Sample dates: {dates[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB error: {e}")
        return False

def check_postgresql():
    """Check PostgreSQL database contents."""
    print("\n🔍 CHECKING POSTGRESQL DATABASE")
    print("=" * 50)
    
    try:
        # Connect to PostgreSQL
        engine = create_engine(settings.database_url_sync)
        
        with engine.connect() as conn:
            print("✅ Connected to PostgreSQL")
            
            # Check tables
            tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """
            tables = conn.execute(text(tables_query)).fetchall()
            print(f"📁 Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table[0]}")
            
            # Check ARGO data stats
            print("\n📊 ARGO DATA STATISTICS:")
            
            # Floats
            try:
                floats_query = """
                    SELECT COUNT(*) as total_floats,
                           MIN(deployment_date) as earliest_date,
                           MAX(deployment_date) as latest_date
                    FROM argo_floats;
                """
                result = conn.execute(text(floats_query)).fetchone()
                print(f"   🔘 Floats: {result[0]}")
                print(f"   📅 Date range: {result[1]} to {result[2]}")
            except Exception as e:
                print(f"   ❌ Floats query error: {e}")
            
            # Profiles
            try:
                profiles_query = """
                    SELECT COUNT(*) as total_profiles,
                           MIN(date) as earliest_profile,
                           MAX(date) as latest_profile,
                           COUNT(DISTINCT EXTRACT(YEAR FROM date)) as years_covered
                    FROM argo_profiles;
                """
                result = conn.execute(text(profiles_query)).fetchone()
                print(f"   🔘 Profiles: {result[0]}")
                print(f"   📅 Profile range: {result[1]} to {result[2]}")
                print(f"   📊 Years covered: {result[3]}")
            except Exception as e:
                print(f"   ❌ Profiles query error: {e}")
            
            # Check October 2024 specifically
            try:
                oct_2024_query = """
                    SELECT COUNT(*) as oct_2024_profiles
                    FROM argo_profiles 
                    WHERE EXTRACT(YEAR FROM date) = 2024 
                    AND EXTRACT(MONTH FROM date) = 10;
                """
                result = conn.execute(text(oct_2024_query)).fetchone()
                print(f"   🔘 October 2024 profiles: {result[0]}")
            except Exception as e:
                print(f"   ❌ October 2024 query error: {e}")
            
            # Measurements
            try:
                measurements_query = """
                    SELECT COUNT(*) as total_measurements
                    FROM argo_measurements;
                """
                result = conn.execute(text(measurements_query)).fetchone()
                print(f"   🔘 Measurements: {result[0]}")
            except Exception as e:
                print(f"   ❌ Measurements query error: {e}")
            
            # Check temporal distribution
            try:
                temporal_query = """
                    SELECT EXTRACT(YEAR FROM date) as year,
                           EXTRACT(MONTH FROM date) as month,
                           COUNT(*) as profile_count
                    FROM argo_profiles
                    WHERE date >= '2020-01-01'
                    GROUP BY EXTRACT(YEAR FROM date), EXTRACT(MONTH FROM date)
                    ORDER BY year, month;
                """
                results = conn.execute(text(temporal_query)).fetchall()
                print(f"\n📊 TEMPORAL DISTRIBUTION (2020+):")
                
                # Group by year
                year_data = {}
                for row in results:
                    year = int(row[0])
                    month = int(row[1])
                    count = row[2]
                    
                    if year not in year_data:
                        year_data[year] = {}
                    year_data[year][month] = count
                
                # Show summary by year
                for year in sorted(year_data.keys()):
                    months = len(year_data[year])
                    total = sum(year_data[year].values())
                    print(f"   {year}: {total} profiles across {months} months")
                    
                    # Check if October 2024 specifically
                    if year == 2024 and 10 in year_data[year]:
                        print(f"      🎯 October 2024: {year_data[year][10]} profiles")
                
            except Exception as e:
                print(f"   ❌ Temporal distribution query error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")
        return False

def check_rag_pipeline():
    """Check if RAG pipeline configuration looks correct."""
    print("\n🔍 CHECKING RAG PIPELINE CONFIGURATION")
    print("=" * 50)
    
    try:
        from app.services.rag_service import RAGPipeline, VectorStore
        
        # Check vector store settings
        print("📋 Vector Store Configuration:")
        print(f"   ChromaDB path: ./data/chromadb")
        print(f"   Collection name: {settings.chromadb_collection_name}")
        
        # Try to initialize (without full setup)
        vector_store = VectorStore()
        print("✅ Vector store class loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG pipeline error: {e}")
        return False

def main():
    """Main function to run all checks."""
    print("🔍 VECTOR DATABASE AND DATA VERIFICATION")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    
    # Run all checks
    chromadb_ok = check_chromadb()
    postgres_ok = check_postgresql()
    rag_ok = check_rag_pipeline()
    
    print("\n📊 SUMMARY")
    print("=" * 30)
    print(f"ChromaDB: {'✅ OK' if chromadb_ok else '❌ FAILED'}")
    print(f"PostgreSQL: {'✅ OK' if postgres_ok else '❌ FAILED'}")
    print(f"RAG Pipeline: {'✅ OK' if rag_ok else '❌ FAILED'}")
    
    if chromadb_ok and postgres_ok:
        print("\n🎉 Both databases are accessible!")
        print("💡 If the AI still says 'no access', the issue might be:")
        print("   1. RAG pipeline not properly connecting to ChromaDB")
        print("   2. Query processing not finding relevant embeddings")
        print("   3. Vector embeddings not covering all temporal ranges")
        print("   4. API endpoint not properly routing to vector search")
    else:
        print("\n⚠️ Database issues detected!")

if __name__ == "__main__":
    main()