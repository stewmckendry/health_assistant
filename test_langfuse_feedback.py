#!/usr/bin/env python3
"""
Test script to verify Langfuse tracing and feedback integration for Dr. OFF and Dr. OPA agents.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_dr_off_agent():
    """Test Dr. OFF agent with Langfuse tracing"""
    from src.agents.dr_off_agent.openai_agent import create_dr_off_agent
    
    print("Testing Dr. OFF Agent with Langfuse tracing...")
    print("-" * 50)
    
    # Create agent
    agent = await create_dr_off_agent()
    
    # Test query with user_id and session_id
    result = await agent.query(
        "What is covered under OHIP for diabetes management?",
        session_id="test-session-001",
        user_id="test-user-001"
    )
    
    print(f"✅ Response received: {len(result.get('response', ''))} characters")
    print(f"✅ Trace ID: {result.get('trace_id')}")
    print(f"✅ Citations: {len(result.get('citations', []))}")
    print(f"✅ Tools used: {result.get('tools_used', [])}")
    
    return result.get('trace_id')

async def test_dr_opa_agent():
    """Test Dr. OPA agent with Langfuse tracing"""
    from src.agents.dr_opa_agent.openai_agent import create_dr_opa_agent
    
    print("\nTesting Dr. OPA Agent with Langfuse tracing...")
    print("-" * 50)
    
    # Create agent
    agent = await create_dr_opa_agent()
    
    # Test query with user_id and session_id
    result = await agent.query(
        "What are the CPSO guidelines for telemedicine?",
        session_id="test-session-002",
        user_id="test-user-001"
    )
    
    print(f"✅ Response received: {len(result.get('response', ''))} characters")
    print(f"✅ Trace ID: {result.get('trace_id')}")
    print(f"✅ Citations: {len(result.get('citations', []))}")
    print(f"✅ Highlights: {len(result.get('highlights', []))}")
    print(f"✅ Tools used: {result.get('tools_used', [])}")
    
    return result.get('trace_id')

async def test_feedback_submission(trace_id: str):
    """Test feedback submission via API"""
    import aiohttp
    import json
    
    print(f"\nTesting feedback submission for trace: {trace_id}")
    print("-" * 50)
    
    feedback_data = {
        "traceId": trace_id,
        "sessionId": "test-session-001",
        "rating": 5,
        "comment": "Test feedback - excellent response with proper citations"
    }
    
    # Note: This would normally go to the web API endpoint
    # For testing, we'll simulate the Langfuse update directly
    try:
        from langfuse import Langfuse
        
        langfuse = Langfuse()
        
        # Add score to the trace
        langfuse.score(
            trace_id=trace_id,
            name="user_rating",
            value=feedback_data["rating"],
            comment=feedback_data["comment"]
        )
        
        langfuse.flush()
        
        print(f"✅ Feedback submitted successfully")
        print(f"   - Rating: {feedback_data['rating']}/5")
        print(f"   - Comment: {feedback_data['comment']}")
        
    except Exception as e:
        print(f"❌ Failed to submit feedback: {e}")

async def main():
    """Run all tests"""
    print("=" * 60)
    print("LANGFUSE TRACING & FEEDBACK INTEGRATION TEST")
    print("=" * 60)
    
    # Check environment
    if not os.getenv("LANGFUSE_PUBLIC_KEY"):
        print("⚠️  LANGFUSE_PUBLIC_KEY not set - tracing will be disabled")
    if not os.getenv("LANGFUSE_SECRET_KEY"):
        print("⚠️  LANGFUSE_SECRET_KEY not set - tracing will be disabled")
    
    print()
    
    try:
        # Test Dr. OFF agent
        dr_off_trace_id = await test_dr_off_agent()
        
        # Test Dr. OPA agent  
        dr_opa_trace_id = await test_dr_opa_agent()
        
        # Test feedback submission (if trace IDs were generated)
        if dr_off_trace_id:
            await test_feedback_submission(dr_off_trace_id)
        else:
            print("\n⚠️  No trace ID from Dr. OFF - skipping feedback test")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\n📊 Check your Langfuse dashboard for traces:")
    print(f"   {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")

if __name__ == "__main__":
    asyncio.run(main())