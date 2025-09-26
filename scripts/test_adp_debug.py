#!/usr/bin/env python
"""Debug script for testing ADP tool directly."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.dr_off_agent.mcp.tools.adp import adp_get
from src.agents.dr_off_agent.mcp.tools.adp import ADPGetRequest

async def test_adp_tool():
    """Test ADP tool with different queries."""
    print("Testing ADP tool...")
    
    # Test 1: Simple wheelchair query
    print("\n1. Testing simple wheelchair query:")
    request = ADPGetRequest(
        device={"type": "wheelchair"}
    )
    try:
        result = await adp_get(request)
        print(f"Result: {result}")
        print(f"Confidence: {result.confidence}")
        print(f"Citations: {result.citations}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Power wheelchair with use case
    print("\n2. Testing power wheelchair with use case:")
    request = ADPGetRequest(
        device={"type": "power wheelchair"},
        use_case={"query": "Patient with MS needs power wheelchair"}
    )
    try:
        result = await adp_get(request)
        print(f"Result confidence: {result.confidence}")
        if result.eligibility:
            print(f"Eligibility: {result.eligibility.eligible}")
        if result.funding:
            print(f"Funding: {result.funding.percentage}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_adp_tool())