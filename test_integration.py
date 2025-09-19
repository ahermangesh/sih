"""
Test Enhanced RAG Integration in Main Server
Verifies that the enhanced RAG service is working through the live API
"""

import requests
import json
import time

def test_enhanced_rag_integration():
    """Test the enhanced RAG service through the live server API."""
    base_url = "http://localhost:8002"
    
    print("🧪 Testing Enhanced RAG Integration")
    print("=" * 60)
    
    # Test temporal queries that were previously failing
    temporal_queries = [
        "october 2024 data",
        "show me temperature data from october 2024",
        "what argo profiles do we have for 2024?",
    ]
    
    # Test semantic queries that should still work
    semantic_queries = [
        "what is argo data used for?",
        "explain oceanography principles"
    ]
    
    print("\n🕒 TESTING TEMPORAL QUERIES (should use PostgreSQL)")
    print("-" * 50)
    
    for i, query in enumerate(temporal_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        try:
            response = requests.post(
                f"{base_url}/api/v1/chat/query",
                json={
                    "message": query,
                    "conversation_id": f"test_temporal_{i}",
                    "language": "en"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Status: {response.status_code}")
                print(f"   📊 Confidence: {data.get('confidence', 'N/A')}")
                
                # Check if it's using enhanced RAG with temporal detection
                query_type = data.get('query_type', 'unknown')
                
                if query_type == 'temporal':
                    print(f"   🎯 Query type: {query_type} (Enhanced RAG working!)")
                else:
                    print(f"   ⚠️  Query type: {query_type} (may not be using enhanced RAG)")
                
                # Check response content
                response_text = data.get('message', '')
                if 'don\'t have access' in response_text.lower():
                    print(f"   ❌ Still getting 'don't have access' error")
                elif 'found' in response_text.lower() and '2024' in response_text:
                    print(f"   ✅ Response mentions finding 2024 data")
                
                print(f"   💬 Response: {response_text[:100]}...")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
        
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
        
        time.sleep(1)  # Rate limiting
    
    print("\n🔍 TESTING SEMANTIC QUERIES (should use ChromaDB)")
    print("-" * 50)
    
    for i, query in enumerate(semantic_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        try:
            response = requests.post(
                f"{base_url}/api/v1/chat/query",
                json={
                    "message": query,
                    "conversation_id": f"test_semantic_{i}",
                    "language": "en"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Status: {response.status_code}")
                print(f"   📊 Confidence: {data.get('confidence', 'N/A')}")
                
                query_type = data.get('query_type', 'unknown')
                print(f"   🎯 Query type: {query_type}")
                
                response_text = data.get('message', '')
                print(f"   💬 Response: {response_text[:100]}...")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("🎉 INTEGRATION TEST COMPLETE!")
    print("=" * 60)
    print("If temporal queries show 'temporal' query type and find 2024 data,")
    print("then the Enhanced RAG integration is working successfully!")

if __name__ == "__main__":
    test_enhanced_rag_integration()