#!/usr/bin/env python3
"""
FloatChat - Real-World User Scenario Testing

Test the system against the 10 real-world user queries from different user types:
Scientists, Policy Makers, Fisheries, Educators, Environmental Researchers, 
Journalists, Maritime Industry, Students, Climate NGOs, and General Public.
"""

import asyncio
import time
import json
import requests
from typing import List, Dict, Any
from datetime import datetime

class RealWorldTester:
    """Test FloatChat against real-world user scenarios."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        
    def test_real_world_scenarios(self):
        """Test all 10 real-world user scenarios."""
        
        print("🌊 FloatChat Real-World User Scenario Testing")
        print("=" * 60)
        print("Testing against actual user queries from different sectors")
        print(f"Target URL: {self.base_url}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Real-world scenarios from different user types
        scenarios = [
            {
                "id": "scientist_01",
                "user_type": "Scientist/Researcher",
                "query": "Show me the salinity profile at 10°N, 65°E in March 2023",
                "expected_elements": [
                    "salinity", "profile", "depth", "coordinates", "march 2023", 
                    "specific_measurements", "scientific_data"
                ],
                "ideal_response_type": "Map + Graph + Scientific Summary"
            },
            {
                "id": "policy_02", 
                "user_type": "Policy Maker",
                "query": "Compare average sea temperature in Bay of Bengal vs Arabian Sea between 2021-2023",
                "expected_elements": [
                    "temperature", "bay of bengal", "arabian sea", "comparison", 
                    "2021", "2023", "average", "trends"
                ],
                "ideal_response_type": "Comparative Analysis + Regional Data"
            },
            {
                "id": "fisheries_03",
                "user_type": "Fisheries Sector/NGO", 
                "query": "Show oxygen levels in the Arabian Sea in the last 6 months",
                "expected_elements": [
                    "oxygen", "arabian sea", "recent", "levels", "hypoxic", "6 months"
                ],
                "ideal_response_type": "Environmental Risk Assessment"
            },
            {
                "id": "educator_04",
                "user_type": "Educator/Student",
                "query": "Where are the ARGO floats currently operating in the Indian Ocean?",
                "expected_elements": [
                    "argo", "floats", "indian ocean", "locations", "operating", "active"
                ],
                "ideal_response_type": "Educational Map + Float Status"
            },
            {
                "id": "environmental_05",
                "user_type": "Environmental Researcher", 
                "query": "What are the seasonal variations of salinity near the equator from 2020-2025?",
                "expected_elements": [
                    "seasonal", "salinity", "equator", "variations", "2020", "2025", "monsoon"
                ],
                "ideal_response_type": "Seasonal Analysis + Climate Patterns"
            },
            {
                "id": "journalist_06",
                "user_type": "Journalist",
                "query": "Is there evidence of ocean warming in the Indian Ocean from 2020 to 2025?",
                "expected_elements": [
                    "warming", "evidence", "indian ocean", "2020", "2025", "temperature", "trend"
                ],
                "ideal_response_type": "Climate Story + Data Evidence"
            },
            {
                "id": "maritime_07", 
                "user_type": "Maritime Industry",
                "query": "What are the nearest floats to Sri Lanka right now?",
                "expected_elements": [
                    "nearest", "floats", "sri lanka", "distance", "current", "location"
                ],
                "ideal_response_type": "Operational Data + Proximity Info"
            },
            {
                "id": "student_08",
                "user_type": "Student",
                "query": "Can you explain what an ARGO float measures and how it works?",
                "expected_elements": [
                    "argo", "float", "measures", "temperature", "salinity", "depth", "explanation"
                ],
                "ideal_response_type": "Educational Explanation + Simple Language"
            },
            {
                "id": "climate_ngo_09",
                "user_type": "Climate NGO",
                "query": "Generate a report of ocean heat content in Indian Ocean from 2020-2025",
                "expected_elements": [
                    "report", "heat content", "indian ocean", "2020", "2025", "analysis"
                ],
                "ideal_response_type": "Comprehensive Report + Policy Insights"
            },
            {
                "id": "general_public_10",
                "user_type": "General Public/School Kid", 
                "query": "Show me a fun fact about the ocean near India",
                "expected_elements": [
                    "fun fact", "india", "ocean", "interesting", "simple", "educational"
                ],
                "ideal_response_type": "Engaging Explanation + Simple Visualization"
            }
        ]
        
        # Run all scenarios
        for i, scenario in enumerate(scenarios, 1):
            self._test_scenario(i, scenario)
            time.sleep(1)  # Brief pause between tests
        
        # Generate comprehensive report
        self._generate_real_world_report()
    
    def _test_scenario(self, scenario_num: int, scenario: Dict[str, Any]):
        """Test a single real-world scenario."""
        
        print(f"\n{'='*70}")
        print(f"🎯 SCENARIO {scenario_num}: {scenario['user_type']}")
        print(f"{'='*70}")
        print(f"Query: {scenario['query']}")
        print(f"Expected Response Type: {scenario['ideal_response_type']}")
        
        start_time = time.time()
        
        try:
            # Make API request
            response = requests.post(
                f"{self.base_url}/api/v1/chat/query",
                json={
                    "message": scenario['query'],
                    "conversation_id": f"realworld_{scenario['id']}",
                    "language": "auto"
                },
                timeout=45  # Longer timeout for complex queries
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get("message", "")
                
                # Analyze response quality
                analysis = self._analyze_response_quality(
                    response_text, 
                    scenario['expected_elements'],
                    scenario['user_type']
                )
                
                result = {
                    "scenario_num": scenario_num,
                    "user_type": scenario['user_type'],
                    "query": scenario['query'],
                    "response_time": response_time,
                    "response_length": len(response_text),
                    "confidence": data.get("confidence", 0),
                    "contexts_retrieved": data.get("metadata", {}).get("contexts_retrieved", 0),
                    "response_preview": response_text[:300] + "...",
                    "full_response": response_text,
                    "expected_elements": scenario['expected_elements'],
                    "ideal_response_type": scenario['ideal_response_type'],
                    "quality_analysis": analysis,
                    "success": True
                }
                
                # Print results
                print(f"✅ SUCCESS")
                print(f"   Response Time: {response_time:.2f}s")
                print(f"   Confidence: {data.get('confidence', 0):.2f}")
                print(f"   Response Length: {len(response_text)} characters")
                print(f"   Response Preview: {response_text[:200]}...")
                
                # Quality analysis
                print(f"\n🔍 QUALITY ANALYSIS:")
                print(f"   📊 Element Coverage: {analysis['element_coverage']:.1f}%")
                print(f"   🎯 User Appropriateness: {analysis['user_appropriateness']:.1f}%")
                print(f"   📈 Scientific Accuracy: {analysis['scientific_accuracy']:.1f}%")
                print(f"   🌟 Overall Quality: {analysis['overall_quality']:.1f}%")
                
                # Missing elements
                if analysis['missing_elements']:
                    print(f"   ⚠️  Missing Elements: {', '.join(analysis['missing_elements'])}")
                
            else:
                result = {
                    "scenario_num": scenario_num,
                    "user_type": scenario['user_type'],
                    "query": scenario['query'],
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "response_time": response_time
                }
                print(f"❌ FAILED: HTTP {response.status_code}")
                
        except Exception as e:
            result = {
                "scenario_num": scenario_num,
                "user_type": scenario['user_type'], 
                "query": scenario['query'],
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
            print(f"❌ FAILED: {str(e)}")
        
        self.results.append(result)
    
    def _analyze_response_quality(self, response: str, expected_elements: List[str], user_type: str) -> Dict[str, Any]:
        """Analyze response quality for real-world scenarios."""
        
        response_lower = response.lower()
        
        # Check element coverage
        found_elements = []
        missing_elements = []
        
        for element in expected_elements:
            element_lower = element.lower().replace('_', ' ')
            
            if element_lower == "specific measurements":
                # Check for numbers and units
                has_numbers = any(char.isdigit() for char in response)
                has_units = any(unit in response_lower for unit in ['°c', 'psu', 'ml/l', 'meters', 'km'])
                found = has_numbers and has_units
            elif element_lower == "scientific data":
                # Check for scientific terminology
                found = any(term in response_lower for term in ['data', 'measurement', 'profile', 'analysis'])
            else:
                # Direct keyword search
                found = element_lower in response_lower
            
            if found:
                found_elements.append(element)
            else:
                missing_elements.append(element)
        
        element_coverage = len(found_elements) / len(expected_elements) * 100
        
        # User appropriateness scoring
        user_appropriateness = self._score_user_appropriateness(response_lower, user_type)
        
        # Scientific accuracy scoring
        scientific_accuracy = self._score_scientific_accuracy(response_lower)
        
        # Overall quality score
        overall_quality = (element_coverage + user_appropriateness + scientific_accuracy) / 3
        
        return {
            "element_coverage": element_coverage,
            "user_appropriateness": user_appropriateness,
            "scientific_accuracy": scientific_accuracy,
            "overall_quality": overall_quality,
            "found_elements": found_elements,
            "missing_elements": missing_elements
        }
    
    def _score_user_appropriateness(self, response: str, user_type: str) -> float:
        """Score how well the response is tailored to the user type."""
        
        score = 50.0  # Base score
        
        if "scientist" in user_type.lower() or "researcher" in user_type.lower():
            # Should have technical language
            if any(term in response for term in ['analysis', 'data', 'measurement', 'profile']):
                score += 25
            if any(term in response for term in ['psu', '°c', 'depth', 'stratification']):
                score += 25
                
        elif "policy" in user_type.lower() or "ngo" in user_type.lower():
            # Should have comparative and trend language
            if any(term in response for term in ['trend', 'increase', 'decrease', 'comparison']):
                score += 25
            if any(term in response for term in ['average', 'significant', 'indicates']):
                score += 25
                
        elif "student" in user_type.lower() or "educator" in user_type.lower():
            # Should have explanatory language
            if any(term in response for term in ['explain', 'understand', 'learn', 'educational']):
                score += 25
            if len(response) > 200:  # Detailed explanation
                score += 25
                
        elif "general public" in user_type.lower() or "kid" in user_type.lower():
            # Should have simple, engaging language
            if any(term in response for term in ['fun fact', 'interesting', 'did you know']):
                score += 25
            if any(term in response for term in ['simple', 'easy', 'fascinating']):
                score += 25
        
        return min(score, 100.0)
    
    def _score_scientific_accuracy(self, response: str) -> float:
        """Score scientific accuracy and terminology usage."""
        
        score = 60.0  # Base score
        
        # Positive indicators
        scientific_terms = [
            'temperature', 'salinity', 'pressure', 'depth', 'argo', 'float', 
            'profile', 'measurement', 'data', 'analysis', 'ocean', 'sea'
        ]
        
        for term in scientific_terms:
            if term in response:
                score += 3
        
        # Units and measurements
        if any(unit in response for unit in ['°c', 'psu', 'ml/l', 'meters', 'km']):
            score += 10
        
        # Specific data references
        if any(char.isdigit() for char in response):
            score += 10
        
        return min(score, 100.0)
    
    def _generate_real_world_report(self):
        """Generate comprehensive real-world testing report."""
        
        print(f"\n{'='*80}")
        print("📊 REAL-WORLD USER SCENARIO TESTING REPORT")
        print(f"{'='*80}")
        
        successful_tests = [r for r in self.results if r.get("success", False)]
        failed_tests = [r for r in self.results if not r.get("success", False)]
        
        print(f"Total Scenarios Tested: {len(self.results)}")
        print(f"✅ Successful: {len(successful_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        print(f"📈 Success Rate: {len(successful_tests)/len(self.results)*100:.1f}%")
        
        if successful_tests:
            # Performance metrics
            avg_response_time = sum(r.get("response_time", 0) for r in successful_tests) / len(successful_tests)
            avg_confidence = sum(r.get("confidence", 0) for r in successful_tests) / len(successful_tests)
            
            # Quality metrics
            avg_element_coverage = sum(r.get("quality_analysis", {}).get("element_coverage", 0) for r in successful_tests) / len(successful_tests)
            avg_user_appropriateness = sum(r.get("quality_analysis", {}).get("user_appropriateness", 0) for r in successful_tests) / len(successful_tests)
            avg_scientific_accuracy = sum(r.get("quality_analysis", {}).get("scientific_accuracy", 0) for r in successful_tests) / len(successful_tests)
            avg_overall_quality = sum(r.get("quality_analysis", {}).get("overall_quality", 0) for r in successful_tests) / len(successful_tests)
            
            print(f"\n🚀 PERFORMANCE METRICS:")
            print(f"   Average Response Time: {avg_response_time:.2f}s")
            print(f"   Average Confidence: {avg_confidence:.2f}")
            
            print(f"\n🎯 QUALITY METRICS:")
            print(f"   Element Coverage: {avg_element_coverage:.1f}%")
            print(f"   User Appropriateness: {avg_user_appropriateness:.1f}%")
            print(f"   Scientific Accuracy: {avg_scientific_accuracy:.1f}%")
            print(f"   Overall Quality Score: {avg_overall_quality:.1f}%")
            
            # User type analysis
            print(f"\n👥 USER TYPE PERFORMANCE:")
            user_types = {}
            for test in successful_tests:
                user_type = test.get("user_type", "Unknown")
                if user_type not in user_types:
                    user_types[user_type] = []
                user_types[user_type].append(test.get("quality_analysis", {}).get("overall_quality", 0))
            
            for user_type, scores in user_types.items():
                avg_score = sum(scores) / len(scores) if scores else 0
                status = "✅" if avg_score > 75 else "⚠️" if avg_score > 60 else "❌"
                print(f"   {status} {user_type}: {avg_score:.1f}%")
        
        if failed_tests:
            print(f"\n❌ FAILED SCENARIOS:")
            for test in failed_tests:
                print(f"   • {test['user_type']}: {test.get('error', 'Unknown error')}")
        
        # Save detailed results
        with open("real_world_test_results.json", "w") as f:
            json.dump({
                "test_summary": {
                    "total_scenarios": len(self.results),
                    "successful": len(successful_tests),
                    "failed": len(failed_tests),
                    "success_rate": len(successful_tests)/len(self.results)*100,
                    "timestamp": datetime.now().isoformat()
                },
                "detailed_results": self.results
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: real_world_test_results.json")


def main():
    """Main function to run real-world scenario testing."""
    print("🌊 Starting FloatChat Real-World User Scenario Testing")
    
    tester = RealWorldTester()
    tester.test_real_world_scenarios()
    
    print("\n🎉 Real-world testing completed!")
    print("This validates FloatChat against actual user needs from different sectors.")


if __name__ == "__main__":
    main()
