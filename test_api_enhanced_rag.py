"""
Test Enhanced RAG Service via API
Test the temporal query fixing through the actual API endpoint
"""

import requests
import json
import time

def test_api_queries():
    """Test the enhanced RAG service via API."""
    base_url = "http://localhost:8001"
    
    # Test queries that were failing before
    test_queries = [
        "october 2024 data",
        "show me temperature data from october 2024", 
        "what argo profiles do we have for 2024?",
        "recent salinity measurements",
        "what is argo data used for?"  # Non-temporal for comparison
    ]
    
    print("Testing Enhanced RAG Service via API")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        print("-" * 40)
        
        try:
            # Send request to chat API with correct schema
            response = requests.post(
                f"{base_url}/api/v1/chat/query",
                json={
                    "message": query,
                    "conversation_id": f"test_enhanced_rag_{i}",
                    "language": "en"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Status: {response.status_code}")
                print(f"Response: {data.get('response', 'No response')[:200]}...")
                
                if 'metadata' in data:
                    metadata = data['metadata']
                    print(f"Query Type: {metadata.get('query_type', 'standard')}")
                    print(f"Confidence: {metadata.get('confidence_score', 'N/A')}")
                    
                    if 'temporal_info' in metadata:
                        print(f"Temporal Info: {metadata['temporal_info']}")
                    
                    if 'postgres_results_count' in metadata:
                        print(f"PostgreSQL Results: {metadata['postgres_results_count']}")
            else:
                print(f"✗ Error: {response.status_code}")
                print(f"Response: {response.text}")
        
        except requests.exceptions.RequestException as e:
            print(f"✗ Request failed: {e}")
        
        # Small delay between requests
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("API Testing completed!")

if __name__ == "__main__":
    test_api_queries()