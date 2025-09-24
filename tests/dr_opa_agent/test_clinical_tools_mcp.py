#!/usr/bin/env python3
"""Test the new clinical_tools MCP tool."""

import sys
import asyncio
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.dr_opa_agent.mcp.server import clinical_tools_handler


async def test_clinical_tools():
    """Test the clinical_tools MCP tool with various queries."""
    
    print("\n" + "="*60)
    print("TESTING CEP CLINICAL TOOLS MCP TOOL")
    print("="*60 + "\n")
    
    # Test 1: Search by condition
    print("Test 1: Search for dementia tools")
    print("-" * 40)
    result = await clinical_tools_handler(condition="dementia")
    print(f"Found {result['total_tools']} tools")
    for tool in result['tools']:
        print(f"  - {tool['name']}: {tool['url']}")
        if tool.get('key_features'):
            features = [k for k, v in tool['key_features'].items() if v]
            if features:
                print(f"    Features: {', '.join(features)}")
    
    # Test 2: Search by category
    print("\nTest 2: Search by category (mental_health)")
    print("-" * 40)
    result = await clinical_tools_handler(category="mental_health")
    print(f"Found {result['total_tools']} tools")
    for tool in result['tools']:
        print(f"  - {tool['name']} ({tool['category']})")
    
    # Test 3: Search by feature type
    print("\nTest 3: Search for tools with algorithms")
    print("-" * 40)
    result = await clinical_tools_handler(feature_type="algorithm")
    print(f"Found {result['total_tools']} tools with algorithms")
    for tool in result['tools']:
        print(f"  - {tool['name']}")
        if tool['key_features'].get('assessment_algorithm'):
            print(f"    Algorithm URL: {tool['key_features']['assessment_algorithm']['url']}")
    
    # Test 4: Get tool with sections
    print("\nTest 4: Get dementia tool with sections")
    print("-" * 40)
    result = await clinical_tools_handler(
        tool_name="dementia",
        include_sections=True
    )
    if result['tools']:
        tool = result['tools'][0]
        print(f"Tool: {tool['name']}")
        print(f"URL: {tool['url']}")
        if tool.get('sections'):
            print(f"Sections ({len(tool['sections'])}):")
            for section in tool['sections']:
                print(f"  - {section['title']}")
                print(f"    URL: {section['url']}")
                print(f"    Summary: {section['summary'][:100]}...")
    
    # Test 5: Get all CEP tools
    print("\nTest 5: Get all CEP tools")
    print("-" * 40)
    result = await clinical_tools_handler()
    print(f"Total CEP tools in database: {result['total_tools']}")
    
    categories = {}
    for tool in result['tools']:
        cat = tool.get('category', 'unknown')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tool['name'])
    
    print("\nTools by category:")
    for cat, tools in categories.items():
        print(f"  {cat}: {', '.join(tools)}")
    
    print("\n" + "="*60)
    print("TEST COMPLETED SUCCESSFULLY!")
    print("="*60 + "\n")
    
    return result


if __name__ == "__main__":
    asyncio.run(test_clinical_tools())