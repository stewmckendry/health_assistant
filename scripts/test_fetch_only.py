#!/usr/bin/env python
"""Test SDK with only web_fetch tool (no web_search)."""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv('/Users/liammckendry/health_assistant_performance/.env')

# Initialize client
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Create message with ONLY web_fetch tool (no web_search)
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    extra_headers={
        "anthropic-beta": "web-search-2025-03-05,web-fetch-2025-09-10"
    },
    tools=[
        {
            "type": "web_fetch_20250910", 
            "name": "web_fetch",
            "max_uses": 2  # Try limiting to 2 fetches
        }
    ],
    messages=[
        {
            "role": "user",
            "content": "What are symptoms of flu?"
        }
    ]
)

# Print raw response
print("=== RAW RESPONSE ===")
print(json.dumps(response.model_dump(), indent=2))

# Count tool calls
tool_calls = 0
for content in response.content:
    if content.type == 'server_tool_use':
        tool_calls += 1
        print(f"\nTool call {tool_calls}: {content.name}")

print(f"\nTotal tool calls: {tool_calls}")

# Save to file for analysis
with open('/Users/liammckendry/health_assistant_performance/logs/fetch_only_test.json', 'w') as f:
    json.dump(response.model_dump(), f, indent=2)

print("\n=== RESPONSE SAVED TO logs/fetch_only_test.json ===")