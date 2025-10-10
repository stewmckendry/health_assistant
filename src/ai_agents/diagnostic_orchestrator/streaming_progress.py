"""
Streaming Progress Tracker for The Chief

Converts OpenAI Agents SDK streaming events into user-friendly progress updates
that can be displayed in the UI to show what's happening during the 80+ second wait.

Example output:
- "🔍 Analyzing your clinical query..."
- "👨‍⚕️ Consulting Agent 97 for evidence-based clinical guidance from trusted medical sources..."
- "📊 Agent 97 is searching 97 trusted medical sources for clinical evidence..."
- "✅ Agent 97 retrieved 15 results"
- "🏥 Consulting Dr. OPA for Ontario clinical pathways and quality standards..."
- "🔧 Dr. OPA is looking up clinical decision tools..."
- etc.
"""

import json
from typing import AsyncIterator, Dict, Any
from dataclasses import dataclass

from agents.stream_events import StreamEvent, RunItemStreamEvent, AgentUpdatedStreamEvent


@dataclass
class ProgressUpdate:
    """User-friendly progress update"""
    message: str
    """Human-readable message describing what's happening"""

    event_type: str
    """Type of event (agent_switched, tool_called, tool_output, message_created)"""

    agent_name: str | None = None
    """Which agent is involved"""

    tool_name: str | None = None
    """Which tool is being called"""

    details: Dict[str, Any] | None = None
    """Additional structured data"""


class StreamingProgressTracker:
    """Converts SDK streaming events into user-friendly progress updates"""

    # Agent name mappings
    AGENT_DISPLAY_NAMES = {
        "The Chief": "The Chief (Clinical Intelligence Orchestrator)",
        "Dr. OPA": "Dr. OPA",
        "Dr. OFF": "Dr. OFF",
        "Agent 97": "Agent 97",
    }

    # Agent emojis for visual distinction
    AGENT_EMOJIS = {
        "The Chief": "🎯",
        "Dr. OPA": "🏥",
        "Dr. OFF": "💰",
        "Agent 97": "👨‍⚕️",
    }

    # Tool descriptions for Dr. OPA
    OPA_TOOL_DESCRIPTIONS = {
        "opa_search_sections": "searching Ontario practice guidance",
        "opa_policy_check": "checking CPSO policies",
        "opa_program_lookup": "looking up Ontario Health programs",
        "opa_ipac_guidance": "retrieving infection prevention and control guidance",
        "opa_clinical_tools": "finding clinical decision support tools",
        "opa_quality_standards": "reviewing Ontario Health quality standards",
        "opa_choosing_wisely": "checking Choosing Wisely recommendations",
        "web_search": "searching trusted Ontario healthcare websites",
    }

    # Tool descriptions for Dr. OFF
    OFF_TOOL_DESCRIPTIONS = {
        "schedule_get": "searching OHIP billing codes",
        "odb_get": "checking ODB drug formulary coverage",
        "adp_get": "reviewing Assistive Devices Program funding",
        "web_search": "searching trusted Ontario healthcare websites",
    }

    # Tool descriptions for Agent 97
    AGENT_97_TOOL_DESCRIPTIONS = {
        "clinician_search": "searching 97 trusted medical sources for clinical evidence",
        "clinician_search_get_domains": "retrieving list of trusted medical domains",
        "clinician_search_health_check": "checking clinical search service health",
        "web_search": "searching trusted medical sources",
    }

    # Tool descriptions for Chief's agent consultations
    ORCHESTRATOR_TOOL_DESCRIPTIONS = {
        "Dr. OPA": "calling Dr. OPA",
        "Dr. OFF": "calling Dr. OFF",
        "Agent 97": "calling Agent 97",
    }

    def __init__(self):
        self.current_agent = "The Chief"
        self.tool_call_count = 0

    def get_agent_emoji(self, agent_name: str) -> str:
        """Get emoji for agent"""
        return self.AGENT_EMOJIS.get(agent_name, "🤖")

    def get_tool_description(self, tool_name: str) -> str:
        """Get user-friendly description of what a tool does"""
        # Try each tool dictionary
        for tool_dict in [
            self.OPA_TOOL_DESCRIPTIONS,
            self.OFF_TOOL_DESCRIPTIONS,
            self.AGENT_97_TOOL_DESCRIPTIONS,
            self.ORCHESTRATOR_TOOL_DESCRIPTIONS
        ]:
            if tool_name in tool_dict:
                return tool_dict[tool_name]

        # Fallback: humanize the tool name
        return tool_name.replace("_", " ")

    def get_query_from_arguments(self, arguments_str: str) -> str | None:
        """Extract the query from tool call arguments"""
        try:
            args = json.loads(arguments_str)
            # Common query parameter names (including 'q' for web_search)
            for key in ['query', 'q', 'clinical_query', 'question', 'input']:
                if key in args:
                    return args[key]  # No truncation
        except:
            pass
        return None

    async def stream_progress(
        self,
        stream_events: AsyncIterator[StreamEvent]
    ) -> AsyncIterator[ProgressUpdate]:
        """
        Convert SDK streaming events into user-friendly progress updates

        Args:
            stream_events: Async iterator of StreamEvent from Runner.run_streamed()

        Yields:
            ProgressUpdate objects with user-friendly messages
        """
        # Yield initial message
        yield ProgressUpdate(
            message="🔍 Analyzing your clinical query...",
            event_type="analysis_started",
            agent_name="The Chief"
        )

        async for event in stream_events:
            # Agent switched
            if isinstance(event, AgentUpdatedStreamEvent):
                agent_name = event.new_agent.name
                self.current_agent = agent_name
                emoji = self.get_agent_emoji(agent_name)

                # Create user-friendly message based on agent
                if agent_name == "Agent 97":
                    message = f"{emoji} Consulting Agent 97 for evidence-based clinical guidance from trusted medical sources..."
                elif agent_name == "Dr. OPA":
                    message = f"{emoji} Consulting Dr. OPA for Ontario clinical pathways and quality standards..."
                elif agent_name == "Dr. OFF":
                    message = f"{emoji} Consulting Dr. OFF for coverage and billing information..."
                else:
                    message = f"{emoji} Switched to {agent_name}..."

                yield ProgressUpdate(
                    message=message,
                    event_type="agent_switched",
                    agent_name=agent_name
                )

            # Tool call or output
            elif isinstance(event, RunItemStreamEvent):
                # Tool being called
                if event.name == "tool_called":
                    if hasattr(event.item, 'raw_item') and hasattr(event.item.raw_item, 'name'):
                        tool_name = event.item.raw_item.name
                        tool_desc = self.get_tool_description(tool_name)
                        emoji = self.get_agent_emoji(self.current_agent)

                        # Try to get the query argument
                        query = None
                        if hasattr(event.item.raw_item, 'arguments'):
                            query = self.get_query_from_arguments(event.item.raw_item.arguments)

                        # Build message
                        if query:
                            message = f"{emoji} {self.current_agent} is {tool_desc} for: \"{query}\""
                        else:
                            message = f"{emoji} {self.current_agent} is {tool_desc}..."

                        self.tool_call_count += 1

                        yield ProgressUpdate(
                            message=message,
                            event_type="tool_called",
                            agent_name=self.current_agent,
                            tool_name=tool_name,
                            details={"query": query} if query else None
                        )

                # Tool output received
                elif event.name == "tool_output":
                    emoji = "✅"

                    # Try to extract meaningful info from output
                    result_count = None
                    if hasattr(event.item, 'output'):
                        output = event.item.output
                        if isinstance(output, dict):
                            # Check for common result count fields
                            if 'items' in output and isinstance(output['items'], list):
                                result_count = len(output['items'])
                            elif 'results' in output and isinstance(output['results'], list):
                                result_count = len(output['results'])

                    if result_count is not None:
                        message = f"{emoji} {self.current_agent} retrieved {result_count} results"
                    else:
                        message = f"{emoji} {self.current_agent} completed search"

                    yield ProgressUpdate(
                        message=message,
                        event_type="tool_output",
                        agent_name=self.current_agent,
                        details={"result_count": result_count} if result_count else None
                    )

                # Reasoning output (o1/o3/o4 models or agents using reasoning)
                elif event.name == "reasoning_item_created":
                    if hasattr(event.item, 'raw_item'):
                        reasoning_item = event.item.raw_item

                        # Try to extract summary text
                        reasoning_text = None

                        # Check if summary exists and has content
                        if hasattr(reasoning_item, 'summary') and reasoning_item.summary:
                            # summary is a list of Summary objects with text attribute
                            summaries = []
                            for summary in reasoning_item.summary:
                                if hasattr(summary, 'text') and summary.text:
                                    summaries.append(summary.text)
                            if summaries:
                                reasoning_text = " ".join(summaries)

                        # Skip empty reasoning items (status='in_progress' with no summary yet)
                        # Only emit progress when we have actual reasoning content
                        if not reasoning_text:
                            continue  # Skip this event, don't yield anything

                        emoji = "🤔"
                        # Truncate long reasoning
                        if len(reasoning_text) > 100:
                            reasoning_text = reasoning_text[:97] + "..."
                        message = f"{emoji} {self.current_agent} reasoning: {reasoning_text}"

                        yield ProgressUpdate(
                            message=message,
                            event_type="reasoning",
                            agent_name=self.current_agent,
                            details={"reasoning": reasoning_text}
                        )

                # Message being generated (final synthesis)
                elif event.name == "message_output_created":
                    yield ProgressUpdate(
                        message="✍️ The Chief is synthesizing insights from all specialists...",
                        event_type="synthesis_started",
                        agent_name="The Chief"
                    )
