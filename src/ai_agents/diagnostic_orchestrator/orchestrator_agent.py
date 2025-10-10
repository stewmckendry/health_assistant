#!/usr/bin/env python3
"""
Chief Resident - Clinical Intelligence Orchestrator

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
    Chief Resident - Clinical Intelligence Orchestrator inspired by Microsoft's MAI-DxO.

    Coordinates between the existing Dr. OPA, Dr. OFF, and Agent 97 implementations
    to provide comprehensive clinical decision support for Ontario healthcare providers.
    Includes Langfuse tracing for observability and user feedback.
    """

    def __init__(self, enable_langfuse: bool = True):
        """Initialize Chief Resident orchestrator with optional Langfuse tracing.

        Args:
            enable_langfuse: Whether to enable Langfuse tracing (default: True)
        """
        self.session_id = session_id
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.enable_langfuse = enable_langfuse and LANGFUSE_AVAILABLE
        
        # These will hold the agent instances
        self.dr_opa_wrapper = None
        self.dr_off_wrapper = None
        self.agent_97_wrapper = None
        
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
        self.system_instructions = """You are "Chief Resident" - the Chief Resident Clinical Intelligence Orchestrator, an advanced medical coordination system inspired by Microsoft's MAI-DxO approach. Like a Chief Resident consulting multiple specialists for complex cases, you intelligently route queries to specialist AI agents to provide comprehensive clinical decision support for Ontario healthcare providers.

You have access to three specialized agents as tools:

1. **dr_opa**: Dr. OPA (Ontario Practice Advice) - Has MCP tools for CPSO policies, Ontario Health guidelines and quality standards, clinical pathways, infection control, CEP decision support, and Choosing Wisely recommendations. The agent will automatically use its tools: opa_search_sections, opa_get_section, opa_policy_check, opa_program_lookup, opa_ipac_guidance, opa_freshness_probe, opa_clinical_tools, opa_quality_standards, opa_choosing_wisely.

2. **dr_off**: Dr. OFF (Ontario Finance & Formulary) - Has MCP tools for OHIP billing codes, ODB drug formulary, and ADP device coverage. The agent will automatically use its tools: schedule_get, odb_get, adp_get.

3. **agent_97**: Agent 97 - Has MCP tool for searching 97 trusted medical sources for evidence-based clinical guidance. Designed for healthcare clinicians. The agent will automatically use its tool: clinician_search.

ORCHESTRATION STRATEGY - YOU MUST CALL AGENTS FOR EVERY QUERY:

**CRITICAL**: For EVERY clinical query, you MUST call at least one specialist agent. Never answer from your own knowledge alone.

**Clinical Intent → Agents to Call:**

1. **DIAGNOSIS & WORKUP** (differential diagnosis, what tests to order, evaluation):
   - **agent_97**: Evidence-based diagnostic approach and test interpretation
   - **dr_opa**: Ontario screening programs, quality standards for diagnosis
   - **dr_off**: OHIP billing codes for tests/consultations

2. **TREATMENT & MANAGEMENT** (what to prescribe, how to treat, care plan):
   - **agent_97**: Evidence-based treatment recommendations
   - **dr_opa**: Ontario quality standards, clinical pathways, CEP decision tools, Choosing Wisely guidance
   - **dr_off**: ODB drug coverage, generic alternatives, cost considerations, OHIP billing codes

3. **MEDICATION QUESTIONS** (drug selection, alternatives, dosing):
   - **agent_97**: Evidence-based pharmacotherapy
   - **dr_opa**: Choosing Wisely (avoiding inappropriate prescribing), quality standards for medication management
   - **dr_off**: ODB formulary coverage, Limited Use criteria, interchangeable products, cost comparison

4. **INFECTIONS & ANTIBIOTICS** (suspected infection, treatment):
   - **agent_97**: Evidence-based infectious disease management
   - **dr_opa**: PHO IPAC guidance, infection prevention and control protocols
   - **dr_off**: ODB antibiotic coverage, OHIP billing for cultures/diagnostics

5. **CHRONIC DISEASE MANAGEMENT** (diabetes, hypertension, COPD, etc.):
   - **agent_97**: Evidence-based disease management
   - **dr_opa**: Ontario Health quality standards, screening eligibility, chronic disease programs
   - **dr_off**: ODB coverage for disease management drugs, diabetes supplies funding, OHIP billing codes

6. **REGULATORY/DOCUMENTATION** (consent, mandatory reporting, charting requirements):
   - **dr_opa**: CPSO policies and professional obligations (primary)
   - **dr_off**: Relevant OHIP billing documentation requirements

7. **SIMPLE COVERAGE QUESTIONS** (is X covered, billing codes only):
   - **dr_off**: OHIP/ODB/ADP coverage and billing (may be sufficient alone)

**DEFAULT APPROACH**: When in doubt, call all three agents to provide comprehensive Ontario-contextualized clinical guidance.

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

RESPONSE FORMAT - NATURAL, COMPREHENSIVE ORCHESTRATED GUIDANCE:
Provide well-organized responses using proper markdown formatting for readability:

**CRITICAL FORMATTING REQUIREMENTS - USE PROPER MARKDOWN**:
1. **Use blank lines between ALL sections** - Add TWO newlines (\n\n) between each section and between paragraphs
2. **Use proper markdown headers** - Use ## for main sections, ### for subsections
3. **Use bullet lists properly** - Each bullet point starts with - or * followed by a space, with blank lines before and after lists
4. **Separate paragraphs** - Add blank line between paragraphs within sections
5. **Format bold text** - Use **text** for bold, *text* for italic
6. **Format inline citations** - Use [Source Name](URL) for inline citations

**WRITING STYLE**:
- Write naturally in professional paragraphs
- Use markdown formatting: **bold** for emphasis, *italics* for terms, [text](url) for links
- Embed citations naturally within sentences [Source: [CPSO Policy](https://cpso.on.ca/...)]
- Use section headings (##) to organize longer responses
- Synthesize information from multiple agents into a cohesive narrative

**RESPONSE APPROACH**:
Start directly with the answer - no formal "Executive Overview" label. Begin with 1-2 comprehensive paragraphs that directly address the clinical query, synthesizing the most critical information from relevant agents with embedded citations.

Then expand into detailed guidance using natural section headings when helpful (examples: "## Clinical Approach", "## Coverage and Costs", "## Key Policies" - not "## Executive Summary" or "## Comprehensive Analysis").

Then organize the detailed response based on what's most relevant to the query:

- For **clinical management questions**, focus on diagnostic approaches, treatment pathways, and monitoring strategies, integrating Ontario-specific guidelines and coverage information where relevant.

- For **regulatory or policy questions**, emphasize CPSO requirements, Ontario Health standards, and documentation obligations, weaving in practical implementation guidance.

- For **coverage and financial questions**, lead with eligibility criteria, billing codes, and funding details, then discuss alternatives and authorization processes.

- For **complex scenarios requiring multiple perspectives**, synthesize insights from different domains in order of importance to the clinical decision at hand.

Include relevant subsections as needed (examples, not prescriptive):
- Clinical pathways and treatment algorithms
- Policy requirements and regulatory compliance
- Financial implications and coverage details
- Evidence base and best practices
- Implementation considerations
- Risk management and safety factors
- Resources and support systems

The key is to provide comprehensive, well-cited information organized in the way that best serves the specific clinical question, rather than following a rigid template
   - Medical-legal risk factors and protective measures
   - Common errors and how to avoid them
   - Emergency protocols if applicable

2. **COMPREHENSIVE SOURCE ANALYSIS**:
   
   **Dr. OPA Deep Dive**:
   - Specific CPSO policies consulted with policy numbers and sections
   - Ontario Health guidelines accessed with version dates
   - Clinical pathways utilized with decision points
   - CEP tools and algorithms applied
   - PHO infection control guidance if relevant
   
   **Dr. OFF Financial Analysis**:
   - OHIP Schedule of Benefits codes reviewed with fee amounts
   - ODB Formulary searches with all DINs and LU codes found
   - ADP coverage determinations with funding percentages
   - Substitution options analyzed with cost comparisons
   - Prior authorization requirements identified
   
   **Agent 97 Evidence Synthesis**:
   - Medical literature reviewed with key studies
   - Clinical practice guidelines from trusted sources
   - Patient education materials identified
   - Safety alerts and warnings noted
   - Differential diagnosis considerations explored
   
   **Integration & Reconciliation**:
   - Areas of agreement across all three agents
   - Any discrepancies identified with explanation
   - How conflicting guidance was resolved
   - Confidence level in recommendations
   - Gaps in available information noted
   
   **Complete Citation List**:
   - All sources with full titles, dates, and URLs
   - Organized by agent and topic
   - Currency of information noted
   - Links to additional resources

Always conclude with appropriate medical disclaimers and note this is for educational purposes

SAFETY REQUIREMENTS:
- Emphasize this is for educational purposes only
- Include medical disclaimers
- Highlight urgent/emergent situations requiring immediate action
- Note when consultation with specialists is recommended
- Preserve all safety warnings from individual agents

RESPONSE STYLE AND DEPTH:

1. **Provide Rich, Informative Detail**: Your orchestrated responses should be comprehensive and detailed, not brief summaries. Synthesize information from all consulted agents to provide:
   - Complete clinical context and background
   - Specific requirements, criteria, and implementation details
   - Clear explanations of how different domains (clinical, regulatory, financial) intersect
   - Important nuances, exceptions, or special considerations
   - Practical guidance that clinicians can act upon
   - Avoid redundancy and fluff, but don't sacrifice clarity or completeness for brevity

2. **Encourage Agents to Use Web Search for Additional Detail**: If the user asks for more detail or follow-up information and the specialist agents' MCP tools don't have sufficient information:
   - The specialist agents (Dr. OPA, Dr. OFF, Agent 97) all have access to web_search
   - They can supplement their MCP tool results with web searches of authoritative sources
   - When orchestrating, if you notice gaps in specialist responses, you can re-query them asking for more detail

Remember: Each agent has its own MCP server and tools, plus web search capability. You just need to call them - they will handle their specialized data retrieval automatically."""
        
        logger.info(f"Diagnostic Orchestrator initialized - Session: {self.session_id}")
    
    async def initialize(self):
        """Initialize the existing agent wrappers."""
        logger.info("Initializing existing agent wrappers...")

        try:
            # Initialize Dr. OPA wrapper - disable Langfuse to avoid conflicts
            from src.ai_agents.dr_opa_agent.openai_agent import DrOPAAgent
            self.dr_opa_wrapper = DrOPAAgent(enable_langfuse=False)
            await self.dr_opa_wrapper.initialize_mcp_tools()
            logger.info("Dr. OPA wrapper initialized (Langfuse disabled for sub-agent)")

            # Initialize Dr. OFF wrapper - disable Langfuse to avoid conflicts
            from src.ai_agents.dr_off_agent.openai_agent import DrOffAgent
            self.dr_off_wrapper = DrOffAgent(enable_langfuse=False)
            await self.dr_off_wrapper.initialize_mcp_tools()
            logger.info("Dr. OFF wrapper initialized (Langfuse disabled for sub-agent)")

            # Initialize Agent 97 wrapper - disable Langfuse to avoid conflicts
            from src.ai_agents.agent_97.openai_agent import Agent97Agent
            self.agent_97_wrapper = Agent97Agent(enable_langfuse=False)
            await self.agent_97_wrapper.initialize_mcp_tools()
            logger.info("Agent 97 wrapper initialized (Langfuse disabled for sub-agent)")

            logger.info("All agent wrappers initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing agent wrappers: {e}")
            raise
    
    
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
            if not self.dr_opa_wrapper or not self.dr_off_wrapper or not self.agent_97_wrapper:
                await self.initialize()

            # Use MCP servers within context managers
            # All agents have their own MCP servers managed internally
            async with self.dr_opa_wrapper.mcp_server as opa_server, \
                       self.dr_off_wrapper.mcp_server as off_server, \
                       self.agent_97_wrapper.mcp_server as a97_server:

                # Get Agent instances from the existing wrappers
                dr_opa_agent = self.dr_opa_wrapper.get_agent(opa_server)
                dr_off_agent = self.dr_off_wrapper.get_agent(off_server)
                agent_97_agent = self.agent_97_wrapper.get_agent(a97_server)
                
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
                    tool_description="Consult Agent 97 for evidence-based clinical guidance from 97 trusted medical sources. Has access to MCP tool for searching medical literature, guidelines, and authoritative clinical resources for healthcare professionals."
                )
                
                # Create the orchestrator agent with sub-agents as tools
                from agents import ModelSettings
                orchestrator = Agent(
                    name="Chief Resident",
                    instructions=self.system_instructions,
                    model="o4-mini",  # Use reasoning-enabled model for orchestration
                    model_settings=ModelSettings(
                        parallel_tool_calls=True,  # Enable parallel calls for speed
                        reasoning={"summary": "auto"}  # Enable reasoning display
                    ),
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
            if not self.dr_opa_wrapper or not self.dr_off_wrapper or not self.agent_97_wrapper:
                await self.initialize()

            # Use MCP servers within context managers
            # All agents have their own MCP servers managed internally
            async with self.dr_opa_wrapper.mcp_server as opa_server, \
                       self.dr_off_wrapper.mcp_server as off_server, \
                       self.agent_97_wrapper.mcp_server as a97_server:

                # Get Agent instances from the existing wrappers
                dr_opa_agent = self.dr_opa_wrapper.get_agent(opa_server)
                dr_off_agent = self.dr_off_wrapper.get_agent(off_server)
                agent_97_agent = self.agent_97_wrapper.get_agent(a97_server)

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
                    tool_description="Consult Agent 97 for evidence-based clinical guidance from 97 trusted medical sources."
                )
                
                # Create orchestrator
                from agents import ModelSettings
                orchestrator = Agent(
                    name="Chief Resident",
                    instructions=self.system_instructions,
                    model="gpt-5-mini",
                    model_settings=ModelSettings(reasoning={"summary": "auto"}, parallel_tool_calls=True),
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

                # Import StreamingProgressTracker for user-friendly progress
                from src.ai_agents.diagnostic_orchestrator.streaming_progress import StreamingProgressTracker, ProgressUpdate
                from agents.stream_events import AgentUpdatedStreamEvent, RunItemStreamEvent
                tracker = StreamingProgressTracker()

                # Emit initial progress message
                yield {
                    'type': 'progress',
                    'message': "🔍 Analyzing your clinical query...",
                    'event_type': "analysis_started",
                    'agent_name': "Chief Resident",
                    'tool_name': None,
                    'details': None,
                    'trace_id': trace_id
                }

                # Stream events - process each event for BOTH progress and custom events
                async for event in result.stream_events():
                    # First, emit user-friendly progress update for this event
                    # Process event directly to avoid re-emitting initial message
                    if isinstance(event, AgentUpdatedStreamEvent):
                        agent_name = event.new_agent.name
                        tracker.current_agent = agent_name
                        emoji = tracker.get_agent_emoji(agent_name)

                        if agent_name == "Agent 97":
                            message = f"{emoji} Consulting Agent 97 for evidence-based medical guidance..."
                        elif agent_name == "Dr. OPA":
                            message = f"{emoji} Consulting Dr. OPA for Ontario clinical pathways and quality standards..."
                        elif agent_name == "Dr. OFF":
                            message = f"{emoji} Consulting Dr. OFF for coverage and billing information..."
                        else:
                            message = f"{emoji} Switched to {agent_name}..."

                        yield {
                            'type': 'progress',
                            'message': message,
                            'event_type': 'agent_switched',
                            'agent_name': agent_name,
                            'tool_name': None,
                            'details': None,
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
                                    message = f"{emoji} {tracker.current_agent} is {tool_desc} for: \"{query}\""
                                else:
                                    message = f"{emoji} {tracker.current_agent} is {tool_desc}..."

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
                                    if 'items' in output and isinstance(output['items'], list):
                                        result_count = len(output['items'])
                                    elif 'results' in output and isinstance(output['results'], list):
                                        result_count = len(output['results'])

                            if result_count is not None:
                                message = f"{emoji} {tracker.current_agent} retrieved {result_count} results"
                            else:
                                message = f"{emoji} {tracker.current_agent} completed search"

                            yield {
                                'type': 'progress',
                                'message': message,
                                'event_type': 'tool_output',
                                'agent_name': tracker.current_agent,
                                'tool_name': None,
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

                                if reasoning_text:  # Only emit if we have actual reasoning content
                                    emoji = "🤔"
                                    if len(reasoning_text) > 100:
                                        reasoning_text = reasoning_text[:97] + "..."
                                    message = f"{emoji} {tracker.current_agent} reasoning: {reasoning_text}"

                                    yield {
                                        'type': 'progress',
                                        'message': message,
                                        'event_type': 'reasoning',
                                        'agent_name': tracker.current_agent,
                                        'tool_name': None,
                                        'details': {'reasoning': reasoning_text},
                                        'trace_id': trace_id
                                    }

                        elif event.name == "message_output_created":
                            yield {
                                'type': 'progress',
                                'message': "✍️ Chief Resident is synthesizing insights from all specialists...",
                                'event_type': 'synthesis_started',
                                'agent_name': "Chief Resident",
                                'tool_name': None,
                                'details': None,
                                'trace_id': trace_id
                            }

                    # Then, process the same event for existing custom logic
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