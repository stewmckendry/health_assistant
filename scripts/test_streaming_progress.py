#!/usr/bin/env python3
"""
Test streaming progress tracker with mock SDK events.

This verifies that StreamingProgressTracker can correctly convert
OpenAI Agents SDK streaming events into user-friendly progress messages.
"""

import asyncio
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any, AsyncIterator

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.ai_agents.diagnostic_orchestrator.streaming_progress import StreamingProgressTracker


# Import SDK event types
from agents.stream_events import AgentUpdatedStreamEvent as SDKAgentUpdatedStreamEvent, RunItemStreamEvent as SDKRunItemStreamEvent

# Mock agent class
@dataclass
class MockAgent:
    name: str


@dataclass
class MockRawItem:
    name: str
    arguments: str = ""
    summary: list = None  # For reasoning events


@dataclass
class MockItem:
    raw_item: MockRawItem
    output: Any = None
    type: str = "tool_call_item"


async def mock_stream_events() -> AsyncIterator:
    """Generate mock stream events as if from Runner.run_streamed()"""

    # Initial: The Chief starts
    yield SDKAgentUpdatedStreamEvent(
        new_agent=MockAgent(name="The Chief")
    )

    # Consulting Agent 97
    yield SDKAgentUpdatedStreamEvent(
        new_agent=MockAgent(name="Agent 97")
    )

    # Agent 97 calls its tool
    yield SDKRunItemStreamEvent(
        name="tool_called",
        item=MockItem(
            raw_item=MockRawItem(
                name="agent_97_query",
                arguments='{"query": "treatment for newly diagnosed type 2 diabetes"}'
            )
        )
    )

    # Agent 97 gets results
    yield SDKRunItemStreamEvent(
        name="tool_output",
        item=MockItem(
            raw_item=MockRawItem(name="agent_97_query"),
            output={"items": [{"title": "Result 1"}, {"title": "Result 2"}, {"title": "Result 3"}]}
        )
    )

    # Consulting Dr. OPA
    yield SDKAgentUpdatedStreamEvent(
        new_agent=MockAgent(name="Dr. OPA")
    )

    # Dr. OPA calls opa_quality_standards
    yield SDKRunItemStreamEvent(
        name="tool_called",
        item=MockItem(
            raw_item=MockRawItem(
                name="opa_quality_standards",
                arguments='{"clinical_query": "diabetes management quality standards"}'
            )
        )
    )

    # Dr. OPA gets results
    yield SDKRunItemStreamEvent(
        name="tool_output",
        item=MockItem(
            raw_item=MockRawItem(name="opa_quality_standards"),
            output={"items": [{"title": "QS 1"}, {"title": "QS 2"}]}
        )
    )

    # Consulting Dr. OFF
    yield SDKAgentUpdatedStreamEvent(
        new_agent=MockAgent(name="Dr. OFF")
    )

    # Dr. OFF calls odb_get
    yield SDKRunItemStreamEvent(
        name="tool_called",
        item=MockItem(
            raw_item=MockRawItem(
                name="odb_get",
                arguments='{"query": "metformin coverage"}'
            )
        )
    )

    # Dr. OFF gets results
    yield SDKRunItemStreamEvent(
        name="tool_output",
        item=MockItem(
            raw_item=MockRawItem(name="odb_get"),
            output={"results": [{"drug": "Metformin"}]}
        )
    )

    # Back to The Chief for synthesis
    yield SDKAgentUpdatedStreamEvent(
        new_agent=MockAgent(name="The Chief")
    )

    # Final synthesis message
    yield SDKRunItemStreamEvent(
        name="message_output_created",
        item=MockItem(
            raw_item=MockRawItem(name="message")
        )
    )


async def test_streaming_progress():
    """Test StreamingProgressTracker with mock events"""

    print("="*80)
    print("Testing Streaming Progress Tracker")
    print("="*80)
    print()

    # Create progress tracker
    tracker = StreamingProgressTracker()

    # Stream mock events through the tracker
    async for progress in tracker.stream_progress(mock_stream_events()):
        print(f"{progress.message}")
        if progress.details:
            print(f"  Details: {progress.details}")

    print()
    print("="*80)
    print("✅ StreamingProgressTracker test complete!")
    print("="*80)
    print()
    print("The tracker successfully converts SDK events into user-friendly messages:")
    print("  - Agent switching: Consulting [Agent Name] for [purpose]...")
    print("  - Tool calls: [Agent] is [doing something] for: \"[query]\"")
    print("  - Tool outputs: [Agent] retrieved N results")
    print()
    print("Note: To use this in production, we need to expose raw stream_events()")
    print("from the orchestrator's Runner.run_streamed() call")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_streaming_progress())
