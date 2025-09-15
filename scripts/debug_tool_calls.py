#!/usr/bin/env python
"""Debug script to see what Anthropic returns for tool calls."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from anthropic import Anthropic

def debug_tool_response():
    """Make a call with tools and inspect the response structure."""
    
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    # Make a medical query that should trigger web search and fetch
    response = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=1500,
        temperature=0.7,
        system="You are a medical education assistant. Use web search and fetch tools to find information.",
        messages=[
            {"role": "user", "content": "What are the latest CDC guidelines for COVID-19 vaccines?"}
        ],
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 2
            },
            {
                "type": "web_fetch_20250910",
                "name": "web_fetch",
                "allowed_domains": ["cdc.gov", "who.int"],
                "max_uses": 3,
                "citations": {"enabled": True}
            }
        ],
        extra_headers={
            "anthropic-beta": "web-search-2025-03-05,web-fetch-2025-09-10"
        }
    )
    
    print("=" * 60)
    print("RESPONSE STRUCTURE ANALYSIS")
    print("=" * 60)
    
    # Analyze each content block
    for i, block in enumerate(response.content):
        print(f"\n--- Content Block {i} ---")
        print(f"Type: {type(block).__name__}")
        print(f"Has 'type' attr: {hasattr(block, 'type')}")
        if hasattr(block, 'type'):
            print(f"Block type: {block.type}")
        
        # List all attributes
        attrs = [attr for attr in dir(block) if not attr.startswith('_')]
        print(f"Attributes: {', '.join(attrs[:10])}")  # First 10 attrs
        
        # Check for specific attributes
        if hasattr(block, 'text'):
            print(f"Has text: {len(str(block.text))} chars")
        if hasattr(block, 'name'):
            print(f"Tool name: {block.name}")
        if hasattr(block, 'input'):
            print(f"Tool input: {block.input}")
        if hasattr(block, 'citations'):
            print(f"Has citations: {block.citations is not None}")
            if block.citations:
                print(f"Citation count: {len(block.citations)}")
    
    print("\n" + "=" * 60)
    print("TOOL USAGE SUMMARY")
    print("=" * 60)
    
    # Count tool usage
    tool_uses = []
    for block in response.content:
        if hasattr(block, 'type'):
            if 'tool' in str(block.type).lower() or block.type in ['server_tool_use', 'tool_use']:
                tool_info = {
                    'type': block.type,
                    'name': getattr(block, 'name', 'unknown')
                }
                tool_uses.append(tool_info)
                print(f"Found tool use: {tool_info}")
    
    if not tool_uses:
        print("No tool uses detected with current detection logic")
    
    return response

if __name__ == "__main__":
    debug_tool_response()