"""
Test October 2024 Specific Query
Test the exact query that was causing the issue
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.services.enhanced_rag_service import EnhancedRAGPipeline


async def test_october_2024():
    """Test the specific October 2024 query that was failing."""
    print("Testing October 2024 specific query...")
    
    try:
        rag = EnhancedRAGPipeline()
        await rag.initialize()
        print("✓ Enhanced RAG pipeline initialized")
        
        # Test the exact query that was failing
        test_queries = [
            "october 2024 data",
            "show me data from october 2024",
            "what temperature data do we have for october 2024",
            "i want to see argo profiles from october 2024",
            "october 2024 temperature and salinity measurements"
        ]
        
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"TESTING: '{query}'")
            print('='*60)
            
            response = await rag.process_query(query)
            
            print(f"Confidence Score: {response.confidence_score}")
            print(f"Query Type: {response.generation_metadata.get('query_type', 'standard')}")
            
            if response.query_results:
                print(f"Results Found: {len(response.query_results)}")
                
                # Show sample data
                if response.query_results:
                    sample = response.query_results[0]
                    print("\nSample Profile:")
                    for key, value in sample.items():
                        if key in ['profile_date', 'wmo_id', 'latitude', 'longitude', 'min_temp', 'max_temp', 'min_salinity', 'max_salinity']:
                            print(f"  {key}: {value}")
            
            print(f"\nFull Response:")
            print(response.response)
            print()
    
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_october_2024())