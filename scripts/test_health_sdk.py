#!/usr/bin/env python
"""Test SDK example with health query similar to our app."""

import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv('/Users/liammckendry/health_assistant_performance/.env')

# Initialize client
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Create message with both web_search and web_fetch tools
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",  # Using same model as our app
    max_tokens=1024,
    extra_headers={
        "anthropic-beta": "web-search-2025-03-05,web-fetch-2025-09-10"
    },
    tools=[
        {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 1  # Try limiting to 1 search
        },
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
with open('/Users/liammckendry/health_assistant_performance/logs/health_sdk_test.json', 'w') as f:
    json.dump(response.model_dump(), f, indent=2)

print("\n=== RESPONSE SAVED TO logs/health_sdk_test.json ===")