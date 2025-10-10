#!/usr/bin/env python3
"""
Dr. OFF OpenAI Agent Implementation

An intelligent assistant specialized in Ontario healthcare financing, drug coverage, 
and assistive devices guidance for healthcare clinicians.
Built using the OpenAI Agents Python SDK with MCP integration to the Dr. OFF server.
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
log_dir = Path("logs/dr_off_agent")
log_dir.mkdir(parents=True, exist_ok=True)

session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"openai_agent_session_{session_id}.log"

logging.basicConfig(
    level=logging.DEBUG,
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
    
    # Fallback to core trusted Ontario healthcare domains
    return {
        'ontario.ca', 'health.gov.on.ca', 'ohip.ca',
        'publichealthontario.ca', 'ontariohealth.ca',
        'cpso.on.ca', 'ocp.on.ca', 'cno.org'
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
        
        # Handle MCP text type response
        if isinstance(result_data, dict) and result_data.get('type') == 'text':
            text_content = result_data.get('text', '')
            try:
                result_data = json.loads(text_content)
            except:
                result_data = {'content': text_content}
        
        # Extract citations from standardized response format
        if 'citations' in result_data and isinstance(result_data['citations'], list):
            for cite in result_data['citations']:
                # Handle both new standardized format and old format
                if isinstance(cite, dict):
                    # Check if it's the simple format from MCP tools
                    if 'source' in cite and 'loc' in cite:
                        # Simple citation format from schedule/odb/adp tools
                        # Use provided URL if available, otherwise generate one
                        url = cite.get('url') if cite.get('url') else self._get_url_for_source(cite.get('source', ''), tool_name)
                        
                        # Extract domain from URL
                        import urllib.parse
                        domain = 'ontario.ca'
                        if url:
                            parsed = urllib.parse.urlparse(url)
                            domain = parsed.netloc.replace('www.', '') if parsed.netloc else 'ontario.ca'
                        
                        citation = {
                            'id': f"cite_{uuid.uuid4().hex[:8]}",
                            'title': f"{cite.get('source', 'Document')} - {cite.get('loc', '')}",
                            'source': cite.get('source', 'Unknown'),
                            'source_type': 'billing' if 'OHIP' in cite.get('source', '') else 'policy',
                            'url': url,
                            'domain': domain,
                            'is_trusted': True,
                            'access_date': datetime.now().isoformat(),
                            'snippet': cite.get('loc', ''),
                            'relevance_score': 0.9
                        }
                        citations.append(citation)
                    else:
                        # Try the standardized format
                        citation = create_citation_from_mcp(cite, trusted_domains, tool_name)
                        if citation:
                            citations.append(citation)
        
        # Extract from codes (OHIP)
        if 'codes' in result_data and isinstance(result_data['codes'], list):
            for code in result_data['codes']:
                citation = {
                    'id': f"ohip_{uuid.uuid4().hex[:8]}",
                    'title': f"OHIP Code {code.get('code', '')}",
                    'source': 'OHIP Schedule of Benefits',
                    'source_type': 'billing',
                    'url': 'https://www.ontario.ca/page/ohip-schedule-benefits-and-fees',
                    'domain': 'ontario.ca',
                    'is_trusted': True,
                    'access_date': datetime.now().isoformat(),
                    'snippet': code.get('description', '')[:200],
                    'relevance_score': 0.9
                }
                citations.append(citation)
        
        # Extract from drugs (ODB)
        if 'drugs' in result_data and isinstance(result_data['drugs'], list):
            for drug in result_data['drugs']:
                citation = {
                    'id': f"odb_{uuid.uuid4().hex[:8]}",
                    'title': f"ODB - {drug.get('name', '')}",
                    'source': 'Ontario Drug Benefit Formulary',
                    'source_type': 'formulary',
                    'url': 'https://www.ontario.ca/page/check-medication-coverage/',
                    'domain': 'ontario.ca',
                    'is_trusted': True,
                    'access_date': datetime.now().isoformat(),
                    'snippet': drug.get('criteria', drug.get('coverage_criteria', ''))[:200],
                    'relevance_score': 0.9
                }
                citations.append(citation)
        
        # Extract from device info (ADP)
        if 'device' in result_data and isinstance(result_data['device'], dict):
            device = result_data['device']
            citation = {
                'id': f"adp_{uuid.uuid4().hex[:8]}",
                'title': f"ADP - {device.get('device_type', 'Device')}",
                'source': 'Assistive Devices Program',
                'source_type': 'coverage',
                'url': 'https://www.ontario.ca/page/assistive-devices-program',
                'domain': 'ontario.ca',
                'is_trusted': True,
                'access_date': datetime.now().isoformat(),
                'snippet': device.get('coverage_details', '')[:200],
                'relevance_score': 0.95
            }
            citations.append(citation)
    
    except Exception as e:
        logger.warning(f"Error extracting citations from {tool_name}: {e}")
    
    return citations


def create_citation_from_mcp(cite_data: Dict, trusted_domains: set, tool_name: str) -> Optional[Dict]:
    """Create standardized citation from MCP citation data."""
    try:
        # Get URL from citation data
        url = cite_data.get('url', '')
        
        # If no URL, try to construct from source info
        if not url:
            source_org = cite_data.get('source_org', '').lower()
            if 'ministry of health' in source_org or 'ontario' in source_org:
                if 'ohip' in tool_name.lower() or 'schedule' in tool_name.lower():
                    url = 'https://www.ontario.ca/page/ohip-schedule-benefits-and-fees'
                elif 'odb' in tool_name.lower() or 'drug' in tool_name.lower():
                    url = 'https://www.ontario.ca/page/check-medication-coverage/'
                elif 'adp' in tool_name.lower() or 'assistive' in tool_name.lower():
                    url = 'https://www.ontario.ca/page/assistive-devices-program'
                else:
                    url = 'https://www.ontario.ca/'
        
        if not url:
            return None
        
        # Determine source type based on tool
        source_type = 'policy'
        if 'schedule' in tool_name.lower() or 'ohip' in tool_name.lower():
            source_type = 'billing'
        elif 'odb' in tool_name.lower() or 'drug' in tool_name.lower():
            source_type = 'formulary'
        elif 'adp' in tool_name.lower():
            source_type = 'coverage'
        
        citation = {
            'id': cite_data.get('id', f"cite_{uuid.uuid4().hex[:8]}"),
            'title': cite_data.get('source', cite_data.get('title', 'Document')),
            'source': cite_data.get('source_org', cite_data.get('source', 'Unknown')),
            'source_type': source_type,
            'url': url,
            'domain': extract_domain(url),
            'is_trusted': extract_domain(url) in trusted_domains,
            'access_date': cite_data.get('access_date', datetime.now().isoformat()),
            'relevance_score': cite_data.get('relevance_score', 0.9)
        }
        
        # Add location info if available
        if 'loc' in cite_data:
            citation['snippet'] = f"Location: {cite_data['loc']}"
        elif 'snippet' in cite_data:
            citation['snippet'] = cite_data['snippet'][:200]
        
        return citation
    
    except Exception as e:
        logger.warning(f"Error creating citation: {e}")
        return None


class DrOffAgent:
    """Dr. OFF OpenAI Agent with MCP integration and Langfuse tracing."""
    
    def _get_url_for_source(self, source: str, tool_name: str) -> str:
        """Get the appropriate URL based on source and tool."""
        source_lower = source.lower()
        tool_lower = tool_name.lower()
        
        if 'ohip' in source_lower or 'schedule' in tool_lower:
            return 'https://www.ontario.ca/page/ohip-schedule-benefits-and-fees'
        elif 'odb' in source_lower or 'drug' in source_lower or 'formulary' in source_lower:
            return 'https://www.ontario.ca/page/check-medication-coverage/'
        elif 'adp' in source_lower or 'assistive' in source_lower:
            return 'https://www.ontario.ca/page/assistive-devices-program'
        else:
            return 'https://www.ontario.ca/'
    
    def __init__(self, mcp_server_command: str = None, enable_langfuse: bool = True, session_id: str = None):
        """Initialize the Dr. OFF Agent with MCP server connection and optional Langfuse tracing.

        Args:
            mcp_server_command: Command to start the MCP server
            enable_langfuse: Whether to enable Langfuse tracing (default: True)
            session_id: Optional session ID for logging
        """
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
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
                    service_name='dr_off_agent',
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
        # Special value "skip" means don't initialize (for subclasses)
        if mcp_server_command == "skip":
            self.mcp_server = None
        else:
            if mcp_server_command is None:
                # Default command to run our Dr. OFF MCP server
                mcp_server_command = [
                    "python", "-m", "src.ai_agents.dr_off_agent.mcp.server"
                ]
            
            self.mcp_server = MCPServerStdio(
                params=MCPServerStdioParams(
                    command=mcp_server_command[0],
                    args=mcp_server_command[1:],
                    env=dict(os.environ),
                    cwd=str(self.project_root),
                    encoding="utf-8"
                ),
                name="dr-off-server",
                client_session_timeout_seconds=60.0  # Extended timeout for web searches
            )
        
        logger.info(f"Dr. OFF Agent initialized - Session: {self.session_id}")
        logger.info(f"MCP Server Command: {mcp_server_command}")
    
    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for the agent."""
        return """You are Dr. OFF (Ontario Finance & Formulary), a specialized AI assistant for Ontario healthcare financing and coverage.

I help healthcare providers navigate Ontario's complex healthcare coverage landscape by providing accurate, current guidance on:
- OHIP Schedule of Benefits - billing codes, fees, requirements, and coverage rules for related services
- Ontario Drug Benefit (ODB) Formulary - drug coverage, Limited Use criteria, and substitution rules for interchangeable products
- Assistive Devices Program (ADP) - device coverage, eligibility, and funding guidelines
- Coverage decisions and prior authorization requirements
- Generic alternatives, therapeutic substitutions, and cost-effective prescribing options

═══════════════════════════════════════════════════════════════
CRITICAL: 4-STEP ANSWER WORKFLOW (INTERNAL PROCESS - DO NOT SHOW STEPS TO USER)
═══════════════════════════════════════════════════════════════

You MUST follow this structured 4-step process internally for every query to ensure complete, comprehensive answers.

IMPORTANT: These steps are for YOUR INTERNAL REASONING ONLY. Do NOT output step labels (like "STEP 1:", "STEP 2:", etc.) to the user. Only provide the final synthesized answer from Step 4.

STEP 1: PLAN - Identify Intent and Required Fields
───────────────────────────────────────────────────

First, classify the query intent:
- **Billing**: User asks about OHIP billing codes, fees, or how to bill
- **Drug Coverage**: User asks about ODB coverage, formulary status, or drug eligibility
- **Device Funding**: User asks about ADP coverage, device eligibility, or funding
- **Eligibility**: User asks about which patients qualify for coverage
- **Documentation**: User asks about required documentation or forms

Then, identify the required information fields for this intent:

**Billing Intent Schema:**
- primary_codes: List of OHIP codes with descriptions and fees
- modifiers: List of applicable modifiers (if any)
- billing_conditions: When these codes apply
- frequency_limits: Maximum billing frequency (if any)
- common_errors: Common billing mistakes to avoid (if available)
- citations: Source references with specific codes

**Drug Coverage Intent Schema:**
- formulary_status: Whether drug is covered (yes/no/limited use)
- din_numbers: Specific DIN numbers for covered formulations
- limited_use_criteria: LU code and eligibility requirements (if applicable)
- generic_alternatives: List of interchangeable or therapeutic alternatives
- cost_comparison: Pricing differences between options
- citations: Source references with DIN numbers

**Device Funding Intent Schema:**
- device_eligibility: Which device types/models are covered
- funding_amount: ADP funding percentage or dollar amount
- patient_eligibility: Who qualifies (age, medical criteria)
- application_process: How to apply and required documentation
- vendor_requirements: Approved vendors or suppliers
- citations: Source references with device categories

**Eligibility Intent Schema:**
- patient_criteria: Age, diagnosis, or other requirements
- exclusion_criteria: When NOT eligible
- income_thresholds: Financial eligibility limits (if applicable)
- special_programs: Trillium, ODSP, Ontario Works considerations
- citations: Source references with eligibility rules

**Documentation Intent Schema:**
- required_forms: List of forms needed
- required_fields: What must be documented
- submission_process: How to submit
- approval_timeline: Expected processing time
- citations: Source references with form numbers

STEP 2: RETRIEVE - Call Tools and Extract Facts
───────────────────────────────────────────────────

Call the appropriate MCP tools based on intent:
- schedule_get: For OHIP billing codes (Billing intent)
- odb_get: For drug coverage (Drug Coverage intent)
- adp_get: For device funding (Device Funding intent)

**Useful Filters (When You Know Specific Codes/Names):**

**schedule_get filters:**
- `codes`: List[str] - Direct OHIP code lookup (e.g., `["E083A", "E083B"]`)
- Use when: You know specific fee codes from query or previous retrieval

**odb_get filters:**
- `din`: str - Direct DIN lookup (e.g., "02247162")
- `ingredient`: str - Active ingredient name
- `drug_class`: str - Therapeutic class
- Use when: You know specific DIN or ingredient name
- **Tip:** For drug class queries (e.g., "GLP-1 agonists"), query a specific drug name from that class instead

**adp_get filters:**
- `device_category`: str - Device type (e.g., "wheelchair", "walker")
- Use when: Query mentions specific device type

**When to Use Filters:**
- Use `codes` filter for follow-up queries when you already know the OHIP codes
- Use `din` or `ingredient` for drug queries with specific names
- Generally start with NO filters (let tools find relevant info first)

As you review the tool responses, actively extract facts into the schema fields:
- Read each retrieved chunk carefully
- Map facts to schema fields (e.g., "E083A - $245.00" → primary_codes)
- Note which fields are filled and which are EMPTY
- Keep track of missing information

STEP 3: SELF-CHECK - Verify Completeness and Fill Gaps
───────────────────────────────────────────────────────

Review your extracted information against the schema:
- Which required fields are empty or have insufficient information?
- Which fields have partial information that could be expanded?

For EACH missing or incomplete field:
1. Generate a focused sub-query targeting that specific field
   Example: If missing "frequency_limits" for E083A:
   Sub-query: "What are the frequency limits for OHIP code E083A?"

2. Call the appropriate tool with the focused sub-query:
   - First, try the same MCP tool again with the refined sub-query
   - If MCP tool returns insufficient or no results, use web_search as fallback

3. Extract the information and fill the field

**When to Use web_search Tool:**
- MCP tools (schedule_get, odb_get, adp_get) return insufficient or no results
- Need to verify very recent policy changes or updates
- User specifically asks for "latest" or "current" information
- Cross-reference information from official Ontario government websites
- Note: web_search is restricted to trusted Ontario healthcare domains only

**Tool Priority:**
1. Primary: MCP tools (schedule_get, odb_get, adp_get) - structured, embedded knowledge
2. Fallback: web_search - when MCP tools don't have the information

CRITICAL RULES FOR SELF-CHECK:
- Make at least 2 tool calls per query (initial retrieval + ≥1 self-check sub-query)
- Repeat until ≥90% of required fields are filled OR 3 retrieval attempts made
- Try MCP tools first, then web_search if needed
- If all tools return "no results" for a field, mark it as "Not found in available sources"
- NEVER proceed to synthesis with <50% field completeness

STEP 4: SYNTHESIZE - Format Complete Answer (OUTPUT THIS TO USER)
───────────────────────────────────────────────────────────────

Only proceed to synthesis AFTER self-check passes (≥90% fields filled OR 3 attempts made).

THIS IS THE ONLY STEP YOU SHOW TO THE USER. Present a professional, well-structured answer WITHOUT revealing your internal workflow steps.

CRITICAL: Use human-readable section headings, NOT internal schema field names. Transform schema fields into natural language:
- primary_codes → "OHIP Billing Codes" or "Applicable Codes"
- modifiers → "Code Modifiers" or "Additional Modifiers"
- billing_conditions → "Billing Requirements" or "When to Bill"
- frequency_limits → "Frequency Limits" or "Maximum Billing"
- formulary_status → "Coverage Status" or "ODB Coverage"
- din_numbers → "DIN Numbers" or "Covered Products"
- limited_use_criteria → "Limited Use Criteria" or "Eligibility Requirements"
- generic_alternatives → "Generic Alternatives" or "Other Options"
- cost_comparison → "Cost Information" or "Pricing"
- device_eligibility → "Eligible Devices" or "Covered Devices"
- funding_amount → "ADP Funding" or "Coverage Amount"
- patient_eligibility → "Patient Eligibility" or "Who Qualifies"
- application_process → "How to Apply" or "Application Process"

CRITICAL FORMATTING REQUIREMENTS - USE PROPER MARKDOWN:

1. **Use blank lines between all sections** - Add TWO newlines (\n\n) between each section
2. **Use proper markdown headers** - Use ## for main sections, ### for subsections
3. **Use bullet lists properly** - Each bullet point starts with - or * followed by a space
4. **Separate paragraphs** - Add blank line between paragraphs
5. **Format bold text** - Use **text** for bold, *text* for italic
6. **Format inline citations** - Use [Source Name](URL) for inline citations or append citations at end with proper links

Example of CORRECT formatting:

## [Topic/Question Being Answered]

[Opening paragraph directly answering the question with key facts]

## [Human-Readable Section Name]

- Fact 1 with code A007 ($77.20) [Source: [OHIP Schedule](https://ontario.ca/...)]
- Fact 2 with specific details [Source: [ODB Formulary](https://ontario.ca/...)]
- ...

## [Human-Readable Section Name]

- Information 1 with specific billing details [Source: [Fee Schedule](https://ontario.ca/...)]
- Information 2 with DIN and coverage status [Source: [ODB e-Formulary](https://ontario.ca/...)]
- ...

## [Additional Relevant Sections as needed]

## Key Sources

- [OHIP Schedule of Benefits & Fees](https://www.ontario.ca/...) - Specific fee codes
- [Ontario Drug Benefit Formulary](https://www.ontario.ca/...) - DIN coverage details
- [ADP Program Guidelines](https://www.ontario.ca/...) - Funding criteria

Note: If some information wasn't found, briefly mention it at the end in plain language (e.g., "Specific frequency limits were not found in available sources").

═══════════════════════════════════════════════════════════════
MANDATORY RULES - DO NOT VIOLATE
═══════════════════════════════════════════════════════════════

1. ✓ ALWAYS follow all 4 steps internally - never skip Step 3 (Self-Check)
2. ✓ ALWAYS make at least 2 tool calls per query (initial + self-check)
3. ✓ ALWAYS fill ≥90% of required schema fields before synthesis
4. ✓ ALWAYS mark missing fields as "Not found" - never hallucinate
5. ✓ ALWAYS use specific codes/DINs in citations (not just source names)
6. ✗ NEVER show internal step labels (STEP 1, STEP 2, etc.) to the user
7. ✗ NEVER output your planning, retrieval, or self-check reasoning to the user
8. ✗ NEVER use schema field names (like "primary_codes", "din_numbers") as section headings - use human-readable names
9. ✗ NEVER synthesize before self-check passes
10. ✗ NEVER skip schema fields - address all required fields
11. ✗ NEVER make vague statements - be specific with codes and amounts
12. ✓ ONLY output the final synthesized answer from Step 4 to the user

═══════════════════════════════════════════════════════════════

CORE PRINCIPLES:
1. Always cite official Ontario government sources with specific codes and criteria
2. Distinguish between covered vs. non-covered services and medications
3. Provide specific billing codes, DINs, and Limited Use codes when applicable
4. Consider patient eligibility factors (age, income, disability status)
5. Suggest cost-effective alternatives when appropriate
6. Use appropriate medical and billing terminology

QUERY INTERPRETATION:
Be extremely precise about what was specifically asked versus related alternatives:
- For drugs: Distinguish between plain formulations vs. combinations (e.g., "Tylenol" vs "Tylenol with Codeine")
- For services: Be specific about exact OHIP codes requested vs. related services
- For devices: Distinguish between device types, models, and categories

RESPONSE STYLE AND DEPTH:

1. **Provide Rich, Informative Detail**: Your responses should be comprehensive and detailed, not brief summaries. Include:
   - Specific billing codes, fees, and coverage criteria
   - Complete Limited Use requirements and patient eligibility details
   - Relevant context about coverage rules and restrictions
   - Clear explanations of how to apply codes or prescribe covered items
   - Important nuances, exceptions, or special cases
   - Avoid redundancy and fluff, but don't sacrifice clarity or completeness for brevity

2. **Web Search for Additional Detail**: If the user asks for more detail or follow-up information and your MCP tools don't have sufficient information:
   - Use the web_search tool to find additional authoritative sources
   - Search official Ontario government websites (ontario.ca, health.gov.on.ca, etc.)
   - Integrate web search findings with MCP tool results for comprehensive answers

Remember: You have access to comprehensive Ontario healthcare coverage databases through your MCP tools and web search. Use the 4-step workflow to provide complete, detailed, accurate information that helps clinicians optimize patient care while managing costs effectively."""

    async def initialize_mcp_tools(self):
        """Initialize and connect to MCP server tools."""
        try:
            logger.info("MCP server is configured with Agent constructor")
            logger.info("Available MCP tools: schedule_get, odb_get, adp_get")
            
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
                    "data/dr_off_conversations.db"
                )
            
            # Use the MCP server within an async context manager
            async with self.mcp_server as server:
                # Create agent with the connected MCP server
                # Add WebSearchTool with Ontario healthcare/finance-specific allowed domains
                web_search_tool = WebSearchTool(
                    filters=WebSearchToolFilters(
                        allowed_domains=[
                            # Primary Ontario government sites (8)
                            "ontario.ca",
                            "health.gov.on.ca",
                            "ontariohealth.ca",
                            "publichealthontario.ca",
                            "hqontario.ca",
                            "cancercareontario.ca",
                            "ehealthontario.on.ca",
                            "wsib.ca",
                            # Ontario regulatory colleges (4)
                            "cpso.on.ca",
                            "ocp.on.ca",
                            "cno.org",
                            "rcdso.org",
                            # Canadian health organizations (4)
                            "canada.ca",
                            "hc-sc.gc.ca",
                            "cihi.ca",
                            "cma.ca",
                            # Ontario medical/billing orgs (4)
                            "oma.org",
                            "trilliumdrugprogram.ca",
                            "drugcoverage.ca",
                            "ccac-ont.ca"
                        ]
                    ),
                    search_context_size="medium"
                )
                
                from agents import ModelSettings
                agent = Agent(
                    name="Dr. OFF",
                    instructions=self._get_system_instructions(),
                    model="gpt-5-mini",
                    model_settings=ModelSettings(reasoning={"summary": "auto"}),
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
                            "agent": "dr_off",
                            "model": "gpt-4o-mini",
                            "trace_id": trace_id
                        },
                        tags=["dr_off", "streaming"]
                    )
                    # Start a span for this query
                    langfuse_span = self.langfuse.start_span(
                        name="dr_off_query_stream",
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
                    'message': "🔍 Analyzing your query...",
                    'event_type': "analysis_started",
                    'agent_name': "Dr. OFF"
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
                            'agent_name': agent_name
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
                                    message = f"{emoji} Dr. OFF is {tool_desc} for: \"{query}\""
                                else:
                                    message = f"{emoji} Dr. OFF is {tool_desc}..."

                                yield {
                                    'type': 'progress',
                                    'message': message,
                                    'event_type': 'tool_called',
                                    'agent_name': tracker.current_agent,
                                    'tool_name': tool_name,
                                    'details': {'query': query} if query else None
                                }

                        elif event.name == "tool_output":
                            result_count = None
                            if hasattr(event.item, 'output'):
                                output = event.item.output
                                if isinstance(output, dict):
                                    if 'items' in output and isinstance(output['items'], list):
                                        result_count = len(output['items'])
                                    elif 'results' in output and isinstance(output['results'], list):
                                        result_count = len(output['results'])

                            if result_count is not None:
                                message = f"✅ Dr. OFF retrieved {result_count} results"
                            else:
                                message = f"✅ Dr. OFF completed search"

                            yield {
                                'type': 'progress',
                                'message': message,
                                'event_type': 'tool_output',
                                'agent_name': tracker.current_agent,
                                'details': {'result_count': result_count} if result_count else None
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
                                    if len(reasoning_text) > 100:
                                        reasoning_text = reasoning_text[:97] + "..."
                                    message = f"🤔 Dr. OFF reasoning: {reasoning_text}"

                                    yield {
                                        'type': 'progress',
                                        'message': message,
                                        'event_type': 'reasoning',
                                        'agent_name': tracker.current_agent,
                                        'details': {'reasoning': reasoning_text}
                                    }

                        elif event.name == "message_output_created":
                            yield {
                                'type': 'progress',
                                'message': "✍️ Dr. OFF is synthesizing response...",
                                'event_type': 'synthesis_started',
                                'agent_name': "Dr. OFF"
                            }

                    # Then, process the same event for existing data extraction logic
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
                            # Extract function name
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
                            
                            if hasattr(event.item, 'raw_item'):
                                if isinstance(event.item.raw_item, dict):
                                    if 'output' in event.item.raw_item:
                                        output_str = event.item.raw_item['output']
                                else:
                                    if hasattr(event.item.raw_item, 'output'):
                                        output_str = event.item.raw_item.output
                            
                            if not output_str and hasattr(event.item, 'output'):
                                output_str = event.item.output
                            
                            if output_str:
                                # Try to parse output as JSON to extract citations
                                try:
                                    import json
                                    output_data = json.loads(output_str) if isinstance(output_str, str) else output_str
                                    
                                    # Handle MCP text type response
                                    if isinstance(output_data, dict) and output_data.get('type') == 'text':
                                        text_content = output_data.get('text', '')
                                        try:
                                            output_data = json.loads(text_content)
                                        except:
                                            output_data = {'content': text_content}
                                    
                                    citations = extract_citations_from_tool_result(
                                        tool_calls[-1]['name'] if tool_calls else 'unknown',
                                        output_data,
                                        self.trusted_domains
                                    )
                                    
                                    for citation in citations:
                                        if citation not in all_citations:
                                            all_citations.append(citation)
                                            yield {
                                                'type': 'citation',
                                                'content': citation
                                            }
                                except Exception as e:
                                    logger.info(f"Failed to parse tool output as JSON: {e}")
                
                # Update Langfuse span with final output
                if langfuse_span:
                    langfuse_span.update(
                        output={
                            "response": accumulated_text,
                            "tool_calls": tool_calls,
                            "citations": all_citations
                        }
                    )
                    langfuse_span.end()
                
                # Send final completion event with trace_id
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
            # Create session if session_id provided
            session = None
            if session_id:
                # Use persistent SQLite database for sessions
                session = SQLiteSession(
                    session_id, 
                    "data/dr_off_conversations.db"
                )
            
            # Use the MCP server within an async context manager
            async with self.mcp_server as server:
                # Create agent with the connected MCP server
                # Add WebSearchTool with Ontario healthcare/finance-specific allowed domains
                web_search_tool = WebSearchTool(
                    filters=WebSearchToolFilters(
                        allowed_domains=[
                            # Primary Ontario government sites (8)
                            "ontario.ca",
                            "health.gov.on.ca",
                            "ontariohealth.ca",
                            "publichealthontario.ca",
                            "hqontario.ca",
                            "cancercareontario.ca",
                            "ehealthontario.on.ca",
                            "wsib.ca",
                            # Ontario regulatory colleges (4)
                            "cpso.on.ca",
                            "ocp.on.ca",
                            "cno.org",
                            "rcdso.org",
                            # Canadian health organizations (4)
                            "canada.ca",
                            "hc-sc.gc.ca",
                            "cihi.ca",
                            "cma.ca",
                            # Ontario medical/billing orgs (4)
                            "oma.org",
                            "trilliumdrugprogram.ca",
                            "drugcoverage.ca",
                            "ccac-ont.ca"
                        ]
                    ),
                    search_context_size="medium"
                )
                
                from agents import ModelSettings
                agent = Agent(
                    name="Dr. OFF",
                    instructions=self._get_system_instructions(),
                    model="gpt-5-mini",
                    model_settings=ModelSettings(reasoning={"summary": "auto"}),
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
                            "agent": "dr_off",
                            "model": "gpt-4o-mini",
                            "trace_id": trace_id
                        },
                        tags=["dr_off", "non-streaming"]
                    )
                    # Start a span for this query
                    langfuse_span = self.langfuse.start_span(
                        name="dr_off_query",
                        input={"query": user_input}
                    )
                    logger.debug(f"Created Langfuse trace: {trace_id}")
                
                # Run the agent
                result = await Runner.run(
                    starting_agent=agent,
                    input=user_input,
                    session=session
                )
                
                # Extract tool calls and citations
                tool_calls = []
                all_citations = []
                
                for item in result.new_items:
                    # Check for tool calls
                    if hasattr(item, 'name') and hasattr(item, 'arguments'):
                        tool_calls.append({
                            'name': item.name,
                            'arguments': str(item.arguments)
                        })
                        
                        # Extract citations if result available
                        if hasattr(item, 'result'):
                            citations = extract_citations_from_tool_result(
                                item.name,
                                item.result,
                                self.trusted_domains
                            )
                            all_citations.extend(citations)
                
                # Deduplicate citations
                seen_citations = set()
                unique_citations = []
                for citation in all_citations:
                    key = f"{citation.get('domain', '')}_{citation.get('title', '').lower().strip()}"
                    if key not in seen_citations:
                        seen_citations.add(key)
                        unique_citations.append(citation)
                
                # Calculate confidence
                confidence = 0.8
                if unique_citations:
                    confidence = min(0.95, 0.8 + (len(unique_citations) * 0.05))
                
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
                
                return {
                    'response': result.final_output,
                    'tool_calls': tool_calls,
                    'tools_used': [tc['name'] for tc in tool_calls],
                    'citations': unique_citations,
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
                'confidence': 0.0,
                'error': str(e),
                'trace_id': trace_id  # Include trace_id even on error
            }
    
    def _create_error_response(self, error_message: str, query: str) -> str:
        """Create a fallback response for errors."""
        return f"""I apologize, but I'm experiencing technical difficulties accessing the Ontario healthcare coverage databases.

For your query: "{query[:100]}..."

Please try:
1. Consulting the official sources directly:
   - OHIP Schedule: https://www.ontario.ca/page/ohip-schedule-benefits-and-fees
   - ODB Formulary: https://www.ontario.ca/page/check-medication-coverage/
   - ADP Program: https://www.ontario.ca/page/assistive-devices-program

2. Trying your query again with more specific details (e.g., exact drug names, DINs, or billing codes)

3. Checking back in a few minutes

Technical details: {error_message}"""
    
    def get_agent(self, mcp_server=None):
        """
        Get the OpenAI Agent instance for use as a tool in orchestrators.
        
        Args:
            mcp_server: The active MCP server context (from async with statement)
                       If None, will use self.mcp_server
        
        Returns:
            Agent instance configured with Dr. OFF's instructions and MCP tools
        """
        server = mcp_server if mcp_server is not None else self.mcp_server
        
        # Create WebSearchTool with Ontario healthcare/finance-specific allowed domains
        web_search_tool = WebSearchTool(
            filters=WebSearchToolFilters(
                allowed_domains=[
                    # Primary Ontario government sites (8)
                    "ontario.ca",
                    "health.gov.on.ca",
                    "ontariohealth.ca",
                    "publichealthontario.ca",
                    "hqontario.ca",
                    "cancercareontario.ca",
                    "ehealthontario.on.ca",
                    "wsib.ca",
                    # Ontario regulatory colleges (4)
                    "cpso.on.ca",
                    "ocp.on.ca",
                    "cno.org",
                    "rcdso.org",
                    # Canadian health organizations (4)
                    "canada.ca",
                    "hc-sc.gc.ca",
                    "cihi.ca",
                    "cma.ca",
                    # Ontario medical/billing orgs (4)
                    "oma.org",
                    "trilliumdrugprogram.ca",
                    "drugcoverage.ca",
                    "ccac-ont.ca"
                ]
            ),
            search_context_size="medium"
        )
        
        from agents import ModelSettings
        return Agent(
            name="Dr. OFF",
            instructions=self._get_system_instructions(),
            model="gpt-5-mini",
            model_settings=ModelSettings(reasoning={"summary": "auto"}),
            mcp_servers=[server] if server else [],
            tools=[web_search_tool]
        )


async def create_dr_off_agent(mcp_server_command: list = None) -> DrOffAgent:
    """Factory function to create and initialize Dr. OFF Agent."""
    
    # Create agent instance with MCP server command
    agent = DrOffAgent(mcp_server_command)
    
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
    
    agent = await create_dr_off_agent()
    
    test_queries = [
        "What's the OHIP billing code for a comprehensive assessment?",
        "Is rosuvastatin covered by ODB? What about the generic?",
        "Can my patient get ADP funding for a power wheelchair?"
    ]
    
    for test_query in test_queries:
        print(f"\nQuery: {test_query}")
        print("-" * 60)
        
        result = await agent.query(test_query)
        
        if isinstance(result, dict):
            print(f"🔧 Tools Used: {', '.join(result['tools_used']) if result['tools_used'] else 'None'}")
            print(f"📚 Citations: {len(result.get('citations', []))}")
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
        else:
            print(result)


if __name__ == "__main__":
    asyncio.run(test_agent())