#!/usr/bin/env python3
"""
Test the Emergency Triage Orchestrator that combines all specialist agents.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from src.agents.clinical.orchestrator import create_triage_orchestrator, run_triage_assessment


# Test cases with expected outcomes
TEST_CASES = [
    {
        "name": "STEMI Presentation",
        "patient_data": {
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
        "should_have_red_flags": True
    },
    {
        "name": "Anaphylaxis",
        "patient_data": {
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
        "should_have_red_flags": True
    },
    {
        "name": "Stroke Symptoms",
        "patient_data": {
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
        "should_have_red_flags": True
    },
    {
        "name": "Moderate Asthma",
        "patient_data": {
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
        "should_have_red_flags": False
    },
    {
        "name": "UTI Symptoms",
        "patient_data": {
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
        "should_have_red_flags": False
    }
]


async def test_orchestrator():
    """Test the orchestrator with various patient scenarios."""
    print("\n" + "="*60)
    print("Testing Emergency Triage Orchestrator")
    print("="*60)
    
    orchestrator = create_triage_orchestrator()
    
    results_summary = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\nTest Case {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Run the orchestrator
            result = await run_triage_assessment(
                test_case["patient_data"],
                session_id=f"test_{i}",
                langfuse_enabled=False  # Disable for testing
            )
            
            # Display results
            print(f"✓ Final CTAS Level: {result.final_ctas_level}")
            print(f"✓ Urgency: {result.urgency}")
            print(f"✓ Confidence: {result.confidence:.2f}")
            print(f"✓ Red Flags: {len(result.red_flags_identified)} identified")
            if result.red_flags_identified:
                print(f"  - {', '.join(result.red_flags_identified[:3])}")
            print(f"✓ Initial Actions: {', '.join(result.initial_actions[:3])}")
            print(f"✓ Recommended Tests: {', '.join(result.recommended_tests[:3])}")
            print(f"✓ Wait Time: {result.estimated_wait_time}")
            print(f"✓ Disposition: {result.disposition}")
            
            # Validate against expected
            if result.final_ctas_level in test_case["expected_ctas"]:
                print(f"✅ CTAS level correct (Expected: {test_case['expected_ctas']}, Got: {result.final_ctas_level})")
                results_summary.append({"case": test_case["name"], "result": "PASS", "ctas": result.final_ctas_level})
            else:
                print(f"⚠️  CTAS level mismatch (Expected: {test_case['expected_ctas']}, Got: {result.final_ctas_level})")
                results_summary.append({"case": test_case["name"], "result": "FAIL", "ctas": result.final_ctas_level})
            
            if test_case["should_have_red_flags"] == (len(result.red_flags_identified) > 0):
                print(f"✅ Red flag detection correct")
            else:
                print(f"⚠️  Red flag detection mismatch")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results_summary.append({"case": test_case["name"], "result": "ERROR", "error": str(e)})
    
    # Print summary
    print("\n" + "="*60)
    print("ORCHESTRATOR TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results_summary if r["result"] == "PASS")
    failed = sum(1 for r in results_summary if r["result"] == "FAIL")
    errors = sum(1 for r in results_summary if r["result"] == "ERROR")
    
    print(f"\nTotal Tests: {len(TEST_CASES)}")
    print(f"✅ Passed: {passed}")
    print(f"⚠️  Failed: {failed}")
    print(f"❌ Errors: {errors}")
    print(f"\nAccuracy: {passed}/{len(TEST_CASES)} = {passed/len(TEST_CASES)*100:.1f}%")
    
    if passed >= 4:  # 80% accuracy threshold
        print("\n🎉 Orchestrator testing SUCCESSFUL! Meets accuracy requirements.")
    else:
        print("\n⚠️  Orchestrator needs improvement to meet accuracy requirements.")
    
    print("\n" + "-"*40)
    for result in results_summary:
        status_icon = "✅" if result["result"] == "PASS" else "⚠️" if result["result"] == "FAIL" else "❌"
        details = f"CTAS {result.get('ctas', 'N/A')}" if result["result"] != "ERROR" else result.get('error', '')[:50]
        print(f"{status_icon} {result['case']}: {result['result']} - {details}")


async def main():
    """Run orchestrator tests."""
    await test_orchestrator()
    
    print("\n" + "="*60)
    print("Next step: Create and test the FastAPI endpoint")
    print("Run: python scripts/test_api_endpoint.py")


if __name__ == "__main__":
    asyncio.run(main())