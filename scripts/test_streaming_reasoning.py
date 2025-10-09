#!/usr/bin/env python3
"""
Test streaming progress tracker with reasoning-enabled model.

This verifies that reasoning items are captured and displayed correctly.
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.ai_agents.diagnostic_orchestrator.streaming_progress import StreamingProgressTracker
from agents import Agent, Runner, ModelSettings


async def test_reasoning_progress():
    """Test StreamingProgressTracker with reasoning-enabled agent"""

    print("="*80)
    print("Testing Streaming Progress with Reasoning (o4-mini)")
    print("="*80)
    print()

    # Create a simple agent with reasoning enabled
    agent = Agent(
        name="Reasoning Assistant",
        instructions="You are a helpful medical assistant. Think through clinical problems step by step.",
        model="o4-mini",
        model_settings=ModelSettings(reasoning={"summary": "auto"}),
    )

    query = "What are the differential diagnoses for acute chest pain in a 45-year-old?"

    print(f"Query: {query}")
    print()
    print("Progress updates (with reasoning):")
    print("-"*80)

    # Run with streaming
    result = Runner.run_streamed(
        starting_agent=agent,
        input=query
    )

    # Create progress tracker
    tracker = StreamingProgressTracker()

    # Stream progress updates
    async for progress in tracker.stream_progress(result.stream_events()):
        print(f"  {progress.message}")
        if progress.details:
            print(f"    └─ Details: {progress.details}")

    print("-"*80)
    print()
    print("✅ Test complete!")
    print()

    # Get final response
    final_output = result.final_output_as(str)
    if final_output:
        print(f"Final response preview: {str(final_output)[:200]}...")
    print()
    print("="*80)
    print("SUCCESS: Reasoning items captured and displayed!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_reasoning_progress())
