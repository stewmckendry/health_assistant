#!/usr/bin/env python3
"""
Dr. OPA OpenAI Agent Implementation

An intelligent assistant specialized in Ontario practice guidance for healthcare clinicians.
Built using the OpenAI Agents Python SDK with MCP integration to the Dr. OPA server.
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

# Import yaml for loading trusted domains
try:
    import yaml
except ImportError:
    yaml = None

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

import sys
from pathlib import Path

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
    from agents import Agent, Runner, WebSearchTool
    from agents.memory import SQLiteSession
    from agents.mcp.server import MCPServerStdio, MCPServerStdioParams
    from agents.tool import WebSearchToolFilters
finally:
    # Restore original sys.path
    sys.path = original_path

# Configure logging
log_dir = Path("logs/dr_opa_agent")
log_dir.mkdir(parents=True, exist_ok=True)

session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"openai_agent_session_{session_id}.log"

logging.basicConfig(
    level=logging.DEBUG,  # Enable debug logging to see tool call extraction
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_trusted_domains() -> set:
    """Load trusted domains from domains.yaml config file."""
    try:
        if yaml is None:
            logger.warning("PyYAML not available, using fallback trusted domains")
            raise ImportError("PyYAML not installed")
            
        domains_file = Path(__file__).parent.parent.parent.parent / "src" / "config" / "domains.yaml"
        if domains_file.exists():
            with open(domains_file, 'r') as f:
                config = yaml.safe_load(f)
                return set(config.get('trusted_domains', []))
        else:
            logger.warning(f"Domains file not found at {domains_file}")
    except Exception as e:
        logger.warning(f"Could not load trusted domains: {e}")
    
    # Fallback to core trusted domains
    return {
        'cpso.on.ca', 'ontario.ca', 'publichealthontario.ca', 'ontariohealth.ca',
        'cep.health', 'mayoclinic.org', 'clevelandclinic.org', 'who.int',
        'cdc.gov', 'nih.gov', 'nejm.org', 'thelancet.com'
    }


def extract_domain(url: str) -> str:
    """Extract domain from URL, normalized without www."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain.replace('www.', '') if domain.startswith('www.') else domain
    except:
        return ''


def extract_citations_from_tool_result(tool_name: str, tool_result: Any, trusted_domains: set) -> List[Dict]:
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
        
        # Extract citations from various MCP response formats
        if 'citations' in result_data and isinstance(result_data['citations'], list):
            # Direct citations list from MCP response
            for cite in result_data['citations']:
                citation = create_citation_from_mcp(cite, trusted_domains)
                if citation:
                    citations.append(citation)
        
        # Extract from highlights that contain citations
        if 'highlights' in result_data and isinstance(result_data['highlights'], list):
            for highlight in result_data['highlights']:
                if 'citations' in highlight:
                    for cite in highlight['citations']:
                        citation = create_citation_from_mcp(cite, trusted_domains)
                        if citation:
                            citations.append(citation)
        
        # Extract from sections with metadata
        if 'sections' in result_data and isinstance(result_data['sections'], list):
            for section in result_data['sections']:
                if 'metadata' in section and 'url' in section['metadata']:
                    citation = {
                        'id': f"section_{uuid.uuid4().hex[:8]}",
                        'title': section.get('heading', 'Document Section'),
                        'source': section['metadata'].get('source_org', 'Unknown'),
                        'source_type': 'policy',
                        'url': section['metadata']['url'],
                        'domain': extract_domain(section['metadata']['url']),
                        'is_trusted': extract_domain(section['metadata']['url']) in trusted_domains,
                        'access_date': datetime.now().isoformat(),
                        'snippet': section.get('text', '')[:200] + '...' if len(section.get('text', '')) > 200 else section.get('text', ''),
                        'relevance_score': section.get('relevance_score', 0.8)
                    }
                    citations.append(citation)
        
        # Extract from documents
        if 'documents' in result_data and isinstance(result_data['documents'], list):
            for doc in result_data['documents']:
                if 'url' in doc and doc['url']:
                    citation = {
                        'id': f"doc_{uuid.uuid4().hex[:8]}",
                        'title': doc.get('title', 'Document'),
                        'source': doc.get('source_org', 'Unknown'),
                        'source_type': doc.get('document_type', 'document'),
                        'url': doc['url'],
                        'domain': extract_domain(doc['url']),
                        'is_trusted': extract_domain(doc['url']) in trusted_domains,
                        'access_date': datetime.now().isoformat(),
                        'relevance_score': 0.8
                    }
                    citations.append(citation)
    
    except Exception as e:
        logger.warning(f"Error extracting citations from {tool_name}: {e}")
    
    return citations


def create_citation_from_mcp(cite_data: Dict, trusted_domains: set) -> Optional[Dict]:
    """Create standardized citation from MCP citation data."""
    try:
        # Handle different MCP citation formats
        url = cite_data.get('url', '')
        if not url and 'source' in cite_data:
            # Try to construct URL from source info
            source_org = cite_data.get('source_org', '').lower()
            if 'cpso' in source_org:
                url = f"https://www.cpso.on.ca/"  # Base URL, specific page unknown
            elif 'ontario' in source_org:
                url = f"https://www.ontario.ca/"
            elif 'pho' in source_org or 'public health ontario' in source_org:
                url = f"https://www.publichealthontario.ca/"
            elif 'cep' in source_org:
                url = f"https://cep.health/"
        
        if not url:
            return None
        
        citation = {
            'id': f"cite_{uuid.uuid4().hex[:8]}",
            'title': cite_data.get('source', cite_data.get('title', 'Document')),
            'source': cite_data.get('source_org', cite_data.get('source', 'Unknown')),
            'source_type': 'policy',  # Most MCP results are policy documents
            'url': url,
            'domain': extract_domain(url),
            'is_trusted': extract_domain(url) in trusted_domains,
            'access_date': datetime.now().isoformat(),
            'relevance_score': 0.9  # High relevance since from structured sources
        }
        
        # Add location info if available
        if 'loc' in cite_data:
            citation['snippet'] = f"Section: {cite_data['loc']}"
        
        return citation
    
    except Exception as e:
        logger.warning(f"Error creating citation: {e}")
        return None


def extract_highlights_from_tool_results(tool_results: List[Dict], citations: List[Dict]) -> List[Dict]:
    """Extract key highlights with citation references."""
    highlights = []
    
    for tool_result in tool_results:
        try:
            result_data = tool_result.get('result', {})
            
            # Extract highlights from MCP response
            if 'highlights' in result_data and isinstance(result_data['highlights'], list):
                for highlight in result_data['highlights']:
                    # Map MCP citations to our citation IDs
                    citation_ids = []
                    if 'citations' in highlight:
                        for cite in highlight['citations']:
                            # Find matching citation by source and location
                            for our_citation in citations:
                                if (cite.get('source', '') in our_citation['title'] or 
                                    cite.get('loc', '') in our_citation.get('snippet', '')):
                                    citation_ids.append(our_citation['id'])
                                    break
                    
                    highlights.append({
                        'point': highlight.get('point', ''),
                        'citations': citation_ids,
                        'confidence': 0.9,
                        'policy_level': highlight.get('policy_level')
                    })
            
            # Extract from expectations and advice
            for section_name in ['expectations', 'advice']:
                if section_name in result_data and isinstance(result_data[section_name], list):
                    for item in result_data[section_name]:
                        citation_ids = []
                        if 'citations' in item:
                            for cite in item['citations']:
                                for our_citation in citations:
                                    if cite.get('source', '') in our_citation['title']:
                                        citation_ids.append(our_citation['id'])
                                        break
                        
                        highlights.append({
                            'point': item.get('point', ''),
                            'citations': citation_ids,
                            'confidence': 0.9,
                            'policy_level': 'expectation' if section_name == 'expectations' else 'advice'
                        })
        
        except Exception as e:
            logger.warning(f"Error extracting highlights: {e}")
    
    return highlights


class DrOPAAgent:
    """Dr. OPA OpenAI Agent with MCP integration and Langfuse tracing."""
    
    def __init__(self, mcp_server_command: str = None, enable_langfuse: bool = True):
        """Initialize the Dr. OPA Agent with MCP server connection and optional Langfuse tracing.
        
        Args:
            mcp_server_command: Command to start the MCP server
            enable_langfuse: Whether to enable Langfuse tracing (default: True)
        """
        self.session_id = session_id
        self.project_root = project_root
        self.trusted_domains = load_trusted_domains()
        self.enable_langfuse = enable_langfuse and LANGFUSE_AVAILABLE
        logger.info(f"Loaded {len(self.trusted_domains)} trusted domains for citation validation")
        
        # Initialize Langfuse tracing if enabled
        if self.enable_langfuse:
            try:
                # Apply nest_asyncio for notebook/async compatibility
                # Skip if running under uvloop (FastAPI/uvicorn)
                if nest_asyncio:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    # Only apply nest_asyncio if not using uvloop
                    if not loop.__class__.__module__.startswith('uvloop'):
                        nest_asyncio.apply()
                
                # Configure logfire for OpenAI Agents instrumentation
                # This automatically sends traces to Langfuse via OTLP
                logfire.configure(
                    service_name='dr_opa_agent',
                    send_to_logfire=False,  # Only send to Langfuse via OTLP
                )
                
                # This method automatically patches the OpenAI Agents SDK
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
        
        # Initialize MCP server connection using STDIO
        # This connects to our local Dr. OPA MCP server running in STDIO mode
        # Special value "skip" means don't initialize (for subclasses)
        if mcp_server_command == "skip":
            self.mcp_server = None
        else:
            if mcp_server_command is None:
                # Default command to run our Dr. OPA MCP server
                mcp_server_command = [
                    "python", "-m", "src.ai_agents.dr_opa_agent.dr_opa_mcp.server"
                ]
            
            self.mcp_server = MCPServerStdio(
                params=MCPServerStdioParams(
                    command=mcp_server_command[0],
                    args=mcp_server_command[1:],
                    env=dict(os.environ),  # Pass current environment variables
                    cwd=str(self.project_root),  # Set working directory
                    encoding="utf-8"
                ),
                name="dr-opa-server",
                client_session_timeout_seconds=60.0  # Extended timeout for opa_program_lookup web searches
            )
        
        logger.info(f"Dr. OPA Agent initialized - Session: {self.session_id}")
        logger.info(f"MCP Server Command: {mcp_server_command}")
    
    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for the agent."""
        return """You are Dr. OPA (Ontario Practice Advice), a specialized AI assistant for Ontario healthcare clinicians.

Your mission is to provide accurate, current practice guidance from trusted Ontario healthcare authorities including:
- CPSO (College of Physicians and Surgeons of Ontario) - regulatory policies and expectations
- Ontario Health - clinical programs, screening guidelines, care pathways, and quality standards
- CEP (Centre for Effective Practice) - clinical decision support tools and algorithms
- PHO (Public Health Ontario) - infection prevention and control guidance
- MOH (Ministry of Health) - policy bulletins and program updates
- Choosing Wisely Canada - evidence-based recommendations to avoid unnecessary tests and procedures

RESPONSE FORMAT - NATURAL, COMPREHENSIVE GUIDANCE:
Provide thorough responses in flowing paragraphs with helpful organization:

**WRITING STYLE**:
- Write naturally in clear, professional paragraphs
- Use markdown formatting: **bold** for emphasis, *italics* for terms, [text](url) for links
- Embed citations naturally within sentences [Source: CPSO Policy #1-21, Section 4.2]
- Use section headings (##) to organize longer responses, but keep them conversational
- Connect ideas with smooth transitions

**RESPONSE APPROACH**:
Start directly with the answer to the query - no need for formal "Executive Summary" labels. Begin with 1-2 paragraphs that directly address the clinical question, integrating the most critical policy requirements and guidelines with embedded citations.

Then expand into relevant details, using natural section headings when helpful (examples: "## Key Requirements", "## Implementation Steps", "## Important Considerations" - not "## Executive Summary" or "## Detailed Analysis").

Structure your response based on the query type:

- For **CPSO policy questions**, lead with the specific regulatory requirements, expectations, and compliance obligations, then discuss practical implementation and documentation needs.

- For **clinical program questions**, focus on eligibility criteria, referral pathways, and coverage details, integrating relevant policies and standards.

- For **infection control questions**, emphasize PHO guidance, specific protocols, and implementation requirements for the healthcare setting in question.

- For **clinical decision support questions**, present the relevant tools, algorithms, and pathways, explaining how to apply them in practice.

- For **quality standards questions**, present the relevant quality statements, indicators, and implementation guidance from Ontario Health standards.

- For **broad practice guidance questions**, synthesize information from multiple sources in order of relevance to the clinical scenario.

Include relevant content areas as appropriate (examples, not required sections):
- Regulatory requirements and policy compliance
- Clinical pathways and care standards
- Program eligibility and access procedures
- Implementation guidance and best practices
- Recent updates and transitioning requirements
- Quality improvement opportunities
- Resources and support tools

The goal is to provide comprehensive, well-cited Ontario-specific guidance organized in the way that best addresses the clinical question at hand, maintaining narrative flow while including all essential details

CORE PRINCIPLES:
1. Always cite your sources with organization, document title, effective dates, and URLs
2. Distinguish between regulatory expectations (mandatory) vs. advice (recommended)
3. Prioritize current guidance over superseded content
4. Provide Ontario-specific context and considerations
5. Use appropriate clinical terminology while remaining accessible
6. When uncertain, recommend consulting the source documents directly

TOOL SELECTION STRATEGY:
Analyze each query and select the most appropriate tools, prioritizing MCP tools over web search:

PRIMARY TOOLS (Use First - Ontario-specific embedded knowledge):
- **opa_policy_check**: For CPSO regulatory questions, policy compliance, professional expectations
  Keywords: CPSO, college, expectation, must, shall, required, policy, regulation

- **opa_program_lookup**: For Ontario Health clinical programs, screening guidelines, care pathways
  Keywords: screening, program, cancer, kidney, cardiac, stroke, ontario health, eligibility

- **opa_ipac_guidance**: For infection prevention and control questions
  Keywords: infection, control, sterilization, disinfection, PPE, hand hygiene, IPAC

- **opa_clinical_tools**: For CEP clinical decision support tools and algorithms
  Keywords: algorithm, tool, calculator, checklist, assessment, CEP, clinical decision

- **opa_choosing_wisely**: For Choosing Wisely recommendations to avoid unnecessary care
  Keywords: unnecessary, overuse, avoid, don't do, choosing wisely, low-value care, imaging, testing
  Use when: Questions about what tests/procedures to avoid, concerns about overutilization

- **opa_quality_standards**: For Ontario Health quality standards and quality statements
  Keywords: quality standard, quality statement, best practice, standard of care, ontario health standard, quality indicators
  Use when: Questions about evidence-based standards for specific conditions, quality improvement guidance

- **opa_search_sections**: For general practice guidance queries across all sources
  Use for: broad questions, multi-source queries, when other tools don't clearly apply

- **opa_freshness_probe**: To verify currency when asked about "current" or "latest" guidance
  Keywords: current, updated, latest, recent, new

- **opa_get_section**: To retrieve complete details when you need full context from a specific section

FALLBACK TOOL (Use when MCP tools don't provide sufficient information):
- **Web Search**: ONLY use as a complement or fallback when:
  - MCP tools return insufficient or no results
  - User specifically asks for latest web updates
  - Need to verify very recent policy changes
  - Cross-reference with official websites
  Note: Web search is restricted to trusted Ontario healthcare domains only

RESPONSE STRUCTURE:
1. **Direct Answer**: Clear, actionable response to the question
2. **Current Guidance**: Relevant policies/guidelines with proper citations
3. **Implementation Notes**: Practical considerations for clinical practice
4. **Related Resources**: Cross-references to additional relevant guidance
5. **Currency Note**: When the guidance was last updated and confidence level
6. **Sources & Tool Contributions**: 
   **MCP Tools Used** (Primary Sources):
   - **opa_policy_check**: [If used] CPSO policies retrieved, specific sections found
   - **opa_program_lookup**: [If used] Ontario Health programs accessed, eligibility criteria obtained
   - **opa_search_sections**: [If used] Number of documents searched, relevance scores
   - **opa_ipac_guidance**: [If used] PHO guidance retrieved, specific protocols found
   - **opa_clinical_tools**: [If used] CEP tools accessed, algorithms applied
   - **opa_choosing_wisely**: [If used] Choosing Wisely recommendations found, specialties searched
   - **opa_quality_standards**: [If used] Quality standards accessed, quality statements retrieved
   - **opa_freshness_probe**: [If used] Currency verification results
   - **opa_get_section**: [If used] Complete sections retrieved for context
   
   **Web Search** (Fallback Source):
   - [If used] State explicitly: "Web search used as fallback because: [reason]"
   - Domains searched and key findings
   - How web results complemented or validated MCP tool data
   
   **Data Reconciliation**:
   - Any discrepancies between MCP tools and web search
   - How conflicts were resolved
   - Confidence level: High/Medium/Low with explanation

CITATION FORMAT:
- Use markdown links: [Organization Name - Document Title](URL)
- Include effective dates in the link text when available
- Format as: [CPSO - Policy Title (Effective: Date)](URL)
- Distinguish between expectations (mandatory) and advice (recommended)
- Ensure URLs are properly formatted for markdown rendering

Remember: You have access to the comprehensive Ontario practice guidance corpus through your MCP tools. Use them strategically to provide the most accurate, current, and relevant information."""

    async def initialize_mcp_tools(self):
        """Initialize and connect to MCP server tools."""
        try:
            logger.info("MCP server is configured with Agent constructor")
            logger.info("Available MCP tools: opa_search_sections, opa_get_section, opa_policy_check, opa_program_lookup, opa_ipac_guidance, opa_freshness_probe, opa_clinical_tools, opa_choosing_wisely, opa_quality_standards")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP tools: {e}")
            logger.warning("Agent will operate without MCP tools - responses will be limited")
            return False
    
    async def query_stream(self, user_input: str, session_id: str = None, user_id: str = None):
        """Process a user query and stream the response with Langfuse tracing.
        
        Args:
            user_input: The user's query
            session_id: Session ID for conversation tracking
            user_id: User ID for tracking
        """
        logger.info(f"Processing streaming query: {user_input[:100]}...")
        
        # Generate a trace ID upfront for fallback
        fallback_trace_id = str(uuid.uuid4())
        trace_id = fallback_trace_id
        
        try:
            from openai.types.responses import ResponseTextDeltaEvent
            
            # Create session if session_id provided
            session = None
            if session_id:
                # Use persistent SQLite database for sessions
                session = SQLiteSession(
                    session_id, 
                    "data/dr_opa_conversations.db"
                )
            
            # Use the MCP server within an async context manager
            async with self.mcp_server as server:
                # Create agent with the connected MCP server
                # Add WebSearchTool with Ontario-specific allowed domains
                web_search_tool = WebSearchTool(
                    filters=WebSearchToolFilters(
                        allowed_domains=[
                            # Primary Ontario healthcare authorities (10)
                            "cpso.on.ca",
                            "ontario.ca",
                            "health.gov.on.ca",
                            "ontariohealth.ca",
                            "publichealthontario.ca",
                            "cep.health",
                            "cno.org",
                            "ocp.on.ca",
                            "rcdso.org",
                            # Key Canadian health organizations (5)
                            "canada.ca",
                            "cihi.ca",
                            "cma.ca",
                            "cfpc.ca",
                            "royalcollege.ca",
                            # Ontario programs and quality (5)
                            "hqontario.ca",
                            "cancercareontario.ca",
                            "ices.on.ca",
                            "choosingwiselycanada.org",
                            "cmpa-acpm.ca"
                        ]
                    ),
                    search_context_size="medium"
                )
                
                agent = Agent(
                    name="Dr. OPA",
                    instructions=self._get_system_instructions(),
                    model="gpt-4o",
                    mcp_servers=[server],
                    tools=[web_search_tool]
                )
                
                # Create Langfuse trace if enabled
                langfuse_span = None
                if self.enable_langfuse and self.langfuse:
                    # Create a new trace ID and update the current trace
                    trace_id = self.langfuse.create_trace_id()
                    self.langfuse.update_current_trace(
                        user_id=user_id,
                        session_id=session_id,
                        metadata={
                            "agent": "dr_opa",
                            "model": "gpt-4o-mini",
                            "trace_id": trace_id
                        },
                        tags=["dr_opa", "streaming"]
                    )
                    # Start a span for this query
                    langfuse_span = self.langfuse.start_span(
                        name="dr_opa_query_stream",
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
                
                # Stream events
                async for event in result.stream_events():
                    if event.type == "raw_response_event":
                        # Stream text deltas
                        if isinstance(event.data, ResponseTextDeltaEvent):
                            delta_text = event.data.delta
                            accumulated_text += delta_text
                            yield {
                                'type': 'text',
                                'content': delta_text
                            }
                    
                    elif event.type == "run_item_stream_event":
                        # Handle tool calls
                        if event.item.type == "tool_call_item":
                            # Extract function name from raw_item
                            tool_name = 'unknown'
                            tool_args = ''
                            
                            if hasattr(event.item, 'raw_item'):
                                raw_item = event.item.raw_item
                                
                                # Handle WebSearchTool which has type 'web_search_call'
                                if hasattr(raw_item, 'type') and raw_item.type == 'web_search_call':
                                    tool_name = 'web_search'
                                    # Extract query from action if available
                                    if hasattr(raw_item, 'action') and hasattr(raw_item.action, 'query'):
                                        tool_args = f'{{"query": "{raw_item.action.query}"}}'
                                    else:
                                        tool_args = ''
                                # Standard function calls (MCP tools)
                                elif hasattr(raw_item, 'function'):
                                    tool_name = raw_item.function.name
                                    tool_args = raw_item.function.arguments
                                elif hasattr(raw_item, 'name'):
                                    tool_name = raw_item.name
                                    tool_args = str(getattr(raw_item, 'arguments', ''))
                                elif isinstance(raw_item, dict):
                                    # Sometimes raw_item is a dict
                                    if 'type' in raw_item and raw_item['type'] == 'web_search_call':
                                        tool_name = 'web_search'
                                        tool_args = ''
                                    elif 'function' in raw_item:
                                        tool_name = raw_item['function'].get('name', 'unknown')
                                        tool_args = raw_item['function'].get('arguments', '')
                                    elif 'name' in raw_item:
                                        tool_name = raw_item['name']
                                        tool_args = str(raw_item.get('arguments', ''))
                            
                            tool_call_data = {
                                'name': tool_name,
                                'arguments': str(tool_args)
                            }
                            tool_calls.append(tool_call_data)
                            
                            # Log tool call to Langfuse
                            if self.enable_langfuse and self.langfuse:
                                self.langfuse.start_span(
                                    name=f"tool_call_{tool_name}",
                                    input={"arguments": tool_args}
                                )
                            
                            yield {
                                'type': 'tool_call',
                                'content': tool_call_data
                            }
                        
                        elif event.item.type == "tool_call_output_item":
                            # Extract citations from tool output
                            output_str = ''
                            
                            # Debug the structure
                            logger.info(f"tool_call_output_item received")
                            logger.info(f"event.item attributes: {[attr for attr in dir(event.item) if not attr.startswith('_')]}")
                            
                            if hasattr(event.item, 'raw_item'):
                                logger.info(f"raw_item type: {type(event.item.raw_item)}")
                                if isinstance(event.item.raw_item, dict):
                                    logger.info(f"raw_item dict keys: {list(event.item.raw_item.keys())}")
                                    if 'output' in event.item.raw_item:
                                        output_str = event.item.raw_item['output']
                                        logger.info(f"Got output from raw_item['output']")
                                else:
                                    logger.info(f"raw_item attributes: {[attr for attr in dir(event.item.raw_item) if not attr.startswith('_')]}")
                                    if hasattr(event.item.raw_item, 'output'):
                                        output_str = event.item.raw_item.output
                                        logger.info(f"Got output from raw_item.output")
                            
                            if not output_str and hasattr(event.item, 'output'):
                                output_str = event.item.output
                                logger.info(f"Got output from item.output, type: {type(event.item.output)}")
                            
                            if not output_str:
                                logger.warning(f"Could not find output in tool_call_output_item")
                            
                            # More detailed logging
                            logger.info(f"Tool output received - type: {type(output_str)}, length: {len(str(output_str))}")
                            if output_str:
                                # Log first 500 chars of output
                                logger.info(f"Tool output preview: {str(output_str)[:500]}...")
                            
                            if output_str:
                                # Try to parse output as JSON to extract citations
                                try:
                                    import json
                                    output_data = json.loads(output_str) if isinstance(output_str, str) else output_str
                                    
                                    # Handle MCP text type response
                                    if isinstance(output_data, dict) and output_data.get('type') == 'text':
                                        # Extract the actual text content
                                        text_content = output_data.get('text', '')
                                        logger.info(f"MCP returned text type, extracting inner text content")
                                        # Try to parse the inner text as JSON
                                        try:
                                            output_data = json.loads(text_content)
                                            logger.info(f"Successfully parsed inner text as JSON")
                                        except:
                                            logger.info(f"Inner text is not JSON, using as-is")
                                            output_data = text_content
                                    
                                    if isinstance(output_data, dict):
                                        logger.info(f"Parsed tool output keys: {list(output_data.keys())}")
                                        # Check for specific fields that might contain citations
                                        for key in ['citations', 'sections', 'documents', 'highlights']:
                                            if key in output_data:
                                                logger.info(f"Found '{key}' in output with {len(output_data[key]) if isinstance(output_data[key], list) else 'non-list'} items")
                                    else:
                                        logger.info(f"Parsed output is not a dict, type: {type(output_data)}")
                                except Exception as e:
                                    logger.info(f"Failed to parse tool output as JSON: {e}")
                                    output_data = output_str
                                
                                citations = extract_citations_from_tool_result(
                                    tool_calls[-1]['name'] if tool_calls else 'unknown',
                                    output_data,
                                    self.trusted_domains
                                )
                                
                                logger.info(f"Extracted {len(citations)} citations from tool '{tool_calls[-1]['name'] if tool_calls else 'unknown'}'")
                                
                                for citation in citations:
                                    if citation not in all_citations:
                                        all_citations.append(citation)
                                        logger.info(f"Yielding citation: {citation.get('title', 'Unknown')} - {citation.get('url', 'no-url')}")
                                        yield {
                                            'type': 'citation',
                                            'content': citation
                                        }
                
                # Update Langfuse trace with final output
                if langfuse_span:
                    langfuse_span.update(
                        output={
                            "response": accumulated_text,
                            "tool_calls": tool_calls,
                            "citations": all_citations
                        }
                    )
                    langfuse_span.end()
                
                # Send final completion event with all accumulated data including trace_id
                yield {
                    'type': 'complete',
                    'content': accumulated_text,
                    'tool_calls': tool_calls,
                    'citations': all_citations,
                    'metadata': {
                        'trace_id': trace_id  # Include trace_id for feedback
                    }
                }
                
                # Flush any pending Langfuse events
                if self.enable_langfuse and self.langfuse:
                    try:
                        self.langfuse.flush()
                    except Exception as e:
                        logger.debug(f"Failed to flush Langfuse: {e}")
                
        except Exception as e:
            logger.error(f"Error in streaming query: {e}")
            
            # Logfire automatically handles error tracing
            
            yield {
                'type': 'error',
                'content': str(e)
            }
    
    async def query(self, user_input: str, session_id: str = None, user_id: str = None) -> Dict:
        """Process a user query and return the agent's response with Langfuse tracing.
        
        Args:
            user_input: The user's query
            session_id: Session ID for conversation tracking
            user_id: User ID for tracking
        """
        logger.info(f"Processing query: {user_input[:100]}...")
        
        # Generate a trace ID upfront for fallback
        fallback_trace_id = str(uuid.uuid4())
        trace_id = fallback_trace_id
        
        try:
            # Runner already imported above
            
            # Create session if session_id provided
            session = None
            if session_id:
                # Use persistent SQLite database for sessions
                session = SQLiteSession(
                    session_id, 
                    "data/dr_opa_conversations.db"
                )
            
            # Use the MCP server within an async context manager
            async with self.mcp_server as server:
                # Create agent with the connected MCP server
                # Add WebSearchTool with Ontario-specific allowed domains
                web_search_tool = WebSearchTool(
                    filters=WebSearchToolFilters(
                        allowed_domains=[
                            # Primary Ontario healthcare authorities (10)
                            "cpso.on.ca",
                            "ontario.ca",
                            "health.gov.on.ca",
                            "ontariohealth.ca",
                            "publichealthontario.ca",
                            "cep.health",
                            "cno.org",
                            "ocp.on.ca",
                            "rcdso.org",
                            # Key Canadian health organizations (5)
                            "canada.ca",
                            "cihi.ca",
                            "cma.ca",
                            "cfpc.ca",
                            "royalcollege.ca",
                            # Ontario programs and quality (5)
                            "hqontario.ca",
                            "cancercareontario.ca",
                            "ices.on.ca",
                            "choosingwiselycanada.org",
                            "cmpa-acpm.ca"
                        ]
                    ),
                    search_context_size="medium"
                )
                
                agent = Agent(
                    name="Dr. OPA",
                    instructions=self._get_system_instructions(),
                    model="gpt-4o",
                    mcp_servers=[server],
                    tools=[web_search_tool]
                )
                
                # Create Langfuse trace if enabled
                langfuse_span = None
                if self.enable_langfuse and self.langfuse:
                    # Create a new trace ID and update the current trace
                    trace_id = self.langfuse.create_trace_id()
                    self.langfuse.update_current_trace(
                        user_id=user_id,
                        session_id=session_id,
                        metadata={
                            "agent": "dr_opa",
                            "model": "gpt-4o-mini",
                            "trace_id": trace_id
                        },
                        tags=["dr_opa", "non-streaming"]
                    )
                    # Start a span for this query
                    langfuse_span = self.langfuse.start_span(
                        name="dr_opa_query",
                        input={"query": user_input}
                    )
                    logger.debug(f"Created Langfuse trace: {trace_id}")
                
                # Run the agent
                result = await Runner.run(
                    starting_agent=agent,
                    input=user_input,
                    session=session
                )
                
                # Extract tool calls and citations from the result
                tool_calls = []
                all_citations = []
                tool_results_for_highlights = []
                
                # Debug the overall result structure
                logger.debug(f"RunResult type: {type(result)}")
                logger.debug(f"RunResult attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
                
                logger.debug(f"Examining {len(result.new_items)} result items for tool calls")
                
                for i, item in enumerate(result.new_items):
                    logger.debug(f"Item {i} type: {type(item)}")
                    logger.debug(f"Item {i} attributes: {[attr for attr in dir(item) if not attr.startswith('_')]}")
                    
                    # Check if this is a FunctionCall or tool-related item
                    tool_call_data = None
                    tool_result_data = None
                    
                    if hasattr(item, 'name') and hasattr(item, 'arguments'):
                        logger.debug(f"Item {i} looks like a function call: name={getattr(item, 'name', None)}")
                        tool_call_data = {
                            'name': item.name,
                            'arguments': str(item.arguments) if hasattr(item, 'arguments') else ''
                        }
                        # Check if this item also has result data
                        if hasattr(item, 'result'):
                            tool_result_data = item.result
                    elif hasattr(item, 'call_id') and hasattr(item, 'name'):
                        logger.debug(f"Item {i} has call_id and name: {item.name}")
                        tool_call_data = {
                            'name': item.name,
                            'arguments': str(getattr(item, 'arguments', ''))
                        }
                        if hasattr(item, 'result'):
                            tool_result_data = item.result
                    elif hasattr(item, 'tool_calls') and item.tool_calls:
                        logger.debug(f"Item {i} has {len(item.tool_calls)} tool calls")
                        for tool_call in item.tool_calls:
                            tool_call_data = {
                                'name': tool_call.function.name,
                                'arguments': tool_call.function.arguments
                            }
                    elif hasattr(item, 'content') and hasattr(item.content, 'tool_calls'):
                        logger.debug(f"Item {i} content has tool calls")
                        if item.content.tool_calls:
                            for tool_call in item.content.tool_calls:
                                tool_call_data = {
                                    'name': tool_call.function.name,
                                    'arguments': tool_call.function.arguments
                                }
                    else:
                        logger.debug(f"Item {i} doesn't match expected patterns")
                        if hasattr(item, '__dict__'):
                            logger.debug(f"Item {i} __dict__: {item.__dict__}")
                    
                    # Add tool call data if found
                    if tool_call_data:
                        tool_calls.append(tool_call_data)
                        
                        # Extract citations from tool result if available
                        if tool_result_data:
                            citations = extract_citations_from_tool_result(
                                tool_call_data['name'], 
                                tool_result_data, 
                                self.trusted_domains
                            )
                            all_citations.extend(citations)
                            
                            # Store tool result for highlight extraction
                            tool_results_for_highlights.append({
                                'name': tool_call_data['name'],
                                'result': tool_result_data
                            })
                    
                # Also check raw_responses for additional tool calls
                logger.debug(f"Examining {len(result.raw_responses)} raw responses")
                for i, response in enumerate(result.raw_responses):
                    logger.debug(f"Response {i} type: {type(response)}")
                    if hasattr(response, 'choices'):
                        for j, choice in enumerate(response.choices):
                            if hasattr(choice, 'message') and hasattr(choice.message, 'tool_calls'):
                                if choice.message.tool_calls:
                                    logger.debug(f"Found tool calls in response {i}, choice {j}")
                                    for tool_call in choice.message.tool_calls:
                                        # Check if we already captured this tool call
                                        existing_call = any(
                                            tc['name'] == tool_call.function.name 
                                            for tc in tool_calls
                                        )
                                        if not existing_call:
                                            tool_calls.append({
                                                'name': tool_call.function.name,
                                                'arguments': tool_call.function.arguments
                                            })
                
                # Deduplicate citations by URL and title
                seen_citations = set()
                unique_citations = []
                for citation in all_citations:
                    # Create deduplication key
                    if citation.get('url') and citation['url'].startswith('http'):
                        key = f"{extract_domain(citation['url'])}_{citation.get('title', '').lower().strip()}"
                    else:
                        key = f"{citation.get('domain', '')}_{citation.get('title', '').lower().strip()}"
                    
                    if key not in seen_citations:
                        seen_citations.add(key)
                        unique_citations.append(citation)
                
                # Extract highlights with citation references
                highlights = extract_highlights_from_tool_results(tool_results_for_highlights, unique_citations)
                
                # Calculate overall confidence
                confidence = 0.8  # Base confidence
                if unique_citations:
                    # Higher confidence with more citations
                    confidence = min(0.95, 0.7 + (len(unique_citations) * 0.05))
                    # Higher confidence if trusted sources
                    trusted_ratio = sum(1 for c in unique_citations if c.get('is_trusted', False)) / len(unique_citations)
                    confidence = min(0.98, confidence + (trusted_ratio * 0.1))
                
                # Log tool calls and citations
                if tool_calls:
                    logger.info(f"MCP Tools called: {[tc['name'] for tc in tool_calls]}")
                    for tc in tool_calls:
                        logger.info(f"  - {tc['name']}: {tc['arguments'][:100]}...")
                else:
                    logger.info("No MCP tools were called")
                
                # Log citation summary
                if unique_citations:
                    trusted_count = sum(1 for c in unique_citations if c.get('is_trusted', False))
                    logger.info(f"Extracted {len(unique_citations)} citations ({trusted_count} trusted)")
                    for cite in unique_citations[:3]:  # Log first 3 citations
                        logger.info(f"  - {cite['title']} ({cite['domain']}) {'✓' if cite.get('is_trusted') else '?'}")
                else:
                    logger.info("No citations extracted from tool results")
                
                logger.info(f"Query processed successfully. Response length: {len(result.final_output)}")
                
                # Log tool calls to Langfuse
                if self.enable_langfuse and self.langfuse:
                    for tool_call in tool_calls:
                        self.langfuse.start_span(
                            name=f"tool_call_{tool_call['name']}",
                            input={"arguments": tool_call['arguments']}
                        )
                
                # Update span with output
                if langfuse_span:
                    langfuse_span.update(
                        output={
                            "response": result.final_output,
                            "tool_calls": tool_calls,
                            "citations": unique_citations
                        }
                    )
                    langfuse_span.end()
                
                # Flush any pending Langfuse events
                if self.enable_langfuse and self.langfuse:
                    try:
                        self.langfuse.flush()
                    except Exception as e:
                        logger.debug(f"Failed to flush Langfuse: {e}")
                
                # Return enhanced response with structured citations
                return {
                    'response': result.final_output,
                    'tool_calls': tool_calls,
                    'tools_used': [tc['name'] for tc in tool_calls],
                    'citations': unique_citations,
                    'highlights': highlights,
                    'confidence': confidence,
                    'trace_id': trace_id  # Include trace_id for feedback
                }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            
            # Logfire automatically handles error tracing
            
            error_response = self._create_error_response(str(e), user_input)
            return {
                'response': error_response,
                'tool_calls': [],
                'tools_used': [],
                'citations': [],
                'highlights': [],
                'confidence': 0.0,
                'error': str(e),
                'trace_id': trace_id  # Include trace_id even on error
            }
    
    def _create_error_response(self, error_message: str, query: str) -> str:
        """Create a fallback response for errors."""
        return f"""I apologize, but I'm experiencing technical difficulties accessing the Ontario practice guidance database.

For your query: "{query[:100]}..."

Please try:
1. Consulting the relevant source documents directly:
   - CPSO: https://www.cpso.on.ca/
   - Ontario Health: https://www.ontariohealth.ca/
   - PHO: https://www.publichealthontario.ca/
   - CEP: https://cep.health/

2. Trying your query again in a few minutes

This is a temporary issue and normal service should resume shortly.

Technical details: {error_message}"""
    
    def get_agent(self, mcp_server=None):
        """
        Get the OpenAI Agent instance for use as a tool in orchestrators.
        
        Args:
            mcp_server: The active MCP server context (from async with statement)
                       If None, will use self.mcp_server
        
        Returns:
            Agent instance configured with Dr. OPA's instructions and MCP tools
        """
        server = mcp_server if mcp_server is not None else self.mcp_server
        
        # Create WebSearchTool with Ontario-specific allowed domains
        web_search_tool = WebSearchTool(
            filters=WebSearchToolFilters(
                allowed_domains=[
                    # Primary Ontario healthcare authorities (10)
                    "cpso.on.ca",
                    "ontario.ca",
                    "health.gov.on.ca",
                    "ontariohealth.ca",
                    "publichealthontario.ca",
                    "cep.health",
                    "cno.org",
                    "ocp.on.ca",
                    "rcdso.org",
                    # Key Canadian health organizations (5)
                    "canada.ca",
                    "cihi.ca",
                    "cma.ca",
                    "cfpc.ca",
                    "royalcollege.ca",
                    # Ontario programs and quality (5)
                    "hqontario.ca",
                    "cancercareontario.ca",
                    "ices.on.ca",
                    "choosingwiselycanada.org",
                    "cmpa-acpm.ca"
                ]
            ),
            search_context_size="medium"
        )
        
        return Agent(
            name="Dr. OPA",
            instructions=self._get_system_instructions(),
            model="gpt-4o",
            mcp_servers=[server] if server else [],
            tools=[web_search_tool]
        )


async def create_dr_opa_agent(mcp_server_command: list = None) -> DrOPAAgent:
    """Factory function to create and initialize Dr. OPA Agent."""
    
    # Create agent instance with MCP server command
    agent = DrOPAAgent(mcp_server_command)
    
    # Initialize MCP tools
    mcp_connected = await agent.initialize_mcp_tools()
    
    if not mcp_connected:
        logger.warning("Agent created without MCP connection - functionality will be limited")
    
    return agent


# Simple test function for development
async def test_agent():
    """Simple test function for development."""
    from dotenv import load_dotenv
    load_dotenv()
    
    agent = await create_dr_opa_agent()
    
    test_query = "What are CPSO expectations for virtual care consent documentation?"
    print(f"Query: {test_query}")
    print("-" * 60)
    
    result = await agent.query(test_query)
    
    # Handle enhanced response format with citations
    if isinstance(result, dict):
        print(f"🔧 Tools Used: {', '.join(result['tools_used']) if result['tools_used'] else 'None'}")
        print(f"📊 Tool Call Details: {len(result['tool_calls'])} tools called")
        print(f"📚 Citations Found: {len(result.get('citations', []))} ({sum(1 for c in result.get('citations', []) if c.get('is_trusted', False))} trusted)")
        print(f"💡 Highlights: {len(result.get('highlights', []))}")
        print(f"🎯 Confidence: {result.get('confidence', 0.0):.2f}")
        print("-" * 60)
        print("📄 Response:")
        print(result['response'])
        
        if result.get('citations'):
            print("\n📚 Citations:")
            for i, cite in enumerate(result['citations'], 1):
                trust_indicator = "✓" if cite.get('is_trusted', False) else "?"
                print(f"  {i}. {trust_indicator} {cite['title']}")
                print(f"     Source: {cite['source']} ({cite['domain']})")
                print(f"     URL: {cite['url']}")
                if cite.get('snippet'):
                    print(f"     Excerpt: {cite['snippet'][:100]}...")
                print()
        
        if result.get('highlights'):
            print("\n💡 Key Highlights:")
            for i, highlight in enumerate(result['highlights'], 1):
                print(f"  {i}. {highlight['point']}")
                if highlight.get('policy_level'):
                    print(f"     Policy Level: {highlight['policy_level']}")
                print(f"     Citations: {len(highlight.get('citations', []))}")
                print()
        
        if result['tool_calls']:
            print("\n🔧 Detailed Tool Calls:")
            for i, tc in enumerate(result['tool_calls'], 1):
                print(f"  {i}. {tc['name']}")
                print(f"     Arguments: {tc['arguments'][:200]}...")
    else:
        # Backward compatibility for string responses
        print(result)


if __name__ == "__main__":
    asyncio.run(test_agent())