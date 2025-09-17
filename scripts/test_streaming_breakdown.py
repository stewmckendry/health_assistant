#!/usr/bin/env python
"""Test to clearly show what parts of the response are being streamed."""

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

# Track different content types
content_blocks = []
current_block_type = None
current_block_content = ""

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
        }
    ],
    messages=[
        {
            "role": "user",
            "content": query
        }
    ]
) as stream:
    
    for event in stream:
        
        if event.type == "content_block_start":
            # Save previous block if exists
            if current_block_type and current_block_content:
                content_blocks.append({
                    "type": current_block_type,
                    "content": current_block_content
                })
            
            # Start new block
            current_block_type = getattr(event.content_block, 'type', 'unknown')
            current_block_content = ""
            
            if current_block_type == "server_tool_use":
                tool_name = getattr(event.content_block, 'name', 'unknown')
                tool_input = getattr(event.content_block, 'input', {})
                current_block_content = f"Tool: {tool_name}, Input: {tool_input}"
                
        elif event.type == "content_block_delta":
            # Accumulate text
            if hasattr(event.delta, 'text'):
                current_block_content += event.delta.text
                
    # Save last block
    if current_block_type and current_block_content:
        content_blocks.append({
            "type": current_block_type,
            "content": current_block_content
        })

# Analyze what was streamed
print("\n📊 CONTENT BREAKDOWN:")
print("=" * 60)

for i, block in enumerate(content_blocks, 1):
    print(f"\n🔹 Block {i}: Type = {block['type']}")
    print("-" * 40)
    
    if block['type'] == 'text':
        # Show first 200 chars of text blocks
        preview = block['content'][:200]
        if len(block['content']) > 200:
            preview += "..."
        print(f"Text content: {preview}")
        print(f"Length: {len(block['content'])} characters")
        
    elif block['type'] == 'server_tool_use':
        print(f"Tool execution: {block['content']}")
        
    else:
        print(f"Content: {block['content'][:200] if len(block['content']) > 200 else block['content']}")

print("\n" + "=" * 60)
print(f"📈 SUMMARY:")
print(f"- Total blocks streamed: {len(content_blocks)}")
print(f"- Block types: {[b['type'] for b in content_blocks]}")

# Categorize the blocks
text_blocks = [b for b in content_blocks if b['type'] == 'text']
tool_blocks = [b for b in content_blocks if b['type'] == 'server_tool_use']

print(f"- Text blocks: {len(text_blocks)}")
print(f"- Tool blocks: {len(tool_blocks)}")

if text_blocks:
    print(f"\n📝 Text block purposes:")
    for i, block in enumerate(text_blocks, 1):
        # Guess the purpose based on content
        content_lower = block['content'].lower()
        if 'search' in content_lower or 'let me' in content_lower or 'i\'ll' in content_lower:
            purpose = "Claude's thinking/planning"
        elif 'based on' in content_lower or 'here are' in content_lower or 'symptoms' in content_lower:
            purpose = "Final answer/response"
        else:
            purpose = "Other content"
        print(f"  - Block {i}: {purpose} ({len(block['content'])} chars)")