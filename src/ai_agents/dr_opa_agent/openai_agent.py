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

        # Extract from items (used in PolicyCheckResponse and other responses)
        if 'items' in result_data and isinstance(result_data['items'], list):
            logger.debug(f"Found {len(result_data['items'])} items in tool result")
            for item in result_data['items']:
                if isinstance(item, dict) and 'metadata' in item:
                    metadata = item['metadata']
                    if 'source_url' in metadata and metadata['source_url']:
                        citation = {
                            'id': f"item_{uuid.uuid4().hex[:8]}",
                            'title': metadata.get('document_title', item.get('source', 'Document')),
                            'source': metadata.get('source_org', 'Unknown'),
                            'source_type': 'policy',
                            'url': metadata['source_url'],
                            'domain': extract_domain(metadata['source_url']),
                            'is_trusted': extract_domain(metadata['source_url']) in trusted_domains,
                            'access_date': datetime.now().isoformat(),
                            'relevance_score': item.get('relevance_score', 0.8),
                            'snippet': metadata.get('section_heading', '')
                        }
                        citations.append(citation)
                        logger.debug(f"Extracted citation from item: {citation['title']} - {citation['url']}")

    except Exception as e:
        logger.warning(f"Error extracting citations from {tool_name}: {e}")
        import traceback
        logger.warning(traceback.format_exc())

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
    
    def __init__(self, mcp_server_command: str = None, enable_langfuse: bool = True, session_id: str = None):
        """Initialize the Dr. OPA Agent with MCP server connection and optional Langfuse tracing.

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

═══════════════════════════════════════════════════════════════
CRITICAL: 4-STEP ANSWER WORKFLOW (INTERNAL PROCESS - DO NOT SHOW STEPS TO USER)
═══════════════════════════════════════════════════════════════

You MUST follow this structured 4-step process internally for every query to ensure complete, comprehensive answers.

IMPORTANT: These steps are for YOUR INTERNAL REASONING ONLY. Do NOT output step labels (like "STEP 1:", "STEP 2:", etc.) to the user. Only provide the final synthesized answer from Step 4.

STEP 1: PLAN - Identify Intent and Required Fields
───────────────────────────────────────────────────

First, classify the query intent:
- **CPSO Policy**: User asks about regulatory requirements, professional expectations, or college policies
- **IPAC Guidelines**: User asks about infection prevention and control protocols
- **Clinical Programs**: User asks about Ontario Health programs, screening, or care pathways
- **Clinical Tools**: User asks about decision support tools, algorithms, or calculators
- **Quality Standards**: User asks about Ontario Health quality standards or best practices
- **Choosing Wisely**: User asks about avoiding unnecessary tests, procedures, or overuse

Then, identify the required information fields for this intent:

**CPSO Policy Intent Schema:**
- regulatory_requirements: Mandatory requirements and expectations (from "expectation" level policies)
- compliance_obligations: What physicians must do
- best_practice_advice: Recommended best practices (from "advice" level policies)
- documentation_requirements: Required documentation standards
- sanctions_consequences: Consequences of non-compliance (if applicable)
- implementation_guidance: How to implement in practice
- related_policies: Other relevant CPSO policies for context
- citations: Source references with policy titles, URLs, and specific sections

**IPAC Guidelines Intent Schema:**
- requirements_mandatory: Mandatory infection control measures
- recommendations_best_practice: Recommended best practices
- setting_specifics: Requirements for specific healthcare settings (hospital, clinic, LTC)
- equipment_procedures: Required equipment and procedures
- validation_monitoring: How to validate compliance
- citations: Source references with PHO document sections

**Clinical Programs Intent Schema:**
- program_eligibility: Who qualifies for the program
- referral_pathways: How to refer patients
- coverage_criteria: What services/tests are covered
- access_procedures: How patients access the program
- program_updates: Recent changes or transitions
- citations: Source references with program names and dates

**Clinical Tools Intent Schema:**
- tool_description: What the tool is and its purpose
- clinical_application: When and how to use it
- interpretation_guidance: How to interpret results
- limitations_caveats: Important limitations or considerations
- access_information: How to access the tool
- citations: Source references with tool names and versions

**Quality Standards Intent Schema:**
- quality_statements: Key quality statements for the condition
- quality_indicators: Measurable indicators of quality care
- implementation_guidance: How to implement in practice
- evidence_base: Supporting evidence for recommendations
- measurement_tools: How to measure adherence
- citations: Source references with standard numbers and dates

**Choosing Wisely Intent Schema:**
- recommendations: Specific "don't do" recommendations
- evidence_rationale: Why these practices should be avoided
- specialty_specific: Which specialty issued the recommendation
- alternative_approaches: What to do instead
- patient_communication: How to discuss with patients
- citations: Source references with recommendation numbers

STEP 2: RETRIEVE - Call Tools and Extract Facts
───────────────────────────────────────────────────

Call the appropriate MCP tools based on intent:
- opa_policy_check: For CPSO policy questions (uses two-tier architecture - auto-classifies intent and scopes to relevant policies)
- opa_ipac_guidance: For infection control questions
- opa_program_lookup: For clinical programs
- opa_clinical_tools: For CEP decision support tools (uses two-tier architecture - auto-classifies intent and scopes to relevant tools)
- opa_quality_standards: For quality standards (uses two-tier architecture - auto-classifies intent and scopes to relevant standards)
- opa_choosing_wisely: For avoiding unnecessary care
- opa_search_sections: For general or multi-source queries

**Two-Tier Retrieval (opa_policy_check, opa_clinical_tools, opa_quality_standards):**

These tools auto-classify queries and scope retrieval:
- **Catalog queries** ("List all CPSO policies", "What tools do you have?") → Returns complete catalog with all available resources
- **Discovery queries** ("What policies exist for X?") → Returns overviews from 2-4 relevant resources
- **Specific queries** ("What are the requirements for Y?") → Returns detailed chunks with parent context from 1-2 resources

Just call with your natural query - the tools handle classification, scoping, and context assembly automatically.

**Sources Filter (Target Specific Organizations):**

All tools support a `sources` filter to search specific organizations:
- `filters={"sources": ["cpso"]}` → CPSO policies only
- `filters={"sources": ["pho"]}` → PHO IPAC guidance only
- `filters={"sources": ["cep"]}` → CEP clinical tools only
- `filters={"sources": ["quality_standards"]}` → Quality standards only
- `filters={"sources": ["choosing_wisely"]}` → Choosing Wisely only

**When to Use Sources Filter:**
- User explicitly asks "What does CPSO say about X?" → Use `filters={"sources": ["cpso"]}`
- User explicitly asks "PHO guidelines for Y" → Use `filters={"sources": ["pho"]}`
- User explicitly asks "CEP tools for Z" → Use `filters={"sources": ["cep"]}`
- User asks broad question → Omit filter (searches all sources)
- Note: Sources filter is OPTIONAL - two-tier tools (policy_check, clinical_tools, quality_standards) auto-scope to relevant resources

As you review the tool responses, actively extract facts into the schema fields:
- Read each retrieved chunk carefully
- Map facts to schema fields (e.g., "Must document informed consent" → regulatory_requirements)
- Note which fields are filled and which are EMPTY
- Keep track of missing information

STEP 3: SELF-CHECK - Verify Completeness and Fill Gaps
───────────────────────────────────────────────────────

Review your extracted information against the schema:
- Which required fields are empty or have insufficient information?
- Which fields have partial information that could be expanded?

For EACH missing or incomplete field:
1. Generate a focused sub-query targeting that specific field
   Example: If missing "documentation_requirements" for virtual care:
   Sub-query: "What documentation is required by CPSO for virtual care?"

2. Call the appropriate tool with the focused sub-query:
   - First, try the same MCP tool again with the refined sub-query
   - If MCP tool returns insufficient or no results, use web_search as fallback

3. Extract the information and fill the field

**When to Use web_search Tool:**
- MCP tools return insufficient or no results for required fields
- Need to verify very recent policy changes or updates
- User specifically asks for "latest" or "current" guidance
- Cross-reference information from official Ontario healthcare websites
- Note: web_search is restricted to trusted Ontario healthcare domains only

**Tool Priority:**
1. Primary: MCP tools (opa_policy_check, opa_ipac_guidance, etc.) - structured, embedded knowledge
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
- regulatory_requirements → "Regulatory Requirements" or "What CPSO Requires"
- compliance_obligations → "Compliance Obligations" or "Physician Responsibilities"
- best_practice_advice → "Best Practice Recommendations" or "Recommended Practices"
- documentation_requirements → "Documentation Requirements" or "Required Documentation"
- sanctions_consequences → "Consequences of Non-Compliance" or "Enforcement"
- implementation_guidance → "Implementation Guidance" or "How to Apply This"
- related_policies → "Related Policies" or "See Also"

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

- Requirement/guideline 1 [Source: [CPSO Policy](https://cpso.on.ca/...)]
- Requirement/guideline 2 [Source: [Ontario Health](https://ontariohealth.ca/...)]
- ...

## [Human-Readable Section Name]

- Information 1 with inline citation [Source: [PHO Guidelines](https://publichealthontario.ca/...)]
- Information 2 with reference [Source: [OHIP Schedule](https://ontario.ca/...)]
- ...

## [Additional Relevant Sections as needed]

## Key Sources

- [CPSO Medical Records Documentation](https://www.cpso.on.ca/...) - Specific section
- [Ontario Health Hypertension Quality Standard](https://www.hqontario.ca/...) - Specific section
- [OHIP Schedule of Benefits](https://www.ontario.ca/...) - Fee codes

Note: If some information wasn't found, briefly mention it at the end in plain language (e.g., "Specific enforcement penalties were not found in available sources").

═══════════════════════════════════════════════════════════════
MANDATORY RULES - DO NOT VIOLATE
═══════════════════════════════════════════════════════════════

1. ✓ ALWAYS follow all 4 steps internally - never skip Step 3 (Self-Check)
2. ✓ ALWAYS make at least 2 tool calls per query (initial + self-check)
3. ✓ ALWAYS fill ≥90% of required schema fields before synthesis
4. ✓ ALWAYS mark missing fields as "Not found" - never hallucinate
5. ✓ ALWAYS distinguish between mandatory requirements vs. recommendations
6. ✗ NEVER show internal step labels (STEP 1, STEP 2, etc.) to the user
7. ✗ NEVER output your planning, retrieval, or self-check reasoning to the user
8. ✗ NEVER use schema field names (like "regulatory_requirements") as section headings - use human-readable names
9. ✗ NEVER synthesize before self-check passes
10. ✗ NEVER skip schema fields - address all required fields
11. ✗ NEVER make vague statements - cite specific policy sections
12. ✓ ONLY output the final synthesized answer from Step 4 to the user

═══════════════════════════════════════════════════════════════

RESPONSE STYLE AND DEPTH:

1. **Provide Rich, Informative Detail**: Your responses should be comprehensive and detailed, not brief summaries. Include:
   - Specific requirements, criteria, and conditions
   - Relevant context and background information
   - Clear explanations of how policies apply in practice
   - Important nuances, exceptions, or special cases
   - Avoid redundancy and fluff, but don't sacrifice clarity or completeness for brevity

2. **Web Search for Additional Detail**: If the user asks for more detail or follow-up information and your MCP tools don't have sufficient information:
   - Use the web_search tool to find additional authoritative sources
   - Search official Ontario health authority websites (CPSO, Ontario Health, PHO, etc.)
   - Integrate web search findings with MCP tool results for comprehensive answers

═══════════════════════════════════════════════════════════════

Remember: You have access to comprehensive Ontario practice guidance through your MCP tools and web search. Use the 4-step workflow to provide complete, detailed, accurate information that helps clinicians deliver evidence-based, compliant care."""

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
                
                from agents import ModelSettings
                agent = Agent(
                    name="Dr. OPA",
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

                # Import StreamingProgressTracker for user-friendly progress
                from src.ai_agents.diagnostic_orchestrator.streaming_progress import StreamingProgressTracker
                from agents.stream_events import AgentUpdatedStreamEvent, RunItemStreamEvent
                tracker = StreamingProgressTracker()

                # Emit initial progress message
                yield {
                    'type': 'progress',
                    'message': "🔍 Analyzing your query...",
                    'event_type': "analysis_started",
                    'agent_name': "Dr. OPA"
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
                        # Debug: log what event.name we're getting
                        logger.info(f"RunItemStreamEvent detected - event.name: {event.name}")

                        if event.name == "tool_called":
                            if hasattr(event.item, 'raw_item') and hasattr(event.item.raw_item, 'name'):
                                tool_name = event.item.raw_item.name
                                tool_desc = tracker.get_tool_description(tool_name)
                                emoji = tracker.get_agent_emoji(tracker.current_agent)

                                query = None
                                if hasattr(event.item.raw_item, 'arguments'):
                                    query = tracker.get_query_from_arguments(event.item.raw_item.arguments)

                                if query:
                                    message = f"{emoji} Dr. OPA is {tool_desc} for: \"{query}\""  # No truncation
                                else:
                                    message = f"{emoji} Dr. OPA is {tool_desc}..."

                                progress_event = {
                                    'type': 'progress',
                                    'message': message,
                                    'event_type': 'tool_called',
                                    'agent_name': tracker.current_agent,
                                    'tool_name': tool_name,
                                    'details': {'query': query} if query else None
                                }
                                logger.info(f"🔥 YIELDING PROGRESS EVENT: {progress_event}")
                                yield progress_event

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
                                message = f"✅ Dr. OPA retrieved {result_count} results"
                            else:
                                message = f"✅ Dr. OPA completed search"

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
                                    message = f"🤔 Dr. OPA reasoning: {reasoning_text}"

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
                                'message': "✍️ Dr. OPA is synthesizing response...",
                                'event_type': 'synthesis_started',
                                'agent_name': "Dr. OPA"
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
                
                from agents import ModelSettings
                agent = Agent(
                    name="Dr. OPA",
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
        
        from agents import ModelSettings
        return Agent(
            name="Dr. OPA",
            instructions=self._get_system_instructions(),
            model="gpt-5-mini",
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