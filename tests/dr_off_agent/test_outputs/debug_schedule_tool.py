#!/usr/bin/env python
"""
Debug the schedule tool to understand why SQL results aren't being returned
"""

import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

from dotenv import load_dotenv
load_dotenv()

from src.agents.dr_off_agent.mcp.tools.schedule import ScheduleTool
from src.agents.dr_off_agent.mcp.models.request import ScheduleGetRequest

async def debug_schedule_tool():
    """Debug the schedule tool step by step"""
    
    print("=" * 60)
    print("DEBUGGING SCHEDULE TOOL")
    print("=" * 60)
    
    # Create tool instance
    tool = ScheduleTool()
    
    # Create request
    request = ScheduleGetRequest(
        q="MRP billing C124",
        codes=["C124", "C122", "C123"],
        include=["codes", "fee", "limits", "documentation"],
        top_k=5
    )
    
    print(f"\nRequest: {request}")
    print(f"SQL Client DB Path: {tool.sql_client.db_path}")
    print(f"Vector Client Path: {tool.vector_client.persist_dir}")
    
    # Execute
    print("\nExecuting...")
    response = await tool.execute(request)
    
    print(f"\nResponse:")
    print(f"  Provenance: {response.provenance}")
    print(f"  Confidence: {response.confidence}")
    print(f"  Items: {len(response.items)}")
    for item in response.items:
        print(f"    - {item.code}: {item.description} - ${item.fee}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(debug_schedule_tool())