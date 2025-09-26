#!/usr/bin/env python
"""Direct test of ADP tool without MCP server."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.dr_off_agent.mcp.tools.adp import adp_get
import json

async def test_adp_tool():
    """Test ADP tool directly."""
    print("Testing ADP tool directly...")
    
    # Test 1: Power wheelchair with proper structure
    print("\n1. Testing power wheelchair with correct structure:")
    request = {
        "device": {
            "category": "mobility",
            "type": "power wheelchair"
        },
        "check": ["eligibility", "exclusions", "funding", "cep"],
        "use_case": {
            "daily": True,
            "location": "home",
            "independent_transfer": False
        },
        "patient_income": 19000
    }
    
    try:
        print(f"Request: {json.dumps(request, indent=2)}")
        result = await adp_get(request)
        print(f"\nResponse:")
        print(json.dumps(result, indent=2, default=str))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Walker with CEP
    print("\n\n2. Testing walker with CEP eligibility:")
    request = {
        "device": {
            "category": "mobility",
            "type": "walker"
        },
        "check": ["eligibility", "funding", "cep"],
        "patient_income": 25000
    }
    
    try:
        result = await adp_get(request)
        print(f"Result confidence: {result.get('confidence', 0)}")
        if result.get("cep"):
            print(f"CEP eligible: {result['cep'].get('eligible')}")
        if result.get("funding"):
            print(f"Funding: ADP {result['funding'].get('adp_contribution')}%")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_adp_tool())