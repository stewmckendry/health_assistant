#!/usr/bin/env python
"""Test if concatenated streaming blocks equal final response."""

import os
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

# Track streamed content
streamed_text = ""
block_count = 0

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
        # Collect all text from deltas
        if event.type == "content_block_delta":
            if hasattr(event.delta, 'text'):
                streamed_text += event.delta.text
                
        elif event.type == "content_block_start":
            if getattr(event.content_block, 'type', None) == 'text':
                block_count += 1
    
    # Get final message
    final_message = stream.get_final_message()

# Extract final response text
final_text = ""
for block in final_message.content:
    if hasattr(block, 'text'):
        final_text += block.text

print("\n📊 COMPARISON RESULTS:")
print("=" * 60)

print(f"📝 Streamed text length: {len(streamed_text)} characters")
print(f"📄 Final text length: {len(final_text)} characters")
print(f"📦 Number of text blocks: {block_count}")

print(f"\n✅ Text matches: {streamed_text == final_text}")

if streamed_text != final_text:
    print("\n⚠️ DIFFERENCES FOUND:")
    print(f"Length difference: {len(final_text) - len(streamed_text)} characters")
    
    # Find where they differ
    for i in range(min(len(streamed_text), len(final_text))):
        if i >= len(streamed_text) or i >= len(final_text) or streamed_text[i] != final_text[i]:
            print(f"First difference at position {i}:")
            print(f"  Streamed: ...{streamed_text[max(0,i-20):i+20]}...")
            print(f"  Final:    ...{final_text[max(0,i-20):i+20]}...")
            break
else:
    print("\n✅ Perfect match! The concatenated streamed text is identical to the final response.")

# Show samples
print("\n📋 CONTENT SAMPLES:")
print("-" * 40)
print("First 200 chars of streamed text:")
print(streamed_text[:200])
print("\n" + "-" * 40)
print("First 200 chars of final text:")
print(final_text[:200])

# Show the structure
print("\n📊 RESPONSE STRUCTURE:")
print("-" * 40)
lines = streamed_text.split('\n')
print(f"Total lines: {len(lines)}")
print(f"Text blocks concatenated: {block_count}")
print("\nFirst 10 lines:")
for i, line in enumerate(lines[:10], 1):
    if line.strip():
        print(f"  {i}. {line[:60]}{'...' if len(line) > 60 else ''}")
    else:
        print(f"  {i}. [empty line]")