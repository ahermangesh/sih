#!/usr/bin/env python3
"""
FloatChat - Comprehensive Test Scenarios
Based on FloatChat Professional Development Plan requirements.

This script tests 10 ideal user scenarios that demonstrate the complete
system capabilities as specified in the development plan.
"""

import asyncio
import time
import json
from typing import List, Dict, Any
from datetime import datetime
import requests
import sys
from pathlib import Path

# Add app to Python path
sys.path.append(str(Path(__file__).parent))

class FloatChatTester:
    """Comprehensive tester for FloatChat system."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    def test_scenario(self, scenario_id: str, query: str, expected_features: List[str], 
                     description: str) -> Dict[str, Any]:
        """Test a single scenario and validate results."""
        
        print(f"\n{'='*60}")
        print(f"🧪 SCENARIO {scenario_id}: {description}")
        print(f"{'='*60}")
        print(f"Query: {query}")
        
        start_time = time.time()
        
        try:
            # Make API request
            response = requests.post(
                f"{self.base_url}/api/v1/chat/query",
                json={
                    "message": query,
                    "conversation_id": f"test_{scenario_id}",
                    "language": "auto"
                },
                timeout=30
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                result = {
                    "scenario_id": scenario_id,
                    "query": query,
                    "description": description,
                    "response_time": response_time,
                    "response_length": len(data.get("message", "")),
                    "confidence": data.get("confidence", 0),
                    "contexts_retrieved": data.get("metadata", {}).get("contexts_retrieved", 0),
                    "processing_time": data.get("processing_time", 0),
                    "rag_used": data.get("metadata", {}).get("rag_used", False),
                    "response_preview": data.get("message", "")[:200] + "...",
                    "full_response": data.get("message", ""),
                    "expected_features": expected_features,
                    "success": True,
                    "validation_results": self._validate_response(data.get("message", ""), expected_features)
                }
                
                # Print results
                print(f"✅ SUCCESS")
                print(f"   Response Time: {response_time:.2f}s")
                print(f"   Processing Time: {data.get('processing_time', 0):.2f}s")
                print(f"   Confidence: {data.get('confidence', 0):.2f}")
                print(f"   Contexts Retrieved: {data.get('metadata', {}).get('contexts_retrieved', 0)}")
                print(f"   Response Length: {len(data.get('message', ''))} characters")
                print(f"   Response Preview: {data.get('message', '')[:200]}...")
                
                # Validate expected features
                validation = result["validation_results"]
                print(f"\n🔍 VALIDATION:")
                for feature, found in validation.items():
                    status = "✅" if found else "❌"
                    print(f"   {status} {feature}")
                
                validation_score = sum(validation.values()) / len(validation) * 100
                print(f"   📊 Validation Score: {validation_score:.1f}%")
                
            else:
                result = {
                    "scenario_id": scenario_id,
                    "query": query,
                    "description": description,
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response_time": response_time
                }
                print(f"❌ FAILED: HTTP {response.status_code}")
                print(f"   Error: {response.text}")
                
        except Exception as e:
            result = {
                "scenario_id": scenario_id,
                "query": query,
                "description": description,
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
            print(f"❌ FAILED: {str(e)}")
        
        self.results.append(result)
        return result
    
    def _validate_response(self, response: str, expected_features: List[str]) -> Dict[str, bool]:
        """Validate if response contains expected features."""
        validation = {}
        response_lower = response.lower()
        
        for feature in expected_features:
            if feature.lower() == "specific_data":
                # Check for specific measurements, coordinates, or dates
                has_numbers = any(char.isdigit() for char in response)
                has_coordinates = any(word in response_lower for word in ["latitude", "longitude", "°", "degrees"])
                has_measurements = any(word in response_lower for word in ["temperature", "salinity", "pressure", "°c"])
                validation[feature] = has_numbers and (has_coordinates or has_measurements)
                
            elif feature.lower() == "argo_references":
                # Check for ARGO float references
                validation[feature] = any(word in response_lower for word in ["argo", "float", "profile", "cycle"])
                
            elif feature.lower() == "location_context":
                # Check for geographical context
                validation[feature] = any(word in response_lower for word in ["ocean", "sea", "region", "area", "location", "latitude", "longitude"])
                
            elif feature.lower() == "temporal_context":
                # Check for time references
                validation[feature] = any(word in response_lower for word in ["date", "time", "2020", "2021", "2022", "2023", "2024", "2025", "recent"])
                
            elif feature.lower() == "scientific_accuracy":
                # Check for scientific terminology
                validation[feature] = any(word in response_lower for word in ["temperature", "salinity", "pressure", "depth", "measurement", "data"])
                
            elif feature.lower() == "contextual_explanation":
                # Check for explanatory content
                validation[feature] = len(response) > 100 and any(word in response_lower for word in ["based on", "according to", "data shows", "indicates"])
                
            else:
                # Generic keyword search
                validation[feature] = feature.lower() in response_lower
        
        return validation
    
    def run_all_scenarios(self):
        """Run all 10 ideal test scenarios."""
        
        print("🚀 FloatChat Comprehensive Testing Suite")
        print("Based on Professional Development Plan Requirements")
        print(f"Target URL: {self.base_url}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 10 Ideal Test Scenarios
        scenarios = [
            {
                "id": "01",
                "query": "Show me recent ocean temperature data from ARGO floats near India",
                "description": "Basic regional temperature query with recent data filter",
                "expected_features": ["specific_data", "argo_references", "location_context", "temporal_context", "temperature"]
            },
            {
                "id": "02", 
                "query": "What is the salinity profile in the Arabian Sea from ARGO measurements?",
                "description": "Specific ocean region with salinity parameter focus",
                "expected_features": ["salinity", "argo_references", "arabian sea", "profile", "specific_data"]
            },
            {
                "id": "03",
                "query": "Compare temperature and salinity data between Indian Ocean and Pacific Ocean from ARGO floats",
                "description": "Multi-region comparison query requiring data analysis",
                "expected_features": ["temperature", "salinity", "indian ocean", "pacific ocean", "comparison", "argo_references"]
            },
            {
                "id": "04",
                "query": "Find ARGO floats that recorded temperatures above 25°C in tropical regions during 2024",
                "description": "Complex query with temperature threshold, region, and temporal filters",
                "expected_features": ["temperature", "25", "tropical", "2024", "argo_references", "specific_data"]
            },
            {
                "id": "05",
                "query": "What are the deepest measurements from ARGO floats and what temperatures were recorded?",
                "description": "Depth-based query requiring analysis of pressure/depth data",
                "expected_features": ["depth", "pressure", "temperature", "deepest", "measurements", "argo_references"]
            },
            {
                "id": "06",
                "query": "Show me ARGO float trajectories and temperature changes in the Bay of Bengal",
                "description": "Trajectory analysis with temporal temperature changes",
                "expected_features": ["trajectory", "temperature", "bay of bengal", "changes", "argo_references", "location_context"]
            },
            {
                "id": "07",
                "query": "Which ARGO floats have been active in the monsoon season and what data did they collect?",
                "description": "Seasonal analysis requiring temporal and meteorological context",
                "expected_features": ["monsoon", "seasonal", "active", "data", "argo_references", "temporal_context"]
            },
            {
                "id": "08",
                "query": "Analyze ocean temperature trends from 2020 to 2024 using ARGO data",
                "description": "Multi-year trend analysis requiring historical data processing",
                "expected_features": ["trends", "2020", "2024", "temperature", "analysis", "argo_references", "temporal_context"]
            },
            {
                "id": "09",
                "query": "What is the relationship between ocean depth and temperature in equatorial regions?",
                "description": "Scientific correlation analysis between depth and temperature",
                "expected_features": ["depth", "temperature", "relationship", "equatorial", "correlation", "scientific_accuracy"]
            },
            {
                "id": "10",
                "query": "Provide a summary of ARGO float data quality and coverage in the Indian Ocean region",
                "description": "Data quality and coverage analysis for specific region",
                "expected_features": ["quality", "coverage", "indian ocean", "summary", "argo_references", "contextual_explanation"]
            }
        ]
        
        # Run all scenarios
        for scenario in scenarios:
            self.test_scenario(
                scenario["id"],
                scenario["query"], 
                scenario["expected_features"],
                scenario["description"]
            )
            
            # Brief pause between tests
            time.sleep(1)
        
        # Generate summary report
        self.generate_summary_report()
    
    def generate_summary_report(self):
        """Generate comprehensive test summary report."""
        
        print(f"\n{'='*80}")
        print("📊 FLOATCHAT TESTING SUMMARY REPORT")
        print(f"{'='*80}")
        
        successful_tests = [r for r in self.results if r.get("success", False)]
        failed_tests = [r for r in self.results if not r.get("success", False)]
        
        print(f"Total Tests: {len(self.results)}")
        print(f"✅ Successful: {len(successful_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        print(f"📈 Success Rate: {len(successful_tests)/len(self.results)*100:.1f}%")
        
        if successful_tests:
            avg_response_time = sum(r.get("response_time", 0) for r in successful_tests) / len(successful_tests)
            avg_processing_time = sum(r.get("processing_time", 0) for r in successful_tests) / len(successful_tests)
            avg_confidence = sum(r.get("confidence", 0) for r in successful_tests) / len(successful_tests)
            avg_contexts = sum(r.get("contexts_retrieved", 0) for r in successful_tests) / len(successful_tests)
            
            print(f"\n🚀 PERFORMANCE METRICS:")
            print(f"   Average Response Time: {avg_response_time:.2f}s")
            print(f"   Average Processing Time: {avg_processing_time:.2f}s") 
            print(f"   Average Confidence: {avg_confidence:.2f}")
            print(f"   Average Contexts Retrieved: {avg_contexts:.1f}")
            
            # Performance targets from plan
            print(f"\n🎯 TARGET COMPLIANCE:")
            response_target = 3.0  # Plan target: <3 seconds
            confidence_target = 0.90  # Plan target: >90% accuracy
            
            print(f"   Response Time Target (<3s): {'✅' if avg_response_time < response_target else '❌'} {avg_response_time:.2f}s")
            print(f"   Confidence Target (>90%): {'✅' if avg_confidence > confidence_target else '❌'} {avg_confidence*100:.1f}%")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['scenario_id']}: {test.get('error', 'Unknown error')}")
        
        # Validation analysis
        if successful_tests:
            print(f"\n🔍 VALIDATION ANALYSIS:")
            all_validations = {}
            for test in successful_tests:
                if "validation_results" in test:
                    for feature, result in test["validation_results"].items():
                        if feature not in all_validations:
                            all_validations[feature] = []
                        all_validations[feature].append(result)
            
            for feature, results in all_validations.items():
                success_rate = sum(results) / len(results) * 100
                status = "✅" if success_rate > 80 else "⚠️" if success_rate > 60 else "❌"
                print(f"   {status} {feature}: {success_rate:.1f}%")
        
        print(f"\n💾 Detailed results saved to: floatchat_test_results.json")
        
        # Save detailed results
        with open("floatchat_test_results.json", "w") as f:
            json.dump({
                "test_summary": {
                    "total_tests": len(self.results),
                    "successful_tests": len(successful_tests),
                    "failed_tests": len(failed_tests),
                    "success_rate": len(successful_tests)/len(self.results)*100,
                    "timestamp": datetime.now().isoformat()
                },
                "detailed_results": self.results
            }, f, indent=2)


def main():
    """Main function to run comprehensive testing."""
    print("🧪 Starting FloatChat Comprehensive Testing")
    
    tester = FloatChatTester()
    tester.run_all_scenarios()
    
    print("\n🎉 Testing completed!")
    print("Review the detailed results in floatchat_test_results.json")


if __name__ == "__main__":
    main()
