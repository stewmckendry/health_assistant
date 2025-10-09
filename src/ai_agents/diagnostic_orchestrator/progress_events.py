"""
Custom Progress Events for Nested Agent Tool Calls

Since OpenAI Agents SDK doesn't expose nested tool calls through streaming
(issue #864), we use a custom event queue that sub-agents can push to.

This allows us to show granular progress like:
- "Dr. OFF is searching OHIP billing codes for: diabetes management"
- "Found 3 billing codes"
- "Dr. OFF is checking ODB formulary for: metformin"
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, AsyncIterator
from datetime import datetime


@dataclass
class SubAgentProgressEvent:
    """Progress event emitted by a sub-agent during tool execution"""

    agent_name: str
    """Which agent emitted this (Dr. OPA, Dr. OFF, Agent 97)"""

    event_type: str
    """Type: tool_start, tool_progress, tool_complete"""

    tool_name: str
    """MCP tool being called (opa_clinical_tools, schedule_get, etc.)"""

    message: str
    """User-friendly message"""

    query: Optional[str] = None
    """Query/input to the tool if available"""

    result_count: Optional[int] = None
    """Number of results returned"""

    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ProgressEventQueue:
    """
    Thread-safe queue for sub-agents to emit progress events.

    Usage in sub-agent:
        async def query(self, question: str):
            # Emit event when starting tool call
            await progress_queue.put(SubAgentProgressEvent(
                agent_name="Dr. OFF",
                event_type="tool_start",
                tool_name="schedule_get",
                message="Searching OHIP billing codes",
                query=question
            ))

            # Call the actual tool
            result = await self.call_schedule_get(question)

            # Emit completion event
            await progress_queue.put(SubAgentProgressEvent(
                agent_name="Dr. OFF",
                event_type="tool_complete",
                tool_name="schedule_get",
                message="Found billing codes",
                result_count=len(result.get('items', []))
            ))
    """

    def __init__(self):
        self._queue: asyncio.Queue[SubAgentProgressEvent] = asyncio.Queue()
        self._active = True

    async def put(self, event: SubAgentProgressEvent):
        """Sub-agents call this to emit progress"""
        if self._active:
            await self._queue.put(event)

    async def get(self) -> SubAgentProgressEvent:
        """Orchestrator calls this to receive progress"""
        return await self._queue.get()

    def try_get_nowait(self) -> Optional[SubAgentProgressEvent]:
        """Non-blocking get"""
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def stream_events(self) -> AsyncIterator[SubAgentProgressEvent]:
        """Stream all events until queue is closed"""
        while self._active or not self._queue.empty():
            try:
                # Wait with timeout so we can check _active flag
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                yield event
            except asyncio.TimeoutError:
                continue

    def close(self):
        """Signal that no more events will be emitted"""
        self._active = False

    def is_empty(self) -> bool:
        """Check if there are pending events"""
        return self._queue.empty()


# Global queue that all agents can access
# This is a singleton pattern - there's one queue per orchestrator session
_global_queue: Optional[ProgressEventQueue] = None


def get_progress_queue() -> ProgressEventQueue:
    """Get or create the global progress queue"""
    global _global_queue
    if _global_queue is None:
        _global_queue = ProgressEventQueue()
    return _global_queue


def reset_progress_queue():
    """Reset the global queue (call at start of new orchestration)"""
    global _global_queue
    if _global_queue:
        _global_queue.close()
    _global_queue = ProgressEventQueue()
    return _global_queue
