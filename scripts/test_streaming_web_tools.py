#!/usr/bin/env python
"""Test streaming response with web tools showing progress updates."""

import os
import time
import json
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv('/Users/liammckendry/health_assistant_performance/.env')

# Initialize client
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Test query
query = "What are symptoms of flu?"

print(f"🔍 Query: {query}")
print("=" * 60)
print("Starting streaming response with web tools...")
print("=" * 60)

# Track timing
start_time = time.time()
first_token_time = None
search_start_time = None
search_end_time = None

# Track content and metrics
accumulated_text = ""
tool_calls = []
citations_count = 0
current_tool = None

# Use streaming with web tools
with client.messages.stream(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    extra_headers={
        "anthropic-beta": "web-search-2025-03-05,web-fetch-2025-09-10"
    },
    tools=[
        {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 1
        },
        {
            "type": "web_fetch_20250910",
            "name": "web_fetch",
            "max_uses": 2
        }
    ],
    messages=[
        {
            "role": "user",
            "content": query
        }
    ]
) as stream:
    print("\n📡 STREAMING RESPONSE:")
    print("-" * 60)
    
    for event in stream:
        current_time = time.time() - start_time
        
        # Track different event types
        if event.type == "message_start":
            print(f"\n[{current_time:.2f}s] ✅ Starting response...\n")
            
        elif event.type == "content_block_start":
            block_type = getattr(event.content_block, 'type', 'unknown')
            
            # Check if it's a tool use block
            if block_type == "server_tool_use":
                tool_name = getattr(event.content_block, 'name', 'unknown')
                tool_input = getattr(event.content_block, 'input', {})
                current_tool = tool_name
                
                print(f"\n[{current_time:.2f}s] 🔧 Using tool: {tool_name}")
                if tool_name == "web_search" and 'query' in tool_input:
                    print(f"   → Searching for: '{tool_input['query']}'")
                    search_start_time = current_time
                elif tool_name == "web_fetch" and 'url' in tool_input:
                    print(f"   → Fetching: {tool_input['url'][:60]}...")
                    
                tool_calls.append(tool_name)
                
        elif event.type == "content_block_delta":
            # Print text as it comes in
            if hasattr(event.delta, 'text'):
                if first_token_time is None:
                    first_token_time = current_time
                    print(f"\n[{current_time:.2f}s] 💬 Claude's response:\n")
                    print("-" * 40)
                
                # Print the text immediately for real-time updates
                print(event.delta.text, end='', flush=True)
                accumulated_text += event.delta.text
                    
        elif event.type == "content_block_stop":
            block_type = getattr(event.content_block, 'type', None) if hasattr(event, 'content_block') else None
            
            # Check if we just finished a tool
            if block_type == "server_tool_use" and current_tool:
                if current_tool == "web_search" and search_start_time:
                    search_end_time = current_time
                    print(f"\n[{current_time:.2f}s] ✓ Web search completed in {search_end_time - search_start_time:.2f}s")
                else:
                    print(f"\n[{current_time:.2f}s] ✓ {current_tool} completed")
                current_tool = None
            elif block_type == "text":
                # Text block finished
                print("\n" + "-" * 40)
                
        elif event.type == "message_stop":
            print(f"\n[{current_time:.2f}s] 🏁 Response completed")

    print("\n" + "=" * 60)
    
    # Get the final accumulated message
    final_message = stream.get_final_message()
    
    # Count citations from the final message
    for block in final_message.content:
        if hasattr(block, 'citations') and block.citations:
            citations_count += len(block.citations)

# Calculate final metrics
total_time = time.time() - start_time
time_to_first_token = first_token_time if first_token_time else 0

print("\n📈 PERFORMANCE METRICS:")
print("=" * 60)
print(f"⏱️  Total response time: {total_time:.2f} seconds")
print(f"🎯 Time to first token: {time_to_first_token:.2f} seconds")
if search_start_time and search_end_time:
    print(f"🔍 Web search duration: {search_end_time - search_start_time:.2f} seconds")
print(f"📝 Response length: {len(accumulated_text)} characters")
print(f"🔧 Tool calls made: {len(tool_calls)} - {tool_calls}")
print(f"📚 Citations found: {citations_count}")
print(f"💰 Token usage:")
print(f"   - Input: {final_message.usage.input_tokens}")
print(f"   - Output: {final_message.usage.output_tokens}")
print(f"   - Total: {final_message.usage.input_tokens + final_message.usage.output_tokens}")

# Log results
log_entry = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "run_name": "streaming-web-tools",
    "query": query,
    "elapsed_seconds": total_time,
    "time_to_first_token": time_to_first_token,
    "citations": citations_count,
    "tool_calls": len(tool_calls),
    "model": "claude-3-5-sonnet-20241022",
    "usage": {
        "input_tokens": final_message.usage.input_tokens,
        "output_tokens": final_message.usage.output_tokens
    }
}

with open('/Users/liammckendry/health_assistant_performance/logs/performance_tests.jsonl', 'a') as f:
    f.write(json.dumps(log_entry) + '\n')

print(f"\n✅ Results saved to performance_tests.jsonl")