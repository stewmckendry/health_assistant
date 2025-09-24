#!/usr/bin/env python
"""Direct test of odb.get tool"""

import asyncio
import sys
import json
sys.path.insert(0, '.')

from src.agents.ontario_orchestrator.mcp.tools.odb import odb_get

async def test():
    print('Testing odb.get with metformin...')
    request = {
        "drug": "metformin",
        "check_alternatives": True,
        "include_lu": True,
        "top_k": 3
    }
    result = await odb_get(request)
    
    # Print results
    print(f"\nCoverage status: {result.get('coverage_status', 'unknown')}")
    print(f"Primary drug: {result.get('primary', {}).get('drug_name', 'N/A')}")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    
    if result.get('interchangeables'):
        print(f"\nFound {len(result['interchangeables'])} interchangeable drugs")
        for drug in result['interchangeables'][:3]:
            print(f"  - {drug.get('drug_name', 'N/A')}: ${drug.get('unit_price', 0):.2f}")
    
    if result.get('lowest_cost'):
        print(f"\nLowest cost option: {result['lowest_cost'].get('drug_name', 'N/A')}")
        print(f"  Price: ${result['lowest_cost'].get('unit_price', 0):.2f}")

if __name__ == "__main__":
    asyncio.run(test())