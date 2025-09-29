#!/usr/bin/env python3
"""
The Chief - Clinical Intelligence Orchestrator

An intelligent medical orchestrator inspired by Microsoft's MAI-DxO that coordinates
between the existing Dr. OPA, Dr. OFF, and Agent 97 implementations using the 
OpenAI Agents SDK's as_tool() pattern. Includes comprehensive Langfuse tracing.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator
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

# Set up path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Note: Agent implementations are imported in initialize() method to avoid circular imports

# Save original sys.path for SDK imports
original_path = sys.path.copy()

# Temporarily modify path to import openai-agents SDK
project_root_str = str(project_root)
if project_root_str in sys.path:
    sys.path.remove(project_root_str)
src_dir = str(project_root / "src")
if src_dir in sys.path:
    sys.path.remove(src_dir)

try:
    # Import OpenAI Agents SDK components
    from agents import Agent, Runner
    from agents.memory import SQLiteSession
    from agents.mcp.server import MCPServerStdio, MCPServerStdioParams
finally:
    # Restore original sys.path
    sys.path = original_path

# Configure logging
log_dir = Path("logs/diagnostic_orchestrator")
log_dir.mkdir(parents=True, exist_ok=True)

session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"orchestrator_session_{session_id}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DiagnosticOrchestrator:
    """
    The Chief - Clinical Intelligence Orchestrator inspired by Microsoft's MAI-DxO.
    
    Coordinates between the existing Dr. OPA, Dr. OFF, and Agent 97 implementations
    to provide comprehensive clinical guidance for Ontario healthcare providers.
    Includes Langfuse tracing for observability and user feedback.
    """
    
    def __init__(self, enable_langfuse: bool = True):
        """Initialize The Chief orchestrator with optional Langfuse tracing.
        
        Args:
            enable_langfuse: Whether to enable Langfuse tracing (default: True)
        """
        self.session_id = session_id
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.enable_langfuse = enable_langfuse and LANGFUSE_AVAILABLE
        
        # These will hold the agent instances
        self.dr_opa_wrapper = None
        self.dr_off_wrapper = None
        
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
                    service_name='chief_orchestrator',
                    send_to_logfire=False,  # Only send to Langfuse via OTLP
                )
                
                # Automatically patch the OpenAI Agents SDK for tracing
                logfire.instrument_openai_agents()
                
                # Get Langfuse client for verification and feedback
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
        
        # System instructions for the orchestrator
        self.system_instructions = """You are "The Chief" - the Chief Clinical Intelligence Orchestrator, an advanced medical coordination system inspired by Microsoft's MAI-DxO approach and named after the chief roles in medicine (Chief Medical Officer, Chief of Staff). You intelligently route queries to multiple specialist AI agents to provide comprehensive guidance for Ontario healthcare providers.

You have access to three specialized agents as tools:

1. **dr_opa**: Dr. OPA (Ontario Practice Advice) - Has MCP tools for CPSO policies, Ontario Health guidelines, clinical pathways, infection control, and CEP decision support. The agent will automatically use its tools: opa_search_sections, opa_get_section, opa_policy_check, opa_program_lookup, opa_ipac_guidance, opa_freshness_probe, opa_clinical_tools.

2. **dr_off**: Dr. OFF (Ontario Finance & Formulary) - Has MCP tools for OHIP billing codes, ODB drug formulary, and ADP device coverage. The agent will automatically use its tools: schedule_get, odb_get, adp_get.

3. **agent_97**: Agent 97 - Has MCP tool for querying 97 trusted medical sources with comprehensive safety guardrails. The agent will automatically use its tool: agent_97_query.

ORCHESTRATION STRATEGY:
- Analyze each clinical query to determine which specialist agents would provide the most valuable insights
- Call the appropriate agent tools based on the query's complexity and domains
- Each agent has its own specialized MCP tools that will be automatically used when you call them
- For regulatory/policy questions → Use dr_opa
- For cost/coverage questions → Use dr_off
- For general medical knowledge → Use agent_97
- For complex cases → Consult multiple specialists and synthesize their insights

IMPORTANT: When you call an agent tool, simply pass the clinical query to it. The agent will automatically:
- Use its own MCP tools to retrieve relevant information
- Process and format the response with citations
- Return comprehensive guidance in its domain

SYNTHESIS APPROACH:
When consulting multiple specialists:
1. Call each relevant agent with the clinical query
2. Each agent will provide their specialized response with citations
3. Integrate the responses into a cohesive clinical narrative
4. Preserve all citations and sources from individual agents
5. Highlight any conflicting information with context
6. Emphasize critical safety information and regulatory requirements

RESPONSE FORMAT:
- Start with a brief summary of the clinical scenario
- Provide integrated guidance organized by clinical relevance
- Include specific details (billing codes, drug DINs, policy references) from agents
- Maintain all citations with clear attribution to the source agent
- End with practical next steps and key takeaways
- Always include appropriate medical disclaimers

SAFETY REQUIREMENTS:
- Emphasize this is for educational purposes only
- Include medical disclaimers
- Highlight urgent/emergent situations requiring immediate action
- Note when consultation with specialists is recommended
- Preserve all safety warnings from individual agents

Remember: Each agent has its own MCP server and tools. You just need to call them - they will handle their specialized data retrieval automatically."""
        
        logger.info(f"Diagnostic Orchestrator initialized - Session: {self.session_id}")
    
    async def initialize(self):
        """Initialize the existing agent wrappers."""
        logger.info("Initializing existing agent wrappers...")
        
        try:
            # Initialize Dr. OPA wrapper - disable Langfuse to avoid conflicts
            from src.agents.dr_opa_agent.openai_agent import DrOPAAgent
            self.dr_opa_wrapper = DrOPAAgent(enable_langfuse=False)
            await self.dr_opa_wrapper.initialize_mcp_tools()
            logger.info("Dr. OPA wrapper initialized (Langfuse disabled for sub-agent)")
            
            # Initialize Dr. OFF wrapper - disable Langfuse to avoid conflicts
            from src.agents.dr_off_agent.openai_agent import DrOffAgent
            self.dr_off_wrapper = DrOffAgent(enable_langfuse=False)
            await self.dr_off_wrapper.initialize_mcp_tools()
            logger.info("Dr. OFF wrapper initialized (Langfuse disabled for sub-agent)")
            
            logger.info("All agent wrappers initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing agent wrappers: {e}")
            raise
    
    def _create_agent_97(self, mcp_server) -> Agent:
        """Create Agent 97 with its MCP server."""
        return Agent(
            name="Agent 97",
            instructions="""You are Agent 97, providing comprehensive medical education from 97 trusted medical sources with safety guardrails.

Use your MCP tool (agent_97_query) to access medical education information focusing on:
- Evidence-based clinical information about conditions
- Differential diagnosis considerations
- Treatment principles and management approaches
- Patient education materials
- Safety considerations and red flags

IMPORTANT:
- Always provide educational information only, NOT medical diagnosis
- Include appropriate medical disclaimers
- The MCP tool will automatically apply safety guardrails
- Citations from trusted sources will be included in the response

When using the agent_97_query tool, pass the clinical query directly and it will:
1. Apply input guardrails to ensure query safety
2. Search 97 trusted medical sources
3. Apply output guardrails to ensure response safety
4. Return educational content with appropriate disclaimers""",
            model="gpt-4o-mini",
            mcp_servers=[mcp_server]
        )
    
    async def orchestrate(self, clinical_query: str, session_id: str = None, user_id: str = None) -> Dict[str, Any]:
        """
        Process a clinical query by orchestrating between specialist agents with Langfuse tracing.
        
        Args:
            clinical_query: The clinical question or scenario
            session_id: Session ID for conversation tracking
            user_id: User ID for tracking
            
        Returns:
            Dict containing synthesized response and metadata including trace_id
        """
        logger.info(f"Orchestrating clinical query: {clinical_query[:100]}...")
        
        # Create Langfuse trace if enabled
        langfuse_span = None
        trace_id = str(uuid.uuid4())  # Always have a trace_id for fallback
        if self.enable_langfuse and self.langfuse:
            # Create a new trace ID
            trace_id = self.langfuse.create_trace_id()
            self.langfuse.update_current_trace(
                user_id=user_id,
                session_id=session_id or self.session_id,
                name="chief_orchestrate",  # Add name parameter
                tags=["orchestrator", "chief", "non-streaming"],  # Add tags
                metadata={
                    "agent": "chief_orchestrator",
                    "model": "gpt-4o",
                    "mode": "orchestration",
                    "trace_id": trace_id,  # Include trace_id in metadata
                    "parent_trace": "OpenAI_Agents_workflow"  # Link to auto-generated trace
                }
            )
            # Start a span for this orchestration
            langfuse_span = self.langfuse.start_span(
                name="chief_orchestrate",
                input={"query": clinical_query}
            )
            logger.debug(f"Created Langfuse trace: {trace_id}")
        
        try:
            # Ensure agents are initialized
            if not self.dr_opa_wrapper or not self.dr_off_wrapper:
                await self.initialize()
            
            # Create MCP server for Agent 97
            agent_97_mcp = MCPServerStdio(
                params=MCPServerStdioParams(
                    command="python",
                    args=["-m", "src.agents.agent_97.mcp.server"],
                    env=dict(os.environ),
                    cwd=str(self.project_root),
                    encoding="utf-8"
                ),
                name="agent-97-server",
                client_session_timeout_seconds=30.0
            )
            
            # Use MCP servers within context managers
            # Dr. OPA and Dr. OFF have their own MCP servers managed internally
            async with self.dr_opa_wrapper.mcp_server as opa_server, \
                       self.dr_off_wrapper.mcp_server as off_server, \
                       agent_97_mcp as a97_server:
                
                # Get Agent instances from the existing wrappers
                dr_opa_agent = self.dr_opa_wrapper.get_agent(opa_server)
                dr_off_agent = self.dr_off_wrapper.get_agent(off_server)
                agent_97_agent = self._create_agent_97(a97_server)
                
                # Convert agents to tools using as_tool()
                dr_opa_tool = dr_opa_agent.as_tool(
                    tool_name="dr_opa",
                    tool_description="Consult Dr. OPA for Ontario practice guidance, CPSO policies, clinical pathways, and regulatory requirements. Has access to MCP tools for retrieving official Ontario healthcare policies."
                )
                
                dr_off_tool = dr_off_agent.as_tool(
                    tool_name="dr_off",
                    tool_description="Consult Dr. OFF for Ontario healthcare financing, OHIP billing codes, ODB drug coverage, and ADP device funding. Has access to MCP tools for retrieving coverage and billing information."
                )
                
                agent_97_tool = agent_97_agent.as_tool(
                    tool_name="agent_97",
                    tool_description="Consult Agent 97 for comprehensive medical education from trusted sources. Has access to MCP tool for retrieving evidence-based clinical information with safety guardrails."
                )
                
                # Create the orchestrator agent with sub-agents as tools
                orchestrator = Agent(
                    name="The Chief",
                    instructions=self.system_instructions,
                    model="gpt-4o",  # Use more powerful model for orchestration
                    tools=[dr_opa_tool, dr_off_tool, agent_97_tool]
                )
                
                # Create session if provided
                session = None
                if session_id:
                    session = SQLiteSession(
                        session_id,
                        "data/orchestrator_conversations.db"
                    )
                
                # Run orchestration, wrapped in logfire span if available
                # This ensures the OpenAI Agents trace captures our input/output
                if self.enable_langfuse and logfire:
                    with logfire.span(
                        'chief_orchestration',
                        _tags={'streaming': 'false'},
                        clinical_query=clinical_query,
                        session_id=session_id or self.session_id,
                        user_id=user_id
                    ):
                        result = await Runner.run(
                            starting_agent=orchestrator,
                            input=clinical_query,
                            session=session
                        )
                else:
                    result = await Runner.run(
                        starting_agent=orchestrator,
                        input=clinical_query,
                        session=session
                    )
                
                # Extract metadata about which agents were consulted
                agents_consulted = []
                tool_calls = []  # Track all tool calls
                
                # Parse tool calls from result
                for item in result.new_items:
                    tool_name = None
                    tool_args = ''
                    
                    # Try different ways to get tool information
                    if hasattr(item, 'type') and item.type == 'tool_call_item':
                        if hasattr(item, 'raw_item'):
                            raw_item = item.raw_item
                            if hasattr(raw_item, 'function'):
                                tool_name = raw_item.function.name
                                tool_args = raw_item.function.arguments
                            elif hasattr(raw_item, 'name'):
                                tool_name = raw_item.name
                                tool_args = str(getattr(raw_item, 'arguments', ''))
                        elif hasattr(item, 'function'):
                            tool_name = item.function.name
                            tool_args = item.function.arguments
                        elif hasattr(item, 'name'):
                            tool_name = item.name
                            tool_args = str(getattr(item, 'arguments', ''))
                    elif hasattr(item, 'name'):
                        # Fallback to direct name access
                        tool_name = item.name
                        tool_args = str(getattr(item, 'arguments', ''))
                    
                    if tool_name:
                        # Map tool name to agent
                        agent_name = 'Unknown'
                        if 'dr_opa' in tool_name.lower():
                            agent_name = 'Dr. OPA'
                        elif 'dr_off' in tool_name.lower():
                            agent_name = 'Dr. OFF'
                        elif 'agent_97' in tool_name.lower():
                            agent_name = 'Agent 97'
                        
                        # Track tool call
                        tool_calls.append({
                            'tool': tool_name,
                            'agent': agent_name,
                            'arguments': tool_args,
                            'sub_tools': []  # Will be populated from result analysis
                        })
                        
                        # Log tool call to Langfuse (critical for trace creation)
                        if self.enable_langfuse and self.langfuse:
                            self.langfuse.start_span(
                                name=f"tool_call_{tool_name}",
                                input={"arguments": tool_args}
                            )
                        
                        if agent_name not in agents_consulted and agent_name != 'Unknown':
                            agents_consulted.append(agent_name)
                
                # Extract sub-agent tool calls from the result
                # Check if result contains structured output with tool calls
                if hasattr(result, 'output') and result.output:
                    try:
                        import json
                        output_str = str(result.output)
                        if '{' in output_str and '}' in output_str:
                            start = output_str.find('{')
                            end = output_str.rfind('}') + 1
                            json_str = output_str[start:end]
                            output_data = json.loads(json_str)
                            
                            # Look for tool_calls in the output
                            if isinstance(output_data, dict) and 'tool_calls' in output_data:
                                sub_tools = output_data['tool_calls']
                                if isinstance(sub_tools, list):
                                    # Match sub-tools to their parent agents
                                    for tc in tool_calls:
                                        if tc['agent'] != 'Unknown':
                                            # Add sub-tools for this agent
                                            for sub_tool in sub_tools:
                                                if isinstance(sub_tool, dict) and 'name' in sub_tool:
                                                    tc['sub_tools'].append({
                                                        'name': sub_tool['name'],
                                                        'arguments': sub_tool.get('arguments', '')
                                                    })
                                                    
                                                    # Log MCP tool to Langfuse
                                                    if self.enable_langfuse and self.langfuse:
                                                        self.langfuse.start_span(
                                                            name=f"mcp_tool_{sub_tool['name']}",
                                                            input={"arguments": sub_tool.get('arguments', '')}
                                                        )
                    except (json.JSONDecodeError, AttributeError):
                        pass
                
                # Extract citations from the response
                import re
                citations = []
                
                # Look for [Source: ...] pattern
                source_pattern = r'\[Source: ([^\]]+)\]'
                citations.extend(re.findall(source_pattern, result.final_output))
                
                # Look for formulary.health.gov.on.ca URLs (common in ODB responses)
                url_pattern = r'https?://(?:www\.)?formulary\.health\.gov\.on\.ca[^\s\)]*'
                citations.extend(re.findall(url_pattern, result.final_output))
                
                # Look for other Ontario health URLs
                ontario_urls = r'https?://(?:www\.)?(?:ontario\.ca|ontariohealth\.ca|cpso\.on\.ca)[^\s\)]*'
                citations.extend(re.findall(ontario_urls, result.final_output))
                
                # Remove duplicates while preserving order
                seen = set()
                unique_citations = []
                for cite in citations:
                    if cite not in seen:
                        seen.add(cite)
                        unique_citations.append(cite)
                citations = unique_citations
                
                logger.info(f"Orchestration complete. Agents consulted: {agents_consulted}")
                
                # Update Langfuse span with output
                if langfuse_span:
                    langfuse_span.update(
                        output={
                            "response": result.final_output[:500],  # Truncate for tracing
                            "agents_consulted": agents_consulted,
                            "tool_calls": tool_calls,
                            "citations": citations,
                            "confidence": 0.9
                        }
                    )
                    langfuse_span.end()
                
                # Flush any pending Langfuse events
                if self.enable_langfuse and self.langfuse:
                    try:
                        logger.info(f"Flushing Langfuse events for trace: {trace_id}")
                        self.langfuse.flush()
                        # Also shutdown properly to ensure all traces are sent
                        import time
                        time.sleep(0.5)  # Give time for async flush
                    except Exception as e:
                        logger.debug(f"Failed to flush Langfuse: {e}")
                
                return {
                    'response': result.final_output,
                    'agents_consulted': agents_consulted,
                    'tool_calls': tool_calls,
                    'citations': citations,
                    'confidence': 0.9,  # High confidence due to multi-agent synthesis
                    'session_id': session_id,
                    'trace_id': trace_id,  # Include trace_id for user feedback
                    'orchestrator': 'Chief',
                    'model': 'gpt-4o'
                }
                
        except Exception as e:
            logger.error(f"Orchestration error: {e}", exc_info=True)
            
            # Log error to Langfuse
            if langfuse_span:
                langfuse_span.update(
                    output={"error": str(e)}
                )
                langfuse_span.end()
            
            return {
                'response': self._create_error_response(str(e), clinical_query),
                'agents_consulted': [],
                'confidence': 0.0,
                'error': str(e),
                'trace_id': trace_id,  # Include trace_id even for errors
                'orchestrator': 'Chief'
            }
    
    async def orchestrate_stream(self, clinical_query: str, session_id: str = None, user_id: str = None):
        """
        Stream the orchestrated response for real-time UI updates with Langfuse tracing.
        
        Yields events as the orchestrator consults different agents and synthesizes responses.
        Each event includes trace_id for user feedback integration.
        """
        logger.info(f"Starting streaming orchestration: {clinical_query[:100]}...")
        
        # Create Langfuse trace if enabled
        langfuse_span = None
        trace_id = str(uuid.uuid4())  # Always have a trace_id for fallback
        if self.enable_langfuse and self.langfuse:
            # Create a new trace ID
            trace_id = self.langfuse.create_trace_id()
            self.langfuse.update_current_trace(
                user_id=user_id,
                session_id=session_id or self.session_id,
                name="chief_orchestrate_stream",  # Add name parameter
                tags=["orchestrator", "chief", "streaming"],  # Add tags
                metadata={
                    "agent": "chief_orchestrator",
                    "model": "gpt-4o",
                    "mode": "streaming",
                    "trace_id": trace_id,  # Include trace_id in metadata
                    "parent_trace": "OpenAI_Agents_workflow"  # Link to auto-generated trace
                }
            )
            # Start a span for this orchestration
            langfuse_span = self.langfuse.start_span(
                name="chief_orchestrate_stream",
                input={"query": clinical_query}
            )
            logger.debug(f"Created Langfuse trace: {trace_id}")
        
        try:
            from openai.types.responses import ResponseTextDeltaEvent
            
            # Ensure agents are initialized
            if not self.dr_opa_wrapper or not self.dr_off_wrapper:
                await self.initialize()
            
            # Create MCP server for Agent 97
            agent_97_mcp = MCPServerStdio(
                params=MCPServerStdioParams(
                    command="python",
                    args=["-m", "src.agents.agent_97.mcp.server"],
                    env=dict(os.environ),
                    cwd=str(self.project_root),
                    encoding="utf-8"
                ),
                name="agent-97-server",
                client_session_timeout_seconds=30.0
            )
            
            # Use MCP servers within context managers
            async with self.dr_opa_wrapper.mcp_server as opa_server, \
                       self.dr_off_wrapper.mcp_server as off_server, \
                       agent_97_mcp as a97_server:
                
                # Get Agent instances from the existing wrappers
                dr_opa_agent = self.dr_opa_wrapper.get_agent(opa_server)
                dr_off_agent = self.dr_off_wrapper.get_agent(off_server)
                agent_97_agent = self._create_agent_97(a97_server)
                
                # Convert agents to tools
                dr_opa_tool = dr_opa_agent.as_tool(
                    tool_name="dr_opa",
                    tool_description="Consult Dr. OPA for Ontario practice guidance and regulatory requirements."
                )
                
                dr_off_tool = dr_off_agent.as_tool(
                    tool_name="dr_off",
                    tool_description="Consult Dr. OFF for Ontario healthcare financing and coverage."
                )
                
                agent_97_tool = agent_97_agent.as_tool(
                    tool_name="agent_97",
                    tool_description="Consult Agent 97 for medical education from trusted sources."
                )
                
                # Create orchestrator
                orchestrator = Agent(
                    name="The Chief",
                    instructions=self.system_instructions,
                    model="gpt-4o",
                    tools=[dr_opa_tool, dr_off_tool, agent_97_tool]
                )
                
                # Create session if provided
                session = None
                if session_id:
                    session = SQLiteSession(
                        session_id,
                        "data/orchestrator_conversations.db"
                    )
                
                # Run orchestration with streaming, wrapped in logfire span if available
                # This ensures the OpenAI Agents trace captures our input/output
                if self.enable_langfuse and logfire:
                    with logfire.span(
                        'chief_orchestration',
                        _tags={'streaming': 'true'},
                        clinical_query=clinical_query,
                        session_id=session_id or self.session_id,
                        user_id=user_id
                    ):
                        result = Runner.run_streamed(
                            starting_agent=orchestrator,
                            input=clinical_query,
                            session=session
                        )
                else:
                    result = Runner.run_streamed(
                        starting_agent=orchestrator,
                        input=clinical_query,
                        session=session
                    )
                
                # Track state
                accumulated_text = ""
                agents_consulted = []
                tool_calls = []  # Track all tool calls
                citations = []  # Track citations from responses
                
                # Stream events
                async for event in result.stream_events():
                    if event.type == "raw_response_event":
                        # Stream text deltas
                        if isinstance(event.data, ResponseTextDeltaEvent):
                            delta_text = event.data.delta
                            accumulated_text += delta_text
                            yield {
                                'type': 'text',
                                'content': delta_text,
                                'trace_id': trace_id  # Include trace_id
                            }
                    
                    elif event.type == "run_item_stream_event":
                        # Handle tool calls to sub-agents
                        if event.item.type == "tool_call_item":
                            tool_name = 'unknown'
                            tool_args = ''
                            
                            # Try to extract tool information
                            if hasattr(event.item, 'raw_item'):
                                raw_item = event.item.raw_item
                                if hasattr(raw_item, 'function'):
                                    tool_name = raw_item.function.name
                                    tool_args = raw_item.function.arguments
                                elif hasattr(raw_item, 'name'):
                                    tool_name = raw_item.name
                                    tool_args = str(getattr(raw_item, 'arguments', ''))
                            elif hasattr(event.item, 'function'):
                                # Direct access to function
                                tool_name = event.item.function.name
                                tool_args = event.item.function.arguments
                            elif hasattr(event.item, 'name'):
                                # Direct access to name
                                tool_name = event.item.name
                                tool_args = str(getattr(event.item, 'arguments', ''))
                            
                            # Map tool name to agent
                            agent_name = 'Unknown'
                            if 'dr_opa' in tool_name.lower():
                                agent_name = 'Dr. OPA'
                            elif 'dr_off' in tool_name.lower():
                                agent_name = 'Dr. OFF'
                            elif 'agent_97' in tool_name.lower():
                                agent_name = 'Agent 97'
                            
                            # Only track if we got a real tool name
                            if tool_name != 'unknown':
                                # Track the top-level agent call
                                tool_calls.append({
                                    'tool': tool_name,  # This will be dr_off, dr_opa, etc.
                                    'agent': agent_name,
                                    'arguments': tool_args,
                                    'sub_tools': []  # Will be populated from tool output
                                })
                                
                                # Log tool call to Langfuse (this is the critical step)
                                if self.enable_langfuse and self.langfuse:
                                    self.langfuse.start_span(
                                        name=f"tool_call_{tool_name}",
                                        input={"arguments": tool_args}
                                    )
                                
                                if agent_name not in agents_consulted and agent_name != 'Unknown':
                                    agents_consulted.append(agent_name)
                            
                            yield {
                                'type': 'agent_consultation',
                                'content': {
                                    'agent': agent_name,
                                    'status': 'consulting'
                                },
                                'trace_id': trace_id  # Include trace_id
                            }
                        
                        elif event.item.type == "tool_call_output_item":
                            # Extract the sub-agent's tool calls and citations from the output
                            if hasattr(event.item, 'output'):
                                output_str = str(event.item.output)
                                
                                # Extract citations from the text output
                                # Look for URLs in the output
                                import re
                                
                                # Extract formulary.health.gov.on.ca URLs
                                formulary_urls = re.findall(r'https?://(?:www\.)?formulary\.health\.gov\.on\.ca[^\s\)]*', output_str)
                                for url in formulary_urls:
                                    if url not in citations:
                                        citations.append(url)
                                        # Forward citation to UI
                                        yield {
                                            'type': 'citation',
                                            'content': {
                                                'url': url,
                                                'source': 'ODB Formulary',
                                                'domain': 'formulary.health.gov.on.ca',
                                                'is_trusted': True,
                                                'source_agent': agents_consulted[-1] if agents_consulted else 'Unknown'
                                            }
                                        }
                                
                                # Extract Ontario health URLs
                                ontario_urls = re.findall(r'https?://(?:www\.)?(?:ontario\.ca|ontariohealth\.ca|cpso\.on\.ca)[^\s\)]*', output_str)
                                for url in ontario_urls:
                                    if url not in citations:
                                        citations.append(url)
                                        domain = 'cpso.on.ca' if 'cpso' in url else 'ontario.ca' if 'ontario.ca' in url else 'ontariohealth.ca'
                                        yield {
                                            'type': 'citation',
                                            'content': {
                                                'url': url,
                                                'source': 'Ontario Health' if 'ontariohealth' in url else 'CPSO' if 'cpso' in url else 'Government of Ontario',
                                                'domain': domain,
                                                'is_trusted': True,
                                                'source_agent': agents_consulted[-1] if agents_consulted else 'Unknown'
                                            }
                                        }
                                
                                # Try to parse JSON output from sub-agents
                                try:
                                    import json
                                    # Look for JSON-like structure in the output
                                    if '{' in output_str and '}' in output_str:
                                        start = output_str.find('{')
                                        end = output_str.rfind('}') + 1
                                        json_str = output_str[start:end]
                                        output_data = json.loads(json_str)
                                        
                                        # Check if the output contains tool_calls from sub-agent
                                        if isinstance(output_data, dict) and 'tool_calls' in output_data:
                                            sub_agent_tools = output_data['tool_calls']
                                            if isinstance(sub_agent_tools, list) and tool_calls:
                                                # Add sub-agent's tool calls to the last agent call
                                                for sub_tool in sub_agent_tools:
                                                    if isinstance(sub_tool, dict) and 'name' in sub_tool:
                                                        tool_calls[-1]['sub_tools'].append({
                                                            'name': sub_tool['name'],  # e.g., odb_get, opa_search_sections
                                                            'arguments': sub_tool.get('arguments', '')
                                                        })
                                                        
                                                        # Log sub-tool to Langfuse
                                                        if self.enable_langfuse and self.langfuse:
                                                            self.langfuse.start_span(
                                                                name=f"mcp_tool_{sub_tool['name']}",
                                                                input={"arguments": sub_tool.get('arguments', '')}
                                                            )
                                        
                                        # Check if output contains citations from sub-agent
                                        if isinstance(output_data, dict) and 'citations' in output_data:
                                            sub_citations = output_data['citations']
                                            if isinstance(sub_citations, list):
                                                for cite in sub_citations:
                                                    if isinstance(cite, dict):
                                                        # Forward structured citation
                                                        if cite not in citations:
                                                            citations.append(cite)
                                                            yield {
                                                                'type': 'citation',
                                                                'content': cite
                                                            }
                                                    elif isinstance(cite, str) and cite not in citations:
                                                        # Forward string citation
                                                        citations.append(cite)
                                                        yield {
                                                            'type': 'citation',
                                                            'content': {
                                                                'source': cite,
                                                                'is_trusted': True,
                                                                'source_agent': agents_consulted[-1] if agents_consulted else 'Unknown'
                                                            }
                                                        }
                                except (json.JSONDecodeError, AttributeError):
                                    # Not JSON or parsing failed, skip
                                    pass
                
                # Extract any additional citations from the final response that weren't caught earlier
                import re
                
                # Look for [Source: ...] pattern in the final accumulated text
                source_pattern = r'\[Source: ([^\]]+)\]'
                final_sources = re.findall(source_pattern, accumulated_text)
                for source in final_sources:
                    if source not in citations:
                        citations.append(source)
                
                # Deduplicate citations (keeping order)
                seen = set()
                unique_citations = []
                for cite in citations:
                    cite_key = str(cite) if isinstance(cite, dict) else cite
                    if cite_key not in seen:
                        seen.add(cite_key)
                        unique_citations.append(cite)
                citations = unique_citations
                
                # Update Langfuse span with output
                if langfuse_span:
                    langfuse_span.update(
                        output={
                            "response": accumulated_text[:500],  # Truncate for tracing
                            "agents_consulted": agents_consulted,
                            "tool_calls": tool_calls,
                            "citations": citations
                        }
                    )
                    langfuse_span.end()
                
                # Flush any pending Langfuse events
                if self.enable_langfuse and self.langfuse:
                    try:
                        logger.info(f"Flushing Langfuse events for trace: {trace_id}")
                        self.langfuse.flush()
                        # Also shutdown properly to ensure all traces are sent
                        import time
                        time.sleep(0.5)  # Give time for async flush
                    except Exception as e:
                        logger.debug(f"Failed to flush Langfuse: {e}")
                
                # Send completion event
                yield {
                    'type': 'complete',
                    'content': accumulated_text,
                    'agents_consulted': agents_consulted,
                    'tool_calls': tool_calls,
                    'citations': citations,
                    'trace_id': trace_id,  # Include trace_id
                    'orchestrator': 'Chief'
                }
                
        except Exception as e:
            logger.error(f"Streaming orchestration error: {e}")
            
            # Log error to Langfuse
            if langfuse_span:
                langfuse_span.update(
                    output={"error": str(e)}
                )
                langfuse_span.end()
            
            yield {
                'type': 'error',
                'content': str(e),
                'trace_id': trace_id  # Include trace_id even for errors
            }
    
    def _create_error_response(self, error_message: str, query: str) -> str:
        """Create a fallback response for orchestration errors."""
        return f"""I apologize, but the Medical Diagnostic Orchestrator is experiencing technical difficulties.

For your query: "{query[:100]}..."

The orchestrator was unable to coordinate between the specialist agents. Please try:

1. Consulting individual resources directly:
   - CPSO: https://www.cpso.on.ca/
   - Ontario Health: https://www.ontariohealth.ca/
   - OHIP Schedule: https://www.ontario.ca/page/ohip-schedule-benefits-and-fees
   - ODB Formulary: https://www.ontario.ca/page/check-medication-coverage/

2. Reformulating your query with more specific details

3. Trying again in a few moments

Technical details: {error_message}

Remember: This system provides educational information only. Always consult appropriate medical professionals for clinical decisions."""


async def create_diagnostic_orchestrator() -> DiagnosticOrchestrator:
    """Factory function to create and initialize the Diagnostic Orchestrator."""
    orchestrator = DiagnosticOrchestrator()
    await orchestrator.initialize()
    return orchestrator


# Test function for development
async def test_orchestrator():
    """Test the diagnostic orchestrator with sample clinical scenarios."""
    from dotenv import load_dotenv
    load_dotenv()
    
    orchestrator = await create_diagnostic_orchestrator()
    
    test_scenarios = [
        {
            "name": "Complex Diabetes Case",
            "query": "I have a 72-year-old patient with newly diagnosed type 2 diabetes, BMI 32, and limited income. What are the CPSO documentation requirements, ODB coverage options for metformin and newer diabetes drugs, and evidence-based management approaches?"
        },
        {
            "name": "Chest Pain Emergency",
            "query": "55-year-old presenting with acute chest pain and shortness of breath. Need Ontario cardiac pathway, OHIP billing codes for ECG and troponins, and current ACS management guidelines."
        },
        {
            "name": "Mental Health Crisis",
            "query": "Young adult presenting with suicidal ideation. What are the mandatory reporting requirements in Ontario, OHIP billing codes for emergency psychiatric assessment, and evidence-based crisis intervention protocols?"
        }
    ]
    
    for scenario in test_scenarios[:1]:  # Test just the first scenario
        print(f"\n{'='*80}")
        print(f"Scenario: {scenario['name']}")
        print(f"Query: {scenario['query']}")
        print(f"{'='*80}\n")
        
        result = await orchestrator.orchestrate(scenario['query'])
        
        print(f"Agents Consulted: {', '.join(result['agents_consulted'])}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Model: {result.get('model', 'unknown')}")
        print(f"\nResponse:\n{'-'*40}")
        print(result['response'])
        
        if result.get('error'):
            print(f"\nError: {result['error']}")


if __name__ == "__main__":
    asyncio.run(test_orchestrator())