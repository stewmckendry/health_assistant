#!/usr/bin/env python
"""Test streaming with configurable settings."""

import asyncio
import aiohttp
import json
import time
import uuid
from datetime import datetime

# Test configuration
API_URL = "http://localhost:8000"
SESSION_ID = str(uuid.uuid4())
USER_ID = "test_user"

async def create_session():
    """Create a new session."""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/sessions", json={"userId": USER_ID}) as resp:
            data = await resp.json()
            return data["sessionId"]

async def update_settings(session_id: str, settings: dict):
    """Update session settings."""
    async with aiohttp.ClientSession() as session:
        async with session.put(
            f"{API_URL}/sessions/{session_id}/settings",
            json=settings
        ) as resp:
            data = await resp.json()
            print(f"✅ Settings updated: {json.dumps(settings, indent=2)}")
            return data

async def test_streaming(session_id: str, query: str):
    """Test streaming response."""
    print(f"\n🔍 Testing STREAMING for query: '{query}'")
    print("=" * 60)
    
    start_time = time.time()
    first_token_time = None
    accumulated_text = ""
    citations = []
    
    async with aiohttp.ClientSession() as session:
        # Make streaming request
        async with session.post(
            f"{API_URL}/chat/stream",
            json={
                "query": query,
                "sessionId": session_id,
                "userId": USER_ID,
                "mode": "patient"
            }
        ) as resp:
            if resp.status != 200:
                print(f"❌ Error: {resp.status}")
                text = await resp.text()
                print(f"Response: {text}")
                return
            
            # Process SSE stream
            async for line in resp.content:
                line_str = line.decode('utf-8').strip()
                if line_str.startswith('data: '):
                    try:
                        event = json.loads(line_str[6:])
                        
                        if event["type"] == "start":
                            print(f"📤 Stream started at {time.time() - start_time:.2f}s")
                        
                        elif event["type"] == "text":
                            if first_token_time is None:
                                first_token_time = time.time() - start_time
                                print(f"⚡ First token received at {first_token_time:.2f}s")
                            accumulated_text += event["content"]
                            # Print dots to show progress
                            print(".", end="", flush=True)
                        
                        elif event["type"] == "citation":
                            citations.append(event["content"])
                        
                        elif event["type"] == "complete":
                            total_time = time.time() - start_time
                            print(f"\n✅ Stream completed at {total_time:.2f}s")
                            print(f"📊 Metrics:")
                            print(f"  - Time to first token: {first_token_time:.2f}s")
                            print(f"  - Total time: {total_time:.2f}s")
                            print(f"  - Response length: {len(accumulated_text)} chars")
                            print(f"  - Citations: {len(citations)}")
                            if event.get("metadata"):
                                meta = event["metadata"]
                                if "usage" in meta:
                                    print(f"  - Tokens: {meta['usage'].get('total_tokens', 'N/A')}")
                        
                        elif event["type"] == "error":
                            print(f"\n❌ Error: {event.get('error', 'Unknown error')}")
                    
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse event: {line_str}")
    
    return accumulated_text, citations

async def test_non_streaming(session_id: str, query: str):
    """Test non-streaming response (when output guardrails are enabled)."""
    print(f"\n🔍 Testing NON-STREAMING for query: '{query}'")
    print("=" * 60)
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/chat",
            json={
                "query": query,
                "sessionId": session_id,
                "userId": USER_ID,
                "mode": "patient"
            }
        ) as resp:
            response_time = time.time() - start_time
            data = await resp.json()
            
            print(f"✅ Response received in {response_time:.2f}s")
            print(f"📊 Metrics:")
            print(f"  - Response length: {len(data.get('content', ''))} chars")
            print(f"  - Citations: {len(data.get('citations', []))}")
            print(f"  - Guardrails applied: {data.get('guardrailTriggered', False)}")
            
            return data.get('content', ''), data.get('citations', [])

async def main():
    """Run the tests."""
    print("🚀 Testing Health Assistant Streaming with Settings")
    print("=" * 60)
    
    # Create session
    session_id = await create_session()
    print(f"📝 Session created: {session_id}")
    
    # Test 1: Default settings (streaming enabled, output guardrails disabled)
    print("\n" + "=" * 60)
    print("TEST 1: Default Settings (Streaming ON, Output Guardrails OFF)")
    print("=" * 60)
    
    await update_settings(session_id, {
        "enable_streaming": True,
        "enable_output_guardrails": False,
        "enable_input_guardrails": True,
        "max_web_searches": 1,
        "max_web_fetches": 2
    })
    
    content1, citations1 = await test_streaming(session_id, "What are symptoms of flu?")
    
    # Test 2: Output guardrails enabled (forces non-streaming)
    print("\n" + "=" * 60)
    print("TEST 2: Output Guardrails ON (Forces Non-Streaming)")
    print("=" * 60)
    
    await update_settings(session_id, {
        "enable_streaming": True,  # Will be overridden
        "enable_output_guardrails": True,  # This forces non-streaming
        "enable_input_guardrails": True
    })
    
    content2, citations2 = await test_non_streaming(session_id, "What are treatments for headaches?")
    
    # Test 3: Streaming disabled explicitly
    print("\n" + "=" * 60)
    print("TEST 3: Streaming Explicitly Disabled")
    print("=" * 60)
    
    await update_settings(session_id, {
        "enable_streaming": False,
        "enable_output_guardrails": False,
        "enable_input_guardrails": True
    })
    
    content3, citations3 = await test_non_streaming(session_id, "What is diabetes?")
    
    # Test 4: Performance settings
    print("\n" + "=" * 60)
    print("TEST 4: Optimized for Speed (No web tools)")
    print("=" * 60)
    
    await update_settings(session_id, {
        "enable_streaming": True,
        "enable_output_guardrails": False,
        "max_web_searches": 0,  # No web searches
        "max_web_fetches": 0    # No web fetches
    })
    
    content4, citations4 = await test_streaming(session_id, "What is a cold?")
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed!")
    print("=" * 60)
    
    # Summary
    print("\n📊 SUMMARY:")
    print(f"1. Default (streaming): {len(content1)} chars, {len(citations1)} citations")
    print(f"2. Guardrails (non-streaming): {len(content2)} chars, {len(citations2)} citations")
    print(f"3. Disabled streaming: {len(content3)} chars, {len(citations3)} citations")
    print(f"4. No web tools: {len(content4)} chars, {len(citations4)} citations")

if __name__ == "__main__":
    asyncio.run(main())