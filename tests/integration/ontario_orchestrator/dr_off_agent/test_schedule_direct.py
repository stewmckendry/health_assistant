#!/usr/bin/env python
"""Direct test of schedule.get tool"""

import asyncio
import sys
import json
sys.path.insert(0, '.')

from src.agents.ontario_orchestrator.mcp.tools.schedule import schedule_get

async def test():
    print('Testing schedule.get with C124 discharge billing...')
    request = {
        "q": 'C124 discharge billing',
        "codes": ['C124'],
        "include": ["codes", "fee", "limits", "documentation"],
        "top_k": 3
    }
    result = await schedule_get(request)
    
    # Print results
    print(f"\nFound {len(result.get('items', []))} items")
    print(f"SQL matches: {result.get('metadata', {}).get('sql_count', 0)}")
    print(f"Vector matches: {result.get('metadata', {}).get('vector_count', 0)}")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    
    if result.get('items'):
        print(f"\nTop result:")
        item = result['items'][0]
        print(f"  Code: {item.get('code', 'N/A')}")
        print(f"  Description: {item.get('description', 'N/A')[:100]}...")
        print(f"  Fee: ${item.get('fee', 0):.2f}")
        
        if item.get('limits'):
            print(f"  Limits: {item['limits'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test())