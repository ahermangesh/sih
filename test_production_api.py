#!/usr/bin/env python3
"""
Test script for FloatChat production API
"""
import requests
import json
import time
import sys

def test_floatchat_api():
    """Test the FloatChat production API endpoints."""
    
    base_url = "http://localhost:8000"
    
    print("🌊 Testing FloatChat Production API")
    print("=" * 50)
    
    tests = []
    
    # Test 1: Health Check
    try:
        print("1. Testing Health Check...")
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Health check passed: {health_data}")
            tests.append(("Health Check", True, health_data))
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            tests.append(("Health Check", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        tests.append(("Health Check", False, str(e)))
    
    # Test 2: Root endpoint
    try:
        print("2. Testing Root Endpoint...")
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            root_data = response.json()
            print(f"   ✅ Root endpoint passed: {root_data.get('message', 'No message')}")
            tests.append(("Root Endpoint", True, root_data))
        else:
            print(f"   ❌ Root endpoint failed: {response.status_code}")
            tests.append(("Root Endpoint", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ Root endpoint error: {e}")
        tests.append(("Root Endpoint", False, str(e)))
    
    # Test 3: API Documentation
    try:
        print("3. Testing API Documentation...")
        response = requests.get(f"{base_url}/docs", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ API docs available")
            tests.append(("API Docs", True, "Available"))
        else:
            print(f"   ❌ API docs failed: {response.status_code}")
            tests.append(("API Docs", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ API docs error: {e}")
        tests.append(("API Docs", False, str(e)))
    
    # Test 4: Real Chat API (simple test)
    try:
        print("4. Testing Real Chat API...")
        chat_data = {
            "message": "Hello, what is ocean temperature?",
            "conversation_id": "test-001"
        }
        response = requests.post(f"{base_url}/api/v1/chat/query", 
                               json=chat_data, timeout=30)
        if response.status_code == 200:
            chat_response = response.json()
            print(f"   ✅ Chat API responded: {chat_response.get('message', 'No message')[:100]}...")
            tests.append(("Chat API", True, chat_response))
        else:
            print(f"   ❌ Chat API failed: {response.status_code}")
            tests.append(("Chat API", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ Chat API error: {e}")
        tests.append(("Chat API", False, str(e)))
    
    # Test 5: ARGO Floats endpoint
    try:
        print("5. Testing ARGO Floats API...")
        response = requests.get(f"{base_url}/api/v1/floats?limit=5", timeout=15)
        if response.status_code == 200:
            floats_data = response.json()
            print(f"   ✅ Floats API responded with data")
            tests.append(("Floats API", True, floats_data))
        else:
            print(f"   ❌ Floats API failed: {response.status_code}")
            tests.append(("Floats API", False, f"Status: {response.status_code}"))
    except Exception as e:
        print(f"   ❌ Floats API error: {e}")
        tests.append(("Floats API", False, str(e)))
    
    # Summary
    print("\n" + "=" * 50)
    print("🧪 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success, _ in tests if success)
    total = len(tests)
    
    for test_name, success, result in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! FloatChat production API is working!")
        return True
    else:
        print("⚠️  Some tests failed. Check the details above.")
        return False

if __name__ == "__main__":
    success = test_floatchat_api()
    sys.exit(0 if success else 1)