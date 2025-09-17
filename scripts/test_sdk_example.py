#!/usr/bin/env python
"""Test SDK example with combined search and fetch tools."""

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
    model="claude-opus-4-1-20250805",
    max_tokens=1024,
    extra_headers={
        "anthropic-beta": "web-search-2025-03-05,web-fetch-2025-09-10"
    },
    tools=[
        {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 3
        },
        {
            "type": "web_fetch_20250910", 
            "name": "web_fetch",
            "max_uses": 5
        }
    ],
    messages=[
        {
            "role": "user",
            "content": "Find me the latest articles about quantum computing and summarize the key developments"
        }
    ]
)

# Print raw response
print("=== RAW RESPONSE ===")
print(json.dumps(response.model_dump(), indent=2))

# Save to file for analysis
with open('/Users/liammckendry/health_assistant_performance/logs/sdk_test_response.json', 'w') as f:
    json.dump(response.model_dump(), f, indent=2)

print("\n=== RESPONSE SAVED TO logs/sdk_test_response.json ===")