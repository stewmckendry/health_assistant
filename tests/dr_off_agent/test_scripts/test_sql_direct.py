#!/usr/bin/env python
"""
Direct test of SQL client to debug why it's not finding codes
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from dotenv import load_dotenv
load_dotenv()

from src.agents.dr_off_agent.mcp.retrieval.sql_client import SQLClient

async def test_sql_client():
    """Test SQL client directly"""
    
    print("=" * 60)
    print("DIRECT SQL CLIENT TEST")
    print("=" * 60)
    
    # Initialize SQL client
    client = SQLClient(db_path="data/ohip.db")
    
    # Test 1: Direct query for C124
    print("\nTest 1: Query for C124 directly")
    try:
        results = await client.query_schedule_fees(
            codes=["C124", "C122", "C123"],
            limit=10
        )
        print(f"Results: {len(results)} items found")
        for result in results:
            print(f"  - {result.get('code')}: {result.get('description')} - ${result.get('amount', 0)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Search by text
    print("\nTest 2: Search for 'discharge' text")
    try:
        results = await client.query_schedule_fees(
            search_text="discharge",
            limit=5
        )
        print(f"Results: {len(results)} items found")
        for result in results:
            print(f"  - {result.get('code')}: {result.get('description')} - ${result.get('amount', 0)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Raw SQL query
    print("\nTest 3: Raw SQL query")
    try:
        query = "SELECT fee_code, description, amount FROM ohip_fee_schedule WHERE fee_code IN ('C124', 'C122', 'C123')"
        results = await client.query(query)
        print(f"Results: {len(results)} items found")
        for result in results:
            print(f"  - {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Check table structure
    print("\nTest 4: Table structure")
    try:
        query = "SELECT * FROM ohip_fee_schedule LIMIT 1"
        results = await client.query(query)
        if results:
            print(f"Columns: {list(results[0].keys())}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_sql_client())