#!/usr/bin/env python
"""Test performance without web tools - direct LLM response."""

import os
import json
import time
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv('/Users/liammckendry/health_assistant_performance/.env')

# Initialize client
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Test query
query = "What are symptoms of flu?"

print(f"Testing query WITHOUT web tools: {query}")
print("=" * 60)

# Measure time
start_time = time.time()

# Create message WITHOUT any web tools
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": query
        }
    ],
    system="You are a helpful medical information assistant. Provide accurate, educational information about health topics. Always remind users that this information is for educational purposes only and they should consult healthcare providers for medical advice."
)

elapsed_time = time.time() - start_time

# Print results
print(f"\n⏱️  Response Time: {elapsed_time:.2f} seconds")
print(f"📊 Token Usage:")
print(f"   - Input: {response.usage.input_tokens}")
print(f"   - Output: {response.usage.output_tokens}")
print(f"   - Total: {response.usage.input_tokens + response.usage.output_tokens}")

# Count tool calls (should be 0)
tool_calls = 0
citations = 0
for content in response.content:
    if hasattr(content, 'type'):
        if content.type == 'server_tool_use':
            tool_calls += 1
        elif content.type == 'text' and hasattr(content, 'citations') and content.citations:
            citations += len(content.citations)

print(f"🔧 Tool Calls: {tool_calls}")
print(f"📚 Citations: {citations}")

print("\n" + "=" * 60)
print("RESPONSE:")
print("=" * 60)
for content in response.content:
    if hasattr(content, 'text'):
        print(content.text)

# Log to performance tests file
log_entry = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "run_name": "no-web-tools",
    "query": query,
    "elapsed_seconds": elapsed_time,
    "citations": citations,
    "tool_calls": tool_calls,
    "model": "claude-3-5-sonnet-20241022",
    "usage": {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens
    },
    "trace_id": None
}

with open('/Users/liammckendry/health_assistant_performance/logs/performance_tests.jsonl', 'a') as f:
    f.write(json.dumps(log_entry) + '\n')

print(f"\n✅ Results saved to performance_tests.jsonl")
print(f"\n🎯 Key Finding: Response time WITHOUT web tools: {elapsed_time:.2f}s vs ~20-25s WITH web tools")