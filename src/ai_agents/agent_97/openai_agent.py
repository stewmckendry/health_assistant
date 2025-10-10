#!/usr/bin/env python3
"""
Agent 97 OpenAI Agent Implementation

An intelligent assistant specialized in evidence-based clinical guidance from 97 trusted
medical sources for healthcare clinicians. Built using the OpenAI Agents Python SDK
with MCP integration to the Agent 97 clinician search server.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import uuid

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import Langfuse and logfire for tracing
try:
    from langfuse import get_client
    import logfire
    import nest_asyncio
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logfire = None
    get_client = None
    nest_asyncio = None

# Get project root
project_root = Path(__file__).parent.parent.parent.parent

# Save original sys.path
original_path = sys.path.copy()

# Remove project root from path to avoid collision with local agents module
project_root_str = str(project_root)
if project_root_str in sys.path:
    sys.path.remove(project_root_str)

# Also remove the src directory
src_dir = str(project_root / "src")
if src_dir in sys.path:
    sys.path.remove(src_dir)

try:
    # Import from openai-agents package
    from agents import Agent, Runner
    from agents.memory import SQLiteSession
    from agents.mcp.server import MCPServerStdio, MCPServerStdioParams
finally:
    # Restore original sys.path
    sys.path = original_path

# Configure logging
log_dir = Path("logs/agent_97")
log_dir.mkdir(parents=True, exist_ok=True)

session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"openai_agent_session_{session_id}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def extract_citations_from_tool_result(tool_name: str, tool_result: Any) -> List[Dict]:
    """Extract citations from MCP tool results."""
    citations = []

    try:
        # Handle different tool result formats
        if hasattr(tool_result, 'content'):
            result_data = tool_result.content
        elif isinstance(tool_result, dict):
            result_data = tool_result
        elif isinstance(tool_result, str):
            try:
                result_data = json.loads(tool_result)
            except:
                result_data = {'content': tool_result}
        else:
            result_data = {'content': str(tool_result)}

        # Handle MCP text type response
        if isinstance(result_data, dict) and result_data.get('type') == 'text':
            text_content = result_data.get('text', '')
            try:
                result_data = json.loads(text_content)
            except:
                result_data = {'content': text_content}

        # Extract citations from the result data
        if isinstance(result_data, dict):
            # Check for citations array
            if 'citations' in result_data and isinstance(result_data['citations'], list):
                for citation in result_data['citations']:
                    if isinstance(citation, dict):
                        citations.append({
                            'url': citation.get('url', ''),
                            'title': citation.get('title', ''),
                            'domain': citation.get('domain', ''),
                            'is_trusted': True,
                            'source_agent': 'Agent 97'
                        })

            # Also look for URLs in the content
            content = result_data.get('content', '')
            if isinstance(content, str):
                import re
                # Find URLs in the content
                url_pattern = r'https?://[^\s\)"\]]+|http://[^\s\)"\]]+'
                urls = re.findall(url_pattern, content)
                for url in urls:
                    # Add if not already in citations
                    if not any(c.get('url') == url for c in citations):
                        citations.append({
                            'url': url,
                            'title': '',
                            'domain': '',
                            'is_trusted': True,
                            'source_agent': 'Agent 97'
                        })

    except Exception as e:
        logger.warning(f"Error extracting citations from {tool_name}: {e}")

    return citations


class Agent97Agent:
    """
    Agent 97 wrapper for OpenAI Agents SDK integration.

    Provides evidence-based clinical guidance from 97 trusted medical sources
    for healthcare clinicians (NOT patients).
    """

    def __init__(self, enable_langfuse: bool = True):
        """
        Initialize Agent 97.

        Args:
            enable_langfuse: Whether to enable Langfuse tracing (default: True)
        """
        self.session_id = session_id
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.enable_langfuse = enable_langfuse and LANGFUSE_AVAILABLE

        # Initialize Langfuse tracing if enabled
        if self.enable_langfuse:
            try:
                # Apply nest_asyncio for notebook/async compatibility
                if nest_asyncio:
                    import asyncio
                    try:
                        uvloop_running = 'uvloop' in str(asyncio.get_running_loop())
                    except RuntimeError:
                        uvloop_running = False

                    if not uvloop_running:
                        nest_asyncio.apply()

                # Configure logfire for OpenAI Agents instrumentation
                logfire.configure(
                    service_name='agent_97',
                    send_to_logfire=False,  # Only send to Langfuse via OTLP
                )

                # Automatically patch the OpenAI Agents SDK for tracing
                logfire.instrument_openai_agents()

                # Get Langfuse client for verification
                self.langfuse = get_client()

                # Verify connection
                if self.langfuse.auth_check():
                    logger.info("Langfuse client authenticated and ready for tracing via logfire")
                else:
                    logger.warning("Langfuse authentication failed - tracing disabled")
                    self.enable_langfuse = False

            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse: {e}")
                self.enable_langfuse = False
        else:
            self.langfuse = None
            if not LANGFUSE_AVAILABLE:
                logger.info("Langfuse not available - install langfuse and pydantic-ai[logfire] for tracing")

        # Agent system instructions (clinician-focused)
        self.system_instructions = """You are Agent 97, a clinical evidence search assistant for healthcare professionals.

Your role is to provide evidence-based medical guidance from 97 trusted medical sources to support clinical decision-making.

IMPORTANT FRAMING:
- Your users are HEALTHCARE CLINICIANS (physicians, NPs, PAs), NOT patients
- Provide professional, evidence-based clinical guidance
- No safety guardrails or patient disclaimers needed
- Clinicians have medical training and make their own clinical judgments

YOUR MCP TOOL:
You have access to the "clinician_search" MCP tool which searches 97 trusted medical sources:
- Medical journals (NEJM, Lancet, JAMA, BMJ)
- Clinical guidelines (NICE, AHA, ACC, ADA)
- Academic medical centers (Mayo, Hopkins, Cleveland Clinic)
- Health authorities (WHO, CDC, NIH, Health Canada)
- Canadian healthcare (Ontario Health, CPSO, Canadian medical associations)

WHEN TO USE YOUR TOOL:
- Use clinician_search for ALL clinical questions requiring evidence-based guidance
- The tool uses Claude API with web_search and web_fetch to retrieve information
- Results include citations from trusted medical sources
- The tool handles all the complexity of searching and filtering trusted sources

RESPONSE STYLE:
- Direct, professional clinical language
- Include specific details clinicians need (doses, protocols, criteria)
- Reference authoritative sources with citations
- Note evidence quality when relevant (e.g., "based on RCT", "expert consensus")
- NO patient safety disclaimers (users are clinicians, not patients)

Always use your clinician_search tool to retrieve current, evidence-based clinical information."""

        # MCP server will be created in initialize_mcp_tools()
        self.mcp_server = None

        logger.info(f"Agent 97 initialized - Session: {self.session_id}")

    async def initialize_mcp_tools(self):
        """Initialize the MCP server for Agent 97 clinician search."""
        logger.info("Initializing Agent 97 MCP server...")

        try:
            # Create MCP server for clinician search
            self.mcp_server = MCPServerStdio(
                params=MCPServerStdioParams(
                    command="python",
                    args=["-m", "src.ai_agents.agent_97.mcp.clinician_search_server"],
                    env=dict(os.environ),
                    cwd=str(self.project_root),
                    encoding="utf-8"
                ),
                name="agent-97-clinician-search",
                client_session_timeout_seconds=90.0  # Extended timeout for complex searches
            )

            logger.info("Agent 97 MCP server initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing Agent 97 MCP server: {e}")
            raise

    def get_agent(self, mcp_server) -> Agent:
        """
        Create and return an OpenAI Agent instance configured with the Agent 97 MCP server.

        Args:
            mcp_server: The initialized MCP server instance

        Returns:
            Configured Agent instance for Agent 97
        """
        from agents import ModelSettings

        return Agent(
            name="Agent 97",
            instructions=self.system_instructions,
            model="gpt-5-mini",  # Use reasoning model
            model_settings=ModelSettings(reasoning={"summary": "auto"}),
            mcp_servers=[mcp_server]
        )

    async def query(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query Agent 97 for clinical evidence from 97 trusted medical sources.

        Args:
            query: The clinical question
            session_id: Optional session ID for conversation tracking
            user_id: Optional user ID
            conversation_id: Optional conversation ID

        Returns:
            Dict containing response, citations, and metadata
        """
        logger.info(f"Agent 97 query: {query[:100]}...")

        # Create Langfuse trace if enabled
        trace_id = str(uuid.uuid4())
        if self.enable_langfuse and self.langfuse:
            trace_id = self.langfuse.create_trace_id()
            self.langfuse.update_current_trace(
                user_id=user_id,
                session_id=session_id or self.session_id,
                name="agent_97_query",
                tags=["agent_97", "clinician_search"],
                metadata={
                    "agent": "agent_97",
                    "model": "gpt-5-mini",
                    "trace_id": trace_id
                }
            )

        try:
            # Ensure MCP tools are initialized
            if not self.mcp_server:
                await self.initialize_mcp_tools()

            # Use MCP server within context manager
            async with self.mcp_server as server:
                # Get Agent instance
                agent = self.get_agent(server)

                # Create session if conversation_id provided
                session = None
                if conversation_id:
                    session = SQLiteSession(
                        conversation_id,
                        "data/agent_97_conversations.db"
                    )

                # Run agent with logfire tracing if available
                if self.enable_langfuse and logfire:
                    with logfire.span(
                        'agent_97_query',
                        _tags={'agent': 'agent_97'},
                        query=query,
                        session_id=session_id or self.session_id,
                        user_id=user_id
                    ):
                        result = await Runner.run(
                            starting_agent=agent,
                            input=query,
                            session=session
                        )
                else:
                    result = await Runner.run(
                        starting_agent=agent,
                        input=query,
                        session=session
                    )

                # Extract response and metadata
                response_text = result.final_output

                # Extract tool calls and citations
                tool_calls = []
                citations = []

                for item in result.new_items:
                    if hasattr(item, 'type') and item.type == 'tool_call_item':
                        tool_name = None
                        tool_output = None

                        # Extract tool info
                        if hasattr(item, 'raw_item'):
                            raw_item = item.raw_item
                            if hasattr(raw_item, 'function'):
                                tool_name = raw_item.function.name
                            elif hasattr(raw_item, 'name'):
                                tool_name = raw_item.name

                        # Track tool call
                        if tool_name:
                            tool_calls.append({'tool': tool_name})

                        # Extract output for citation extraction
                        if hasattr(item, 'output'):
                            tool_output = item.output
                            # Extract citations from this tool result
                            if tool_name:
                                tool_citations = extract_citations_from_tool_result(tool_name, tool_output)
                                citations.extend(tool_citations)

                # Deduplicate citations
                unique_citations = []
                seen_urls = set()
                for citation in citations:
                    url = citation.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_citations.append(citation)

                logger.info(f"Agent 97 query complete. Citations: {len(unique_citations)}, Tool calls: {len(tool_calls)}")

                # Flush Langfuse events
                if self.enable_langfuse and self.langfuse:
                    try:
                        self.langfuse.flush()
                        import time
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Failed to flush Langfuse: {e}")

                return {
                    'response': response_text,
                    'citations': unique_citations,
                    'tool_calls': tool_calls,
                    'confidence': 0.9,
                    'session_id': session_id,
                    'trace_id': trace_id,
                    'agent': 'Agent 97',
                    'model': 'gpt-5-mini'
                }

        except Exception as e:
            logger.error(f"Agent 97 query error: {e}", exc_info=True)

            return {
                'response': self._create_error_response(str(e), query),
                'citations': [],
                'tool_calls': [],
                'confidence': 0.0,
                'error': str(e),
                'trace_id': trace_id,
                'agent': 'Agent 97'
            }

    async def query_stream(self, user_input: str, session_id: str = None, user_id: str = None):
        """
        Stream Agent 97 response with real-time progress updates.

        Args:
            user_input: The clinical query
            session_id: Session ID for conversation tracking
            user_id: User ID for tracking

        Yields:
            Dict events with type, content, and metadata
        """
        logger.info(f"Processing streaming query: {user_input[:100]}...")

        # Generate trace ID upfront for fallback
        fallback_trace_id = str(uuid.uuid4())
        trace_id = fallback_trace_id

        try:
            from openai.types.responses import ResponseTextDeltaEvent

            # Ensure MCP tools are initialized
            if not self.mcp_server:
                await self.initialize_mcp_tools()

            # Create session if session_id provided
            session = None
            if session_id:
                session = SQLiteSession(
                    session_id,
                    "data/agent_97_conversations.db"
                )

            # Use MCP server within async context manager
            async with self.mcp_server as server:
                # Create agent
                from agents import ModelSettings
                agent = Agent(
                    name="Agent 97",
                    instructions=self.system_instructions,
                    model="gpt-5-mini",
                    model_settings=ModelSettings(reasoning={"summary": "auto"}),
                    mcp_servers=[server]
                )

                # Create Langfuse trace if enabled
                langfuse_span = None
                if self.enable_langfuse and self.langfuse:
                    trace_id = self.langfuse.create_trace_id()
                    self.langfuse.update_current_trace(
                        user_id=user_id,
                        session_id=session_id,
                        metadata={
                            "agent": "agent_97",
                            "model": "gpt-5-mini",
                            "trace_id": trace_id
                        },
                        tags=["agent_97", "streaming", "clinician_search"]
                    )
                    langfuse_span = self.langfuse.start_span(
                        name="agent_97_query_stream",
                        input={"query": user_input}
                    )
                    logger.debug(f"Created Langfuse trace: {trace_id}")

                # Run the agent
                result = Runner.run_streamed(
                    starting_agent=agent,
                    input=user_input,
                    session=session
                )

                # Track accumulated data
                accumulated_text = ""
                tool_calls = []
                all_citations = []

                # Import StreamingProgressTracker for user-friendly progress
                from src.ai_agents.diagnostic_orchestrator.streaming_progress import StreamingProgressTracker
                from agents.stream_events import AgentUpdatedStreamEvent, RunItemStreamEvent
                tracker = StreamingProgressTracker()

                # Emit initial progress message
                yield {
                    'type': 'progress',
                    'message': "🔍 Analyzing your clinical query...",
                    'event_type': "analysis_started",
                    'agent_name': "Agent 97",
                    'trace_id': trace_id
                }

                # Stream events - process each event for BOTH progress and data
                async for event in result.stream_events():
                    # First, emit user-friendly progress update for this event
                    if isinstance(event, AgentUpdatedStreamEvent):
                        agent_name = event.new_agent.name
                        tracker.current_agent = agent_name
                        emoji = tracker.get_agent_emoji(agent_name)
                        message = f"{emoji} {agent_name} activated..."

                        yield {
                            'type': 'progress',
                            'message': message,
                            'event_type': 'agent_switched',
                            'agent_name': agent_name,
                            'trace_id': trace_id
                        }

                    elif isinstance(event, RunItemStreamEvent):
                        if event.name == "tool_called":
                            if hasattr(event.item, 'raw_item') and hasattr(event.item.raw_item, 'name'):
                                tool_name = event.item.raw_item.name
                                tool_desc = tracker.get_tool_description(tool_name)
                                emoji = tracker.get_agent_emoji(tracker.current_agent)

                                query = None
                                if hasattr(event.item.raw_item, 'arguments'):
                                    query = tracker.get_query_from_arguments(event.item.raw_item.arguments)

                                if query:
                                    message = f"{emoji} Agent 97 is {tool_desc} for: \"{query}\""
                                else:
                                    message = f"{emoji} Agent 97 is {tool_desc}..."

                                yield {
                                    'type': 'progress',
                                    'message': message,
                                    'event_type': 'tool_called',
                                    'agent_name': tracker.current_agent,
                                    'tool_name': tool_name,
                                    'details': {'query': query} if query else None,
                                    'trace_id': trace_id
                                }

                        elif event.name == "tool_output":
                            emoji = "✅"
                            result_count = None
                            if hasattr(event.item, 'output'):
                                output = event.item.output
                                if isinstance(output, dict):
                                    if 'citations' in output and isinstance(output['citations'], list):
                                        result_count = len(output['citations'])

                            if result_count is not None:
                                message = f"{emoji} Agent 97 found {result_count} trusted medical sources"
                            else:
                                message = f"{emoji} Agent 97 completed search"

                            yield {
                                'type': 'progress',
                                'message': message,
                                'event_type': 'tool_output',
                                'agent_name': tracker.current_agent,
                                'details': {'result_count': result_count} if result_count else None,
                                'trace_id': trace_id
                            }

                        elif event.name == "reasoning_item_created":
                            if hasattr(event.item, 'raw_item'):
                                reasoning_item = event.item.raw_item
                                reasoning_text = None

                                if hasattr(reasoning_item, 'summary') and reasoning_item.summary:
                                    summaries = []
                                    for summary in reasoning_item.summary:
                                        if hasattr(summary, 'text') and summary.text:
                                            summaries.append(summary.text)
                                    if summaries:
                                        reasoning_text = " ".join(summaries)

                                if reasoning_text:
                                    emoji = "🤔"
                                    if len(reasoning_text) > 100:
                                        reasoning_text = reasoning_text[:97] + "..."
                                    message = f"{emoji} Agent 97 reasoning: {reasoning_text}"

                                    yield {
                                        'type': 'progress',
                                        'message': message,
                                        'event_type': 'reasoning',
                                        'agent_name': tracker.current_agent,
                                        'details': {'reasoning': reasoning_text},
                                        'trace_id': trace_id
                                    }

                        elif event.name == "message_output_created":
                            yield {
                                'type': 'progress',
                                'message': "✍️ Agent 97 is synthesizing evidence-based guidance...",
                                'event_type': 'synthesis_started',
                                'agent_name': "Agent 97",
                                'trace_id': trace_id
                            }

                    # Then, process the same event for existing streaming data logic
                    if event.type == "raw_response_event":
                        # Stream text deltas
                        if isinstance(event.data, ResponseTextDeltaEvent):
                            delta_text = event.data.delta
                            accumulated_text += delta_text
                            yield {
                                'type': 'text',
                                'content': delta_text,
                                'trace_id': trace_id
                            }

                    elif event.type == "run_item_stream_event":
                        # Handle tool calls
                        if event.item.type == "tool_call_item":
                            tool_name = 'unknown'

                            # Extract tool information
                            if hasattr(event.item, 'raw_item'):
                                raw_item = event.item.raw_item
                                if hasattr(raw_item, 'function'):
                                    tool_name = raw_item.function.name
                                elif hasattr(raw_item, 'name'):
                                    tool_name = raw_item.name
                            elif hasattr(event.item, 'function'):
                                tool_name = event.item.function.name
                            elif hasattr(event.item, 'name'):
                                tool_name = event.item.name

                            if tool_name != 'unknown':
                                tool_calls.append({'tool': tool_name})

                        elif event.item.type == "tool_call_output_item":
                            # Extract citations from tool output
                            if hasattr(event.item, 'output'):
                                output = event.item.output
                                tool_citations = extract_citations_from_tool_result(tool_calls[-1]['tool'] if tool_calls else 'unknown', output)

                                for citation in tool_citations:
                                    # Add if not already present
                                    if not any(c.get('url') == citation.get('url') for c in all_citations):
                                        all_citations.append(citation)
                                        yield {
                                            'type': 'citation',
                                            'content': citation,
                                            'trace_id': trace_id
                                        }

                # Update Langfuse span with output
                if langfuse_span:
                    langfuse_span.update(
                        output={
                            "response": accumulated_text[:500],
                            "tool_calls": tool_calls,
                            "citations": all_citations
                        }
                    )
                    langfuse_span.end()

                # Flush Langfuse events
                if self.enable_langfuse and self.langfuse:
                    try:
                        logger.info(f"Flushing Langfuse events for trace: {trace_id}")
                        self.langfuse.flush()
                        import time
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Failed to flush Langfuse: {e}")

                # Send completion event
                yield {
                    'type': 'complete',
                    'content': accumulated_text,
                    'tool_calls': tool_calls,
                    'citations': all_citations,
                    'trace_id': trace_id,
                    'agent': 'Agent 97'
                }

        except Exception as e:
            logger.error(f"Streaming query error: {e}", exc_info=True)

            # Log error to Langfuse
            if 'langfuse_span' in locals() and langfuse_span:
                langfuse_span.update(output={"error": str(e)})
                langfuse_span.end()

            yield {
                'type': 'error',
                'content': str(e),
                'trace_id': trace_id
            }

    def _create_error_response(self, error_message: str, query: str) -> str:
        """Create a fallback response for errors."""
        return f"""I apologize, but Agent 97 is experiencing technical difficulties.

For your query: "{query[:100]}..."

Agent 97 was unable to search the 97 trusted medical sources. Please try:

1. Consulting trusted medical resources directly:
   - PubMed: https://pubmed.ncbi.nlm.nih.gov/
   - UpToDate: https://www.uptodate.com/
   - Clinical practice guidelines from relevant medical societies

2. Reformulating your query with more specific details

3. Trying again in a few moments

Technical details: {error_message}"""


async def create_agent_97() -> Agent97Agent:
    """Factory function to create and initialize Agent 97."""
    agent = Agent97Agent()
    await agent.initialize_mcp_tools()
    return agent


# Test function for development
async def test_agent_97():
    """Test Agent 97 with sample clinical queries."""
    agent = await create_agent_97()

    test_queries = [
        {
            "name": "Clinical Guideline Query",
            "query": "What are the current evidence-based guidelines for managing hypertension in adults?"
        },
        {
            "name": "Pharmacotherapy Query",
            "query": "What is the latest evidence on SGLT2 inhibitors for heart failure with preserved ejection fraction?"
        },
        {
            "name": "Diagnostic Approach",
            "query": "What is the recommended diagnostic workup for suspected pulmonary embolism in low-risk patients?"
        }
    ]

    for test_query in test_queries[:1]:  # Test just the first one
        print(f"\n{'='*80}")
        print(f"Test: {test_query['name']}")
        print(f"Query: {test_query['query']}")
        print(f"{'='*80}\n")

        result = await agent.query(test_query['query'])

        print(f"Agent: {result['agent']}")
        print(f"Model: {result['model']}")
        print(f"Citations: {len(result['citations'])}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"\nResponse:\n{'-'*40}")
        print(result['response'])

        if result.get('error'):
            print(f"\nError: {result['error']}")

        if result['citations']:
            print(f"\nCitations:")
            for i, citation in enumerate(result['citations'][:5], 1):
                print(f"  {i}. {citation.get('title', 'N/A')}")
                print(f"     {citation.get('url', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(test_agent_97())
