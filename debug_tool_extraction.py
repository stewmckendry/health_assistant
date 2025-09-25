#!/usr/bin/env python3
"""
Simple debug script to test tool call extraction
"""

import asyncio
import logging
from src.agents.dr_opa_agent.openai_agent import create_dr_opa_agent

# Set up logging to only show INFO and higher
logging.basicConfig(level=logging.INFO)

async def simple_debug():
    agent = await create_dr_opa_agent()
    
    print("🔍 Testing single query...")
    
    try:
        result = await agent.query("What are CPSO virtual care requirements?")
        
        if isinstance(result, dict):
            print(f"✅ Got dict response!")
            print(f"🔧 Tools Used: {result['tools_used']}")
            print(f"📊 Tool Call Count: {len(result['tool_calls'])}")
            
            if result['tool_calls']:
                print("\n🔧 Tool Calls Found:")
                for i, tc in enumerate(result['tool_calls'], 1):
                    print(f"  {i}. Tool: {tc['name']}")
                    args_preview = str(tc['arguments'])[:100] + "..." if len(str(tc['arguments'])) > 100 else str(tc['arguments'])
                    print(f"     Args: {args_preview}")
            else:
                print("❌ No tool calls captured")
            
            response_preview = result['response'][:200] + "..." if len(result['response']) > 200 else result['response']
            print(f"\n📄 Response Preview:\n{response_preview}")
            
        else:
            print(f"❌ Got string response instead of dict: {str(result)[:100]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(simple_debug())