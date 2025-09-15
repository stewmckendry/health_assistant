#!/usr/bin/env python
"""Test tool call tracking in Langfuse."""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

from src.assistants.patient import PatientAssistant

def test_tool_tracking():
    """Test that web_search and web_fetch are properly tracked."""
    
    print("🔍 Testing Tool Call Tracking")
    print("=" * 60)
    
    # Initialize assistant
    assistant = PatientAssistant(guardrail_mode="hybrid")
    
    # Query that should trigger web search and fetch
    query = "What are the latest CDC guidelines on flu vaccines for children?"
    session_id = "tool_tracking_test_001"
    
    print(f"Query: {query}")
    print(f"Session: {session_id}")
    print("-" * 60)
    
    # Process query
    response = assistant.query(query, session_id)
    
    # Display tool call information
    print("\n📊 Tool Calls Tracked:")
    if "tool_calls" in response:
        for i, tool_call in enumerate(response["tool_calls"], 1):
            print(f"\n  Tool Call #{i}:")
            print(f"    Type: {tool_call.get('type', 'unknown')}")
            print(f"    Name: {tool_call.get('name', 'unknown')}")
            if 'input' in tool_call and tool_call['input']:
                print(f"    Input: {json.dumps(tool_call['input'], indent=6)[:100]}...")
            if 'fetch_count' in tool_call:
                print(f"    Fetches: {tool_call['fetch_count']} pages")
    else:
        print("  No tool calls tracked in response")
    
    print("\n📚 Citations Found:")
    if "citations" in response and response["citations"]:
        for i, citation in enumerate(response["citations"][:5], 1):  # Show first 5
            print(f"  {i}. {citation.get('title', 'Untitled')[:50]}...")
            print(f"     URL: {citation.get('url', 'No URL')[:60]}...")
    else:
        print("  No citations found")
    
    print("\n" + "=" * 60)
    print("✅ Check Langfuse dashboard for:")
    print("   - 'llm_call' span should show tool_calls array")
    print("   - Look for 'web_search' and 'web_fetch_summary' entries")
    print("   - Tool inputs and fetch counts should be visible")

if __name__ == "__main__":
    test_tool_tracking()