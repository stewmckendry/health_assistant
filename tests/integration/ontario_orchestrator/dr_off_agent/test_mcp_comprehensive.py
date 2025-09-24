#!/usr/bin/env python
"""Comprehensive test suite for Dr. OFF MCP tools"""

import asyncio
import sys
import json
from datetime import datetime
sys.path.insert(0, '.')

from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get
from src.agents.ontario_orchestrator.mcp.tools.odb import odb_get
from src.agents.ontario_orchestrator.mcp.tools.adp import adp_get
from src.agents.ontario_orchestrator.mcp.tools.coverage import coverage_answer

async def test_schedule():
    """Test schedule.get with various queries"""
    print("\n" + "="*60)
    print("TESTING SCHEDULE.GET")
    print("="*60)
    
    test_cases = [
        {
            "name": "Specific code lookup",
            "request": {
                "q": "C124 discharge billing",
                "codes": ["C124"],
                "include": ["codes", "fee", "limits"],
                "top_k": 3
            }
        },
        {
            "name": "General query",
            "request": {
                "q": "diabetes management",
                "codes": [],
                "include": ["codes", "fee", "limits"],
                "top_k": 5
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        result = await schedule_get(test['request'])
        print(f"Found {len(result.get('items', []))} items")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        print(f"Provenance: {', '.join(result.get('provenance', []))}")
        
        if result.get('items'):
            item = result['items'][0]
            print(f"Top result: {item.get('code', 'N/A')} - {item.get('description', 'N/A')[:60]}...")

async def test_odb():
    """Test odb.get with various drugs"""
    print("\n" + "="*60)
    print("TESTING ODB.GET")
    print("="*60)
    
    test_cases = [
        {
            "name": "Common drug lookup",
            "request": {
                "drug": "metformin",
                "check_alternatives": True,
                "include_lu": True,
                "top_k": 3
            }
        },
        {
            "name": "Brand name lookup",
            "request": {
                "drug": "lipitor",
                "check_alternatives": True,
                "include_lu": False,
                "top_k": 5
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        result = await odb_get(test['request'])
        print(f"Coverage status: {result.get('coverage_status', 'unknown')}")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        print(f"Provenance: {', '.join(result.get('provenance', []))}")
        
        if result.get('primary'):
            print(f"Primary drug: {result['primary'].get('drug_name', 'N/A')}")
        
        if result.get('interchangeables'):
            print(f"Found {len(result['interchangeables'])} interchangeable drugs")

async def test_adp():
    """Test adp.get with various devices"""
    print("\n" + "="*60)
    print("TESTING ADP.GET")
    print("="*60)
    
    test_cases = [
        {
            "name": "Wheelchair eligibility",
            "request": {
                "device": {"category": "mobility", "type": "wheelchair"},
                "check": ["eligibility", "funding", "exclusions"],
                "use_case": {"setting": "home", "duration": "long-term"},
                "patient_income": 25000
            }
        },
        {
            "name": "Hearing aid coverage",
            "request": {
                "device": {"category": "hearing", "type": "hearing_aid"},
                "check": ["eligibility", "funding", "cep"],
                "use_case": {},
                "patient_income": 35000
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        result = await adp_get(test['request'])
        print(f"Eligible: {result.get('eligible', False)}")
        print(f"Funding: {result.get('funding_percentage', 0)}%")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        print(f"Provenance: {', '.join(result.get('provenance', []))}")
        
        if result.get('exclusions'):
            print(f"Exclusions: {len(result['exclusions'])} found")

async def test_coverage():
    """Test coverage.answer orchestrator"""
    print("\n" + "="*60)
    print("TESTING COVERAGE.ANSWER (ORCHESTRATOR)")
    print("="*60)
    
    test_cases = [
        {
            "name": "Complex multi-tool query",
            "request": {
                "question": "Is a wheelchair covered for home use and what's the funding?",
                "hints": {"device": "wheelchair"},
                "patient": {"age": 65, "setting": "home", "income": 20000}
            }
        },
        {
            "name": "Drug coverage query",
            "request": {
                "question": "Is metformin covered by ODB and what are the alternatives?",
                "hints": {"drug": "metformin"},
                "patient": {"age": 70}
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        result = await coverage_answer(test['request'])
        print(f"Decision: {result.get('decision', 'unknown')}")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        print(f"Tools used: {', '.join(result.get('tools_used', []))}")
        
        if result.get('answer'):
            print(f"Answer preview: {result['answer'][:100]}...")
        
        if result.get('citations'):
            print(f"Citations: {len(result['citations'])} sources")

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("DR. OFF MCP COMPREHENSIVE TEST SUITE")
    print(f"Started: {datetime.now().isoformat()}")
    print("="*60)
    
    # Run tests sequentially to avoid overwhelming the system
    await test_schedule()
    await test_odb()
    await test_adp()
    await test_coverage()
    
    print("\n" + "="*60)
    print(f"TESTS COMPLETED: {datetime.now().isoformat()}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())