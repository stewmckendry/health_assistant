#!/usr/bin/env python3
"""
Test streaming progress tracker with a real agent (Dr. OPA).

This proves the StreamingProgressTracker works with actual SDK events
from a real agent run.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.ai_agents.diagnostic_orchestrator.streaming_progress import StreamingProgressTracker
from src.ai_agents.dr_off_agent.openai_agent import DrOffAgent
from agents import Runner
from agents.stream_events import RunItemStreamEvent, AgentUpdatedStreamEvent


async def test_streaming_progress_with_real_agent():
    """Test StreamingProgressTracker with Dr. OFF agent"""

    print("="*80)
    print("Testing Streaming Progress Tracker with Real Agent (Dr. OFF)")
    print("="*80)
    print()

    # Initialize Dr. OFF agent
    print("Initializing Dr. OFF agent...")
    dr_off = DrOffAgent(enable_langfuse=False)
    await dr_off.initialize_mcp_tools()
    print("✓ Dr. OFF initialized")
    print()

    # Test query for OHIP billing codes
    query = "What are the OHIP billing codes for virtual care visits?"

    print(f"Query: {query}")
    print()
    print("Progress updates:")
    print("-"*80)

    # Get the agent instance
    async with dr_off.mcp_server as mcp:
        agent = dr_off.get_agent(mcp)

        # Run with streaming
        result = Runner.run_streamed(
            starting_agent=agent,
            input=query
        )

        # Create progress tracker and test
        tracker = StreamingProgressTracker()

        print("PROGRESS EVENTS:")
        print("="*80)
        progress_count = 0
        async for progress in tracker.stream_progress(result.stream_events()):
            progress_count += 1
            print(f"[{progress_count}] {progress.event_type}: {progress.message}")
            if progress.details:
                print(f"    └─ Details: {progress.details}")

        print("\n" + "="*80)
        print(f"Total progress events: {progress_count}")
        print("="*80)

        print("\n✅ Progress tracking test complete!")


if __name__ == "__main__":
    asyncio.run(test_streaming_progress_with_real_agent())
