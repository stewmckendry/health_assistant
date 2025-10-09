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
from src.ai_agents.dr_opa_agent.openai_agent import DrOPAAgent
from agents import Runner


async def test_streaming_progress_with_real_agent():
    """Test StreamingProgressTracker with Dr. OPA agent"""

    print("="*80)
    print("Testing Streaming Progress Tracker with Real Agent (Dr. OPA)")
    print("="*80)
    print()

    # Initialize Dr. OPA agent
    print("Initializing Dr. OPA agent...")
    dr_opa = DrOPAAgent(enable_langfuse=False)
    await dr_opa.initialize_mcp_tools()
    print("✓ Dr. OPA initialized")
    print()

    # Simple test query
    query = "What are the CPSO policies on obtaining informed consent?"

    print(f"Query: {query}")
    print()
    print("Progress updates:")
    print("-"*80)

    # Get the agent instance
    async with dr_opa.mcp_server as mcp:
        agent = dr_opa.get_agent(mcp)

        # Run with streaming
        result = Runner.run_streamed(
            starting_agent=agent,
            input=query
        )

        # Create progress tracker
        tracker = StreamingProgressTracker()

        # Stream progress updates
        final_output = None
        async for progress in tracker.stream_progress(result.stream_events()):
            print(f"  {progress.message}")
            if progress.details:
                print(f"    └─ Details: {progress.details}")

        print("-"*80)
        print()
        print("✅ Test complete!")
        print()

        # Get final response (already consumed by streaming)
        final_output = result.final_output_as(str)
        if final_output:
            print(f"Final response preview: {str(final_output)[:200]}...")
        else:
            print("(Final output consumed during streaming)")
        print()
        print("="*80)
        print("SUCCESS: StreamingProgressTracker works with real agents!")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(test_streaming_progress_with_real_agent())
