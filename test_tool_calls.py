#!/usr/bin/env python3
"""
Test script to verify tool call extraction and display
"""

import asyncio
from src.agents.dr_opa_agent.openai_agent import create_dr_opa_agent

async def test_with_tool_call_visibility():
    agent = await create_dr_opa_agent()
    
    # Test queries that should definitely trigger MCP tool calls
    test_queries = [
        "Search for CPSO policies on virtual care documentation",  # Should trigger opa_search_sections or opa_policy_check
        "Find Ontario breast cancer screening programs",            # Should trigger opa_program_lookup
        "Hand hygiene requirements for clinical settings"           # Should trigger opa_ipac_guidance
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        print("=" * 80)
        
        try:
            result = await agent.query(query)
            
            if isinstance(result, dict):
                print(f"🔧 Tools Used: {', '.join(result['tools_used']) if result['tools_used'] else 'None'}")
                print(f"📊 Tool Call Count: {len(result['tool_calls'])}")
                
                if result['tool_calls']:
                    print("\n🔧 Tool Call Details:")
                    for i, tc in enumerate(result['tool_calls'], 1):
                        print(f"  {i}. Tool: {tc['name']}")
                        args = tc['arguments']
                        if len(args) > 150:
                            args = args[:150] + "..."
                        print(f"     Args: {args}")
                
                print(f"\n📄 Response Length: {len(result['response'])} characters")
                print("Response Preview:")
                print("-" * 40)
                preview = result['response'][:300]
                if len(result['response']) > 300:
                    preview += "..."
                print(preview)
                
            else:
                print("⚠️  Got string response instead of dict - check agent implementation")
                print(f"Response: {result[:200]}...")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_with_tool_call_visibility())