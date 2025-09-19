#!/usr/bin/env python3
"""
Test individual clinical agents separately to ensure each works correctly.
Tests: Red Flag Detector, Triage Assessor, Workup Suggester
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

from agents import Agent, Runner
from src.agents.clinical.triage_assessor import create_triage_assessor
from src.agents.clinical.red_flag_detector import create_red_flag_detector
from src.agents.clinical.workup_suggester import create_workup_suggester


# Test cases
TEST_CASES = [
    {
        "name": "Chest Pain - High Risk",
        "data": """
        DEMOGRAPHICS: Age: 65, Sex: Male
        CHIEF COMPLAINT: Crushing chest pain
        HISTORY OF PRESENT ILLNESS: Sudden onset crushing chest pain radiating to left arm, started 30 minutes ago while at rest. Associated with shortness of breath and diaphoresis.
        VITAL SIGNS: BP: 150/95, HR: 110, RR: 24, Temp: 36.8°C, SpO2: 94%
        SYMPTOMS: Chest pain, shortness of breath, sweating, nausea
        PAST MEDICAL HISTORY: Hypertension, Type 2 Diabetes, Former smoker
        CURRENT MEDICATIONS: Metoprolol, Metformin
        ALLERGIES: None
        """,
        "expected": {
            "ctas_level": 1,  # Should be 1 or 2
            "has_red_flags": True,
            "critical_level": "CRITICAL"
        }
    },
    {
        "name": "Minor Laceration",
        "data": """
        DEMOGRAPHICS: Age: 25, Sex: Female
        CHIEF COMPLAINT: Cut on finger
        HISTORY OF PRESENT ILLNESS: Accidentally cut finger while cooking 2 hours ago. Bleeding controlled with pressure, wound approximately 2cm.
        VITAL SIGNS: BP: 118/78, HR: 72, RR: 16, Temp: 36.9°C, SpO2: 99%
        SYMPTOMS: Minor pain at wound site
        PAST MEDICAL HISTORY: None
        CURRENT MEDICATIONS: None
        ALLERGIES: Penicillin
        """,
        "expected": {
            "ctas_level": 4,  # Should be 4 or 5
            "has_red_flags": False,
            "critical_level": "LOW"
        }
    },
    {
        "name": "Pediatric Fever",
        "data": """
        DEMOGRAPHICS: Age: 2, Sex: Male
        CHIEF COMPLAINT: High fever and lethargy
        HISTORY OF PRESENT ILLNESS: 2-year-old with fever for 2 days, now lethargic and not drinking fluids. Parents very concerned.
        VITAL SIGNS: BP: 90/60, HR: 160, RR: 40, Temp: 40.2°C, SpO2: 95%
        SYMPTOMS: Fever, lethargy, poor oral intake, irritability
        PAST MEDICAL HISTORY: None
        CURRENT MEDICATIONS: Acetaminophen
        ALLERGIES: None
        """,
        "expected": {
            "ctas_level": 2,  # Should be 2 or 3
            "has_red_flags": True,
            "critical_level": "HIGH"
        }
    }
]


async def test_red_flag_detector():
    """Test the Red Flag Detector agent."""
    print("\n" + "="*60)
    print("Testing Red Flag Detector Agent")
    print("="*60)
    
    agent = create_red_flag_detector()
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\nTest Case {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            result = await Runner.run(
                agent,
                input=test_case["data"],
                max_turns=1
            )
            
            output = result.final_output
            print(f"✓ Has Red Flags: {output.has_red_flags}")
            print(f"✓ Critical Level: {output.critical_level}")
            print(f"✓ Red Flags Found: {output.red_flags[:3] if output.red_flags else 'None'}")
            print(f"✓ Time-Sensitive: {output.time_sensitive_conditions[:2] if output.time_sensitive_conditions else 'None'}")
            
            # Validate against expected
            if test_case["expected"]["has_red_flags"] == output.has_red_flags:
                print(f"✅ Red flag detection matches expected")
            else:
                print(f"⚠️  Red flag mismatch - Expected: {test_case['expected']['has_red_flags']}, Got: {output.has_red_flags}")
                
        except Exception as e:
            print(f"❌ Error: {e}")


async def test_triage_assessor():
    """Test the CTAS Triage Assessor agent."""
    print("\n" + "="*60)
    print("Testing CTAS Triage Assessor Agent")
    print("="*60)
    
    agent = create_triage_assessor()
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\nTest Case {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            result = await Runner.run(
                agent,
                input=test_case["data"],
                max_turns=1
            )
            
            output = result.final_output
            print(f"✓ CTAS Level: {output.ctas_level}")
            print(f"✓ Urgency: {output.urgency}")
            print(f"✓ Confidence: {output.confidence:.2f}")
            print(f"✓ Key Factors: {output.key_factors[:3] if output.key_factors else 'None'}")
            print(f"✓ Reasoning: {output.reasoning[:100]}...")
            
            # Validate against expected (allowing ±1 level variance)
            expected_level = test_case["expected"]["ctas_level"]
            if abs(output.ctas_level - expected_level) <= 1:
                print(f"✅ CTAS level within acceptable range (Expected: {expected_level}, Got: {output.ctas_level})")
            else:
                print(f"⚠️  CTAS level outside range - Expected: {expected_level}, Got: {output.ctas_level}")
                
        except Exception as e:
            print(f"❌ Error: {e}")


async def test_workup_suggester():
    """Test the Initial Workup Suggester agent."""
    print("\n" + "="*60)
    print("Testing Initial Workup Suggester Agent")
    print("="*60)
    
    agent = create_workup_suggester()
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\nTest Case {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Add CTAS level to input for context
            enhanced_input = test_case["data"] + f"\nAssigned CTAS Level: {test_case['expected']['ctas_level']}"
            
            result = await Runner.run(
                agent,
                input=enhanced_input,
                max_turns=1
            )
            
            output = result.final_output
            print(f"✓ Immediate Tests: {[t.test for t in output.immediate_tests[:3]]}")
            print(f"✓ Urgent Tests: {[t.test for t in output.urgent_tests[:3]]}")
            print(f"✓ Routine Tests: {[t.test for t in output.routine_tests[:3]]}")
            print(f"✓ Estimated Cost: {output.estimated_cost}")
            print(f"✓ Clinical Pearls: {output.clinical_pearls[:2] if output.clinical_pearls else 'None'}")
            
            # Basic validation
            if test_case["expected"]["ctas_level"] <= 2:
                if len(output.immediate_tests) > 0:
                    print(f"✅ Has immediate tests for high acuity patient")
                else:
                    print(f"⚠️  No immediate tests for high acuity patient")
            else:
                print(f"✅ Workup appropriate for acuity level")
                
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Run all individual agent tests."""
    print("\n" + "="*60)
    print("INDIVIDUAL AGENT TESTING SUITE")
    print("="*60)
    
    # Test each agent
    await test_red_flag_detector()
    await test_triage_assessor()
    await test_workup_suggester()
    
    print("\n" + "="*60)
    print("Individual Agent Testing Complete!")
    print("="*60)
    print("\nNext step: Test the orchestrator that combines all agents")
    print("Run: python scripts/test_orchestrator.py")


if __name__ == "__main__":
    asyncio.run(main())