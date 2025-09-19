#!/usr/bin/env python3
"""
Re-examine ChromaDB with better sampling and analysis
Since the CSV was extracted from ChromaDB, we know 2024 data exists
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import chromadb
import pandas as pd
from datetime import datetime
import random

def better_chromadb_analysis():
    """Better analysis of ChromaDB contents."""
    print("🔍 CORRECTED CHROMADB ANALYSIS")
    print("=" * 60)
    
    try:
        client = chromadb.PersistentClient(path="./data/chromadb")
        collection = client.get_collection("argo_metadata")
        
        total_docs = collection.count()
        print(f"📊 Total documents: {total_docs:,}")
        
        # Instead of sequential sampling, try random sampling
        print(f"\n🎲 RANDOM SAMPLING ANALYSIS:")
        
        # Get multiple random samples
        sample_sizes = [1000, 5000, 10000]
        for sample_size in sample_sizes:
            if sample_size > total_docs:
                continue
                
            print(f"\n   Sample size: {sample_size:,}")
            
            # Generate random offsets
            max_offset = total_docs - sample_size
            random_offset = random.randint(0, max_offset) if max_offset > 0 else 0
            
            sample = collection.get(limit=sample_size, offset=random_offset)
            
            if sample['metadatas']:
                dates = [meta['date'] for meta in sample['metadatas']]
                dates_df = pd.to_datetime(dates)
                
                print(f"   Date range: {dates_df.min()} to {dates_df.max()}")
                
                # Check year distribution
                year_counts = dates_df.dt.year.value_counts().sort_index()
                print(f"   Years found: {list(year_counts.index)}")
                
                # Check 2024 data specifically
                data_2024 = dates_df[dates_df.dt.year == 2024]
                if len(data_2024) > 0:
                    print(f"   ✅ 2024 data: {len(data_2024)} profiles")
                    months_2024 = data_2024.dt.month.value_counts().sort_index()
                    print(f"   2024 months: {list(months_2024.index)}")
                    
                    # Check October specifically
                    oct_2024 = data_2024[data_2024.dt.month == 10]
                    if len(oct_2024) > 0:
                        print(f"   🎯 October 2024: {len(oct_2024)} profiles")
                        print(f"   Oct range: {oct_2024.min()} to {oct_2024.max()}")
                else:
                    print(f"   ❌ No 2024 data in this sample")
        
        # Try different offsets to find recent data
        print(f"\n🔍 SEARCHING DIFFERENT SECTIONS:")
        
        section_offsets = [0, total_docs//4, total_docs//2, 3*total_docs//4, total_docs-1000]
        for i, offset in enumerate(section_offsets):
            if offset >= total_docs:
                continue
                
            print(f"\n   Section {i+1} (offset {offset:,}):")
            
            sample = collection.get(limit=500, offset=offset)
            
            if sample['metadatas']:
                dates = [meta['date'] for meta in sample['metadatas']]
                dates_df = pd.to_datetime(dates)
                
                print(f"     Date range: {dates_df.min()} to {dates_df.max()}")
                
                # Check for 2024 data
                data_2024 = dates_df[dates_df.dt.year == 2024]
                if len(data_2024) > 0:
                    print(f"     ✅ Found 2024 data: {len(data_2024)} profiles")
                    
                    # Check October
                    oct_2024 = data_2024[data_2024.dt.month == 10]
                    if len(oct_2024) > 0:
                        print(f"     🎯 October 2024: {len(oct_2024)} profiles")
        
        # Try direct search for 2024 data
        print(f"\n🔍 DIRECT SEARCH FOR 2024 DATA:")
        
        # Search with semantic query
        try:
            results_2024 = collection.query(
                query_texts=["2024 oceanographic profile temperature salinity"],
                n_results=50
            )
            
            print(f"   Semantic search results: {len(results_2024['ids'][0])}")
            
            # Check dates in results
            if results_2024['metadatas'][0]:
                result_dates = [meta['date'] for meta in results_2024['metadatas'][0]]
                result_dates_df = pd.to_datetime(result_dates)
                
                print(f"   Date range: {result_dates_df.min()} to {result_dates_df.max()}")
                
                # Count 2024 results
                results_2024_data = result_dates_df[result_dates_df.dt.year == 2024]
                print(f"   2024 results: {len(results_2024_data)}")
                
                # Show sample results
                print(f"   Sample results:")
                for i in range(min(5, len(results_2024['metadatas'][0]))):
                    meta = results_2024['metadatas'][0][i]
                    print(f"     {meta['date']} - Float {meta['float_wmo_id']}")
        
        except Exception as e:
            print(f"   Search error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_csv_vs_chromadb():
    """Compare CSV data with what we find in ChromaDB."""
    print(f"\n📊 CSV vs CHROMADB COMPARISON")
    print("=" * 60)
    
    # Analyze the CSV file first
    try:
        csv_path = "data/exports/chroma_2024-07.csv"
        df = pd.read_csv(csv_path)
        
        print(f"📄 CSV File Analysis:")
        print(f"   Records: {len(df):,}")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"   Unique floats: {df['metadata.float_wmo_id'].nunique()}")
        
        # Get some specific profile IDs from the CSV
        sample_ids = df['id'].head(10).tolist()
        print(f"\n🔍 Sample profile IDs from CSV:")
        for i, profile_id in enumerate(sample_ids[:5]):
            row = df[df['id'] == profile_id].iloc[0]
            print(f"   {i+1}. {profile_id} - {row['date']} - Float {row['metadata.float_wmo_id']}")
        
        # Now try to find these same IDs in ChromaDB
        print(f"\n🔍 Searching for these IDs in ChromaDB:")
        
        client = chromadb.PersistentClient(path="./data/chromadb")
        collection = client.get_collection("argo_metadata")
        
        # Try to get documents by IDs
        try:
            chromadb_results = collection.get(ids=sample_ids[:5])
            
            if chromadb_results['ids']:
                print(f"   ✅ Found {len(chromadb_results['ids'])} documents in ChromaDB")
                
                for i, doc_id in enumerate(chromadb_results['ids']):
                    meta = chromadb_results['metadatas'][i]
                    print(f"     {doc_id} - {meta['date']} - Float {meta['float_wmo_id']}")
            else:
                print(f"   ❌ No documents found with these IDs")
                
        except Exception as e:
            print(f"   ❌ Error searching by ID: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ CSV analysis error: {e}")
        return False

def main():
    """Run corrected analysis."""
    print("🔧 CORRECTED CHROMADB ANALYSIS")
    print("=" * 70)
    print("Since CSV was extracted from ChromaDB, 2024 data must exist!")
    print()
    
    chromadb_ok = better_chromadb_analysis()
    csv_ok = analyze_csv_vs_chromadb()
    
    print(f"\n📊 CORRECTED FINDINGS")
    print("=" * 30)
    print(f"ChromaDB Analysis: {'✅ OK' if chromadb_ok else '❌ FAILED'}")
    print(f"CSV Comparison: {'✅ OK' if csv_ok else '❌ FAILED'}")
    
    print(f"\n💡 LIKELY ISSUES:")
    print("1. My initial sampling was biased toward early data")
    print("2. ChromaDB data might be ordered chronologically")
    print("3. Vector search algorithms might favor certain temporal ranges")
    print("4. Query processing might have semantic/embedding issues")

if __name__ == "__main__":
    main()