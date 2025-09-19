"""
Test Enhanced RAG Service with Temporal Queries
Tests the new temporal query routing functionality
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.services.enhanced_rag_service import EnhancedRAGPipeline, TemporalQueryDetector, PostgreSQLQueryExecutor


async def test_temporal_detection():
    """Test temporal query detection."""
    print("Testing Temporal Query Detection...")
    
    detector = TemporalQueryDetector()
    
    test_queries = [
        ("Show me October 2024 temperature data", True),
        ("What's the salinity in 2023?", True),
        ("Recent ARGO float deployments", True),
        ("Current oceanographic conditions", True),
        ("What is ARGO data about?", False),
        ("Explain oceanography principles", False),
        ("January 2021 profiles in Arabian Sea", True),
        ("2024-10 data from Bay of Bengal", True),
    ]
    
    for query, expected in test_queries:
        result = detector.is_temporal_query(query)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{query}' -> {result} (expected {expected})")
        
        if result:
            temporal_info = detector.extract_temporal_info(query)
            print(f"    Temporal info: {temporal_info}")
        print()


async def test_postgresql_queries():
    """Test PostgreSQL temporal queries."""
    print("Testing PostgreSQL Temporal Queries...")
    
    executor = PostgreSQLQueryExecutor()
    detector = TemporalQueryDetector()
    
    test_queries = [
        "Show me October 2024 temperature data from ARGO floats",
        "What profiles do we have for 2024?",
        "Recent temperature measurements in the Arabian Sea"
    ]
    
    try:
        await executor.initialize()
        print("✓ PostgreSQL connection initialized")
        
        for query in test_queries:
            print(f"\nTesting: '{query}'")
            temporal_info = detector.extract_temporal_info(query)
            print(f"Temporal info: {temporal_info}")
            
            results = await executor.execute_temporal_query(query, temporal_info)
            print(f"Results count: {len(results)}")
            
            if results:
                print("Sample result:")
                sample = results[0]
                for key, value in list(sample.items())[:5]:  # Show first 5 fields
                    print(f"  {key}: {value}")
                if len(sample) > 5:
                    print(f"  ... and {len(sample) - 5} more fields")
            print()
    
    except Exception as e:
        print(f"✗ PostgreSQL test failed: {e}")


async def test_enhanced_rag():
    """Test the complete enhanced RAG pipeline."""
    print("Testing Enhanced RAG Pipeline...")
    
    try:
        rag = EnhancedRAGPipeline()
        await rag.initialize()
        print("✓ Enhanced RAG pipeline initialized")
        
        test_queries = [
            "Show me temperature data from October 2024",
            "What ARGO profiles do we have for 2024?",
            "What is ARGO data used for?",  # Non-temporal
            "Recent salinity measurements in Indian Ocean"
        ]
        
        for query in test_queries:
            print(f"\n--- Testing: '{query}' ---")
            response = await rag.process_query(query)
            
            print(f"Confidence: {response.confidence_score}")
            print(f"Query type: {response.generation_metadata.get('query_type', 'standard')}")
            print(f"Response: {response.response[:200]}...")
            
            if response.query_results:
                print(f"Result count: {len(response.query_results)}")
            
            print()
    
    except Exception as e:
        print(f"✗ Enhanced RAG test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("ENHANCED RAG SERVICE TESTING")
    print("=" * 60)
    
    await test_temporal_detection()
    print("-" * 60)
    
    await test_postgresql_queries()
    print("-" * 60)
    
    await test_enhanced_rag()
    
    print("=" * 60)
    print("Testing completed!")


if __name__ == "__main__":
    asyncio.run(main())