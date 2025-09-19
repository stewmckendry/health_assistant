#!/usr/bin/env python3
"""
Test the Emergency Triage API endpoint.
Tests /api/agents/triage with various clinical scenarios.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any
import httpx
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


# Test cases with expected outcomes
TEST_CASES = [
    {
        "name": "STEMI Presentation",
        "request": {
            "age": 65,
            "sex": "Male",
            "chief_complaint": "Crushing chest pain",
            "history": "Sudden onset crushing chest pain radiating to left arm, started 30 minutes ago while at rest. Associated with shortness of breath and diaphoresis.",
            "vitals": {
                "blood_pressure": "150/95",
                "heart_rate": 110,
                "respiratory_rate": 24,
                "temperature": 36.8,
                "oxygen_saturation": 94,
                "pain_scale": 9
            },
            "symptoms": ["Chest pain", "Shortness of breath", "Sweating", "Nausea"],
            "medical_history": ["Hypertension", "Type 2 Diabetes", "Former smoker"],
            "medications": ["Metoprolol", "Metformin"],
            "allergies": []
        },
        "expected_ctas": [1, 2],  # Should be CTAS 1 or 2
        "expected_urgency": ["Resuscitation", "Emergent"]
    },
    {
        "name": "Anaphylaxis",
        "request": {
            "age": 30,
            "sex": "Female",
            "chief_complaint": "Difficulty breathing after bee sting",
            "history": "Stung by bee 10 minutes ago, rapidly developing facial swelling and difficulty breathing",
            "vitals": {
                "blood_pressure": "85/60",
                "heart_rate": 130,
                "respiratory_rate": 28,
                "temperature": 36.7,
                "oxygen_saturation": 91
            },
            "symptoms": ["Stridor", "Facial swelling", "Hives", "Difficulty breathing"],
            "medical_history": ["Known bee sting allergy"],
            "medications": ["EpiPen (not yet administered)"],
            "allergies": ["Bee stings"]
        },
        "expected_ctas": [1],  # Should be CTAS 1
        "expected_urgency": ["Resuscitation"]
    },
    {
        "name": "Stroke Symptoms",
        "request": {
            "age": 72,
            "sex": "Female",
            "chief_complaint": "Sudden weakness and slurred speech",
            "history": "Sudden onset left-sided weakness and slurred speech started 45 minutes ago. Unable to lift left arm.",
            "vitals": {
                "blood_pressure": "180/110",
                "heart_rate": 88,
                "respiratory_rate": 18,
                "temperature": 36.9,
                "oxygen_saturation": 96
            },
            "symptoms": ["Left-sided weakness", "Slurred speech", "Facial droop", "Confusion"],
            "medical_history": ["Atrial fibrillation", "Hypertension"],
            "medications": ["Warfarin", "Metoprolol"],
            "allergies": []
        },
        "expected_ctas": [1, 2],  # Should be CTAS 1 or 2
        "expected_urgency": ["Resuscitation", "Emergent"]
    },
    {
        "name": "Severe Asthma Exacerbation",
        "request": {
            "age": 18,
            "sex": "Male",
            "chief_complaint": "Can't breathe, wheezing severely",
            "history": "Known asthmatic, progressive dyspnea over past hour despite using rescue inhaler 5 times. Unable to speak in full sentences.",
            "vitals": {
                "blood_pressure": "140/90",
                "heart_rate": 125,
                "respiratory_rate": 32,
                "temperature": 37.0,
                "oxygen_saturation": 88,
                "pain_scale": 6
            },
            "symptoms": ["Severe wheezing", "Unable to speak full sentences", "Using accessory muscles", "Cyanosis"],
            "medical_history": ["Asthma", "Previous ICU admission for asthma"],
            "medications": ["Albuterol", "Flovent", "Prednisone"],
            "allergies": []
        },
        "expected_ctas": [1, 2],  # Should be CTAS 1 or 2
        "expected_urgency": ["Resuscitation", "Emergent"]
    },
    {
        "name": "Moderate Asthma",
        "request": {
            "age": 25,
            "sex": "Male",
            "chief_complaint": "Worsening asthma",
            "history": "Known asthmatic with increasing shortness of breath over 2 days. Using rescue inhaler more frequently.",
            "vitals": {
                "blood_pressure": "125/80",
                "heart_rate": 95,
                "respiratory_rate": 22,
                "temperature": 37.0,
                "oxygen_saturation": 93,
                "pain_scale": 3
            },
            "symptoms": ["Wheezing", "Shortness of breath", "Chest tightness"],
            "medical_history": ["Asthma"],
            "medications": ["Albuterol inhaler", "Flovent"],
            "allergies": []
        },
        "expected_ctas": [3],  # Should be CTAS 3
        "expected_urgency": ["Urgent"]
    },
    {
        "name": "UTI Symptoms",
        "request": {
            "age": 35,
            "sex": "Female",
            "chief_complaint": "Burning with urination",
            "history": "3 days of burning with urination and urinary frequency. No fever or back pain.",
            "vitals": {
                "blood_pressure": "118/76",
                "heart_rate": 78,
                "respiratory_rate": 16,
                "temperature": 37.2,
                "oxygen_saturation": 98,
                "pain_scale": 4
            },
            "symptoms": ["Dysuria", "Urinary frequency", "Mild lower abdominal discomfort"],
            "medical_history": ["Previous UTIs"],
            "medications": ["Oral contraceptive"],
            "allergies": ["Sulfa drugs"]
        },
        "expected_ctas": [4],  # Should be CTAS 4
        "expected_urgency": ["Less Urgent", "Non-Urgent"]
    },
    {
        "name": "Appendicitis Concern",
        "request": {
            "age": 22,
            "sex": "Male",
            "chief_complaint": "Severe abdominal pain",
            "history": "Started as periumbilical pain 12 hours ago, now localized to right lower quadrant. Associated with nausea, vomiting, and low-grade fever.",
            "vitals": {
                "blood_pressure": "128/82",
                "heart_rate": 102,
                "respiratory_rate": 20,
                "temperature": 38.2,
                "oxygen_saturation": 97,
                "pain_scale": 7
            },
            "symptoms": ["RLQ pain", "Nausea", "Vomiting", "Fever", "Rebound tenderness"],
            "medical_history": [],
            "medications": [],
            "allergies": []
        },
        "expected_ctas": [2, 3],  # Should be CTAS 2 or 3
        "expected_urgency": ["Emergent", "Urgent"]
    },
    {
        "name": "Diabetic Ketoacidosis",
        "request": {
            "age": 28,
            "sex": "Female",
            "chief_complaint": "Vomiting and confusion",
            "history": "Type 1 diabetic, ran out of insulin 3 days ago. Increasing thirst, frequent urination, now vomiting and confused.",
            "vitals": {
                "blood_pressure": "95/60",
                "heart_rate": 118,
                "respiratory_rate": 26,
                "temperature": 37.8,
                "oxygen_saturation": 98,
                "pain_scale": 5
            },
            "symptoms": ["Vomiting", "Confusion", "Kussmaul breathing", "Fruity breath odor", "Dehydration"],
            "medical_history": ["Type 1 Diabetes"],
            "medications": ["Insulin (ran out)"],
            "allergies": []
        },
        "expected_ctas": [1, 2],  # Should be CTAS 1 or 2
        "expected_urgency": ["Resuscitation", "Emergent"]
    }
]


async def test_api_endpoint():
    """Test the /api/agents/triage endpoint."""
    print("\n" + "="*60)
    print("Testing Emergency Triage API Endpoint")
    print("="*60)
    
    # Start the API server first
    print("\nStarting FastAPI server...")
    print("Make sure the server is running: python -m uvicorn src.web.api.main:app --reload")
    print("Waiting 3 seconds for server to be ready...")
    await asyncio.sleep(3)
    
    # Base URL for API
    base_url = "http://localhost:8001"
    endpoint = f"{base_url}/api/agents/triage"
    
    results_summary = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check if server is running
        try:
            response = await client.get(f"{base_url}/health")
            print(f"✓ Server health check: {response.status_code}")
        except httpx.ConnectError:
            print("❌ ERROR: Cannot connect to server. Please run:")
            print("   python -m uvicorn src.web.api.main:app --reload")
            return
        
        for i, test_case in enumerate(TEST_CASES, 1):
            print(f"\nTest Case {i}: {test_case['name']}")
            print("-" * 40)
            
            try:
                # Add session ID to request
                request_data = test_case["request"].copy()
                request_data["session_id"] = f"test_api_{i}"
                
                # Send POST request
                start_time = datetime.now()
                response = await client.post(endpoint, json=request_data)
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Display results
                    print(f"✓ Response received in {response_time:.2f}s")
                    print(f"✓ CTAS Level: {result['ctas_level']}")
                    print(f"✓ Urgency: {result['urgency']}")
                    print(f"✓ Confidence: {result['confidence']:.2f}")
                    print(f"✓ Red Flags: {len(result['red_flags'])} identified")
                    if result['red_flags']:
                        print(f"  - {', '.join(result['red_flags'][:3])}")
                    print(f"✓ Wait Time: {result['estimated_wait_time']}")
                    print(f"✓ Disposition: {result['disposition']}")
                    
                    # Validate against expected
                    ctas_correct = result['ctas_level'] in test_case['expected_ctas']
                    urgency_correct = result['urgency'] in test_case['expected_urgency']
                    
                    if ctas_correct and urgency_correct:
                        print(f"✅ Assessment correct (CTAS: {test_case['expected_ctas']}, Urgency: {test_case['expected_urgency']})")
                        results_summary.append({
                            "case": test_case['name'],
                            "result": "PASS",
                            "ctas": result['ctas_level'],
                            "time": response_time
                        })
                    else:
                        print(f"⚠️  Assessment mismatch:")
                        if not ctas_correct:
                            print(f"   - CTAS: Expected {test_case['expected_ctas']}, Got {result['ctas_level']}")
                        if not urgency_correct:
                            print(f"   - Urgency: Expected {test_case['expected_urgency']}, Got {result['urgency']}")
                        results_summary.append({
                            "case": test_case['name'],
                            "result": "FAIL",
                            "ctas": result['ctas_level'],
                            "time": response_time
                        })
                    
                    # Check response time requirement
                    if response_time > 5.0:
                        print(f"⚠️  Response time exceeded 5 seconds ({response_time:.2f}s)")
                    
                else:
                    print(f"❌ Error: HTTP {response.status_code}")
                    print(f"   Response: {response.text}")
                    results_summary.append({
                        "case": test_case['name'],
                        "result": "ERROR",
                        "error": f"HTTP {response.status_code}"
                    })
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                results_summary.append({
                    "case": test_case['name'],
                    "result": "ERROR",
                    "error": str(e)
                })
    
    # Print summary
    print("\n" + "="*60)
    print("API ENDPOINT TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results_summary if r["result"] == "PASS")
    failed = sum(1 for r in results_summary if r["result"] == "FAIL")
    errors = sum(1 for r in results_summary if r["result"] == "ERROR")
    
    print(f"\nTotal Tests: {len(TEST_CASES)}")
    print(f"✅ Passed: {passed}")
    print(f"⚠️  Failed: {failed}")
    print(f"❌ Errors: {errors}")
    
    # Calculate average response time
    times = [r["time"] for r in results_summary if "time" in r]
    if times:
        avg_time = sum(times) / len(times)
        max_time = max(times)
        print(f"\nResponse Times:")
        print(f"  Average: {avg_time:.2f}s")
        print(f"  Maximum: {max_time:.2f}s")
        print(f"  Requirement: <5s {'✅ PASS' if max_time < 5 else '❌ FAIL'}")
    
    # Check accuracy requirement (8/10 = 80%)
    accuracy = passed / len(TEST_CASES) * 100
    print(f"\nAccuracy: {passed}/{len(TEST_CASES)} = {accuracy:.1f}%")
    print(f"Requirement: 80% (8/10) {'✅ PASS' if accuracy >= 80 else '❌ FAIL'}")
    
    if passed >= 7 and max_time < 5:  # 7/8 = 87.5% > 80%
        print("\n🎉 API endpoint testing SUCCESSFUL! Meets all requirements.")
    else:
        print("\n⚠️  API endpoint needs improvement to meet requirements.")
    
    print("\n" + "-"*40)
    for result in results_summary:
        status_icon = "✅" if result["result"] == "PASS" else "⚠️" if result["result"] == "FAIL" else "❌"
        details = f"CTAS {result.get('ctas', 'N/A')}, {result.get('time', 0):.2f}s" if result["result"] != "ERROR" else result.get('error', '')[:50]
        print(f"{status_icon} {result['case']}: {result['result']} - {details}")


async def main():
    """Run API endpoint tests."""
    await test_api_endpoint()
    
    print("\n" + "="*60)
    print("Next step: Create simple web UI for testing")
    print("Run: python scripts/create_test_ui.py")


if __name__ == "__main__":
    asyncio.run(main())