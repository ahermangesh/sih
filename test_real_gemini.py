"""
Test Real Gemini AI Integration
Verify that our Gemini API key works and we can get real AI responses.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_real_gemini():
    """Test real Gemini AI integration."""
    print("🤖 TESTING REAL GEMINI AI INTEGRATION")
    print("=====================================")
    
    try:
        # Import our real Gemini service
        from app.services.real_gemini_service import real_gemini_service
        
        print(f"✅ Gemini service imported successfully")
        print(f"✅ API available: {real_gemini_service.available}")
        
        if not real_gemini_service.available:
            print("❌ Gemini API not available - check your API key")
            return
        
        # Test a simple ocean data query
        test_query = "What is the average temperature in the Arabian Sea?"
        print(f"\n🌊 Testing query: '{test_query}'")
        
        response = await real_gemini_service.analyze_ocean_query(test_query)
        
        print(f"✅ AI Response received!")
        print(f"📝 Message: {response['message'][:200]}...")
        print(f"🎯 Query type: {response.get('query_type', 'N/A')}")
        print(f"📊 Confidence: {response.get('confidence', 'N/A')}")
        print(f"⏰ Timestamp: {response.get('timestamp', 'N/A')}")
        
        print("\n🎉 REAL GEMINI AI WORKING!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Gemini AI: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_real_argo_data():
    """Test real ARGO data fetching."""
    print("\n🌊 TESTING REAL ARGO DATA INTEGRATION")
    print("=====================================")
    
    try:
        from app.services.real_argo_service import real_argo_service
        
        print("✅ ARGO service imported successfully")
        
        # Test fetching active floats
        print("🔍 Fetching active ARGO floats...")
        floats = await real_argo_service.fetch_active_floats()
        
        print(f"✅ Found {len(floats)} active floats")
        if floats:
            print(f"📍 Sample float: WMO {floats[0].get('wmo_id', 'N/A')} - {floats[0].get('platform_type', 'N/A')}")
        
        print("\n🎉 REAL ARGO DATA WORKING!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing ARGO data: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("🚀 FLOATCHAT REAL INTEGRATION TESTS")
    print("===================================")
    
    gemini_ok = await test_real_gemini()
    argo_ok = await test_real_argo_data()
    
    print(f"\n📋 TEST RESULTS:")
    print(f"🤖 Gemini AI: {'✅ WORKING' if gemini_ok else '❌ FAILED'}")
    print(f"🌊 ARGO Data: {'✅ WORKING' if argo_ok else '❌ FAILED'}")
    
    if gemini_ok and argo_ok:
        print(f"\n🎉 ALL SYSTEMS GO! READY FOR REAL FLOATCHAT!")
    else:
        print(f"\n⚠️ Some systems need fixing before launch")

if __name__ == "__main__":
    asyncio.run(main())
