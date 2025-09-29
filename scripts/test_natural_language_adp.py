#!/usr/bin/env python
"""Test natural language ADP queries."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.dr_off_agent.mcp.tools.adp import adp_get
import json

async def test_natural_language():
    """Test natural language queries."""
    
    print("Testing Natural Language ADP Queries\n")
    print("=" * 60)
    
    # Test 1: CPAP query
    print("\n1. Natural Language: 'Can my patient get funding for a CPAP?'")
    request = {
        "query": "Can my patient get funding for a CPAP machine?",
        "patient_income": 35000
    }
    
    try:
        result = await adp_get(request)
        
        # Show the summary
        if "summary" in result:
            print(f"\n📊 SUMMARY: {result['summary']}")
        
        # Show interpretation notes
        if "interpretation_notes" in result:
            print(f"\n📝 NOTES: {json.dumps(result['interpretation_notes'], indent=2)}")
        
        # Show key details
        print(f"\n✓ Confidence: {result.get('confidence', 0)}")
        if result.get("funding"):
            print(f"✓ Funding: ADP {result['funding']['adp_contribution']}% / Patient {result['funding']['client_share_percent']}%")
        if result.get("cep"):
            print(f"✓ CEP Eligible: {result['cep']['eligible']} (threshold ${result['cep']['income_threshold']})")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Power wheelchair query
    print("\n" + "=" * 60)
    print("\n2. Natural Language: 'Is a power wheelchair covered for low income patient?'")
    request = {
        "query": "Is a power wheelchair covered for my low income patient?",
        "patient_income": 19000
    }
    
    try:
        result = await adp_get(request)
        
        if "summary" in result:
            print(f"\n📊 SUMMARY: {result['summary']}")
        
        print(f"\n✓ Confidence: {result.get('confidence', 0)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_natural_language())