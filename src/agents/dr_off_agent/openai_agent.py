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
    from agents import Agent, Runner
    from agents.memory import SQLiteSession
    from agents.mcp.server import MCPServerStdio, MCPServerStdioParams
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
    """Dr. OFF OpenAI Agent with MCP integration."""
    
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
    
    def __init__(self, mcp_server_command: str = None):
        """Initialize the Dr. OFF Agent with MCP server connection."""
        self.session_id = session_id
        self.project_root = project_root
        self.trusted_domains = load_trusted_domains()
        logger.info(f"Loaded {len(self.trusted_domains)} trusted domains for citation validation")
        
        # Initialize MCP server connection using STDIO
        if mcp_server_command is None:
            # Default command to run our Dr. OFF MCP server
            mcp_server_command = [
                "python", "-m", "src.agents.dr_off_agent.mcp.server"
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
            client_session_timeout_seconds=30.0
        )
        
        logger.info(f"Dr. OFF Agent initialized - Session: {self.session_id}")
        logger.info(f"MCP Server Command: {mcp_server_command}")
    
    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for the agent."""
        return """You are Dr. OFF (Ontario Finance & Formulary), a specialized AI assistant for Ontario healthcare financing and coverage.

I help healthcare providers navigate Ontario's complex healthcare coverage landscape by providing accurate, current guidance on:
- OHIP Schedule of Benefits - billing codes, fees, and requirements
- Ontario Drug Benefit (ODB) Formulary - drug coverage and Limited Use criteria
- Assistive Devices Program (ADP) - device coverage and eligibility
- Coverage decisions and prior authorization requirements
- Generic alternatives and cost-effective prescribing

CORE PRINCIPLES:
1. Always cite official Ontario government sources with specific codes and criteria
2. Distinguish between covered vs. non-covered services and medications
3. Provide specific billing codes, DINs, and Limited Use codes when applicable
4. Consider patient eligibility factors (age, income, disability status)
5. Suggest cost-effective alternatives when appropriate
6. Use appropriate medical and billing terminology

CRITICAL: QUERY INTERPRETATION PRECISION
When answering queries, be extremely precise about what was specifically asked versus related alternatives:

**For Drug Queries:**
- If asked about "Tylenol" → interpret as plain acetaminophen (typically NOT covered by ODB)
- If asked about "Tylenol with Codeine" → interpret as acetaminophen + codeine combination (may be covered)
- If search returns related but different medications, clearly distinguish:
  ✓ "The specific drug you asked about (plain Tylenol) is NOT covered by ODB"
  ✓ "However, related products like Tylenol with Codeine have some covered formulations"
  ✗ Don't say "Yes, Tylenol is covered" when only codeine combinations are covered

**For Service Queries:**
- Be specific about exact services requested vs. related services
- Distinguish between different fee codes even if similar
- Clarify when broader categories exist but specific items differ

**For Device Queries:**
- Distinguish between device types, models, and categories
- Be clear about what specific device qualifies vs. alternatives

TOOL SELECTION STRATEGY:
Analyze each query and select the most appropriate MCP tools:

- **schedule_get**: For OHIP billing codes, fee schedules, service requirements
  Keywords: OHIP, billing, code, A001, fee, schedule, physician services
  Example: "What's the billing code for a comprehensive assessment?"

- **odb_get**: For drug coverage, Limited Use criteria, generic alternatives
  Keywords: drug, medication, ODB, formulary, covered, Limited Use, LU code, DIN
  Example: "Is rosuvastatin covered by ODB?"

- **adp_get**: For assistive device coverage, eligibility, funding amounts
  Keywords: wheelchair, walker, hearing aid, CPAP, assistive device, ADP
  Example: "Can my patient get funding for a power wheelchair?"
  Note: Supports natural language queries

RESPONSE STRUCTURE:
1. **Direct Answer**: Clear yes/no on coverage for the EXACT item requested
   - State specifically what was asked about
   - Don't conflate related items with the requested item
2. **Coverage Details**: Requirements, limitations, and eligibility criteria for the specific item
3. **Billing Information**: Specific codes, fees, and documentation needs
4. **Alternatives**: If the requested item isn't covered, mention related covered options
   - Clearly distinguish: "While X is not covered, related product Y is covered"
5. **Next Steps**: How to apply, get prior authorization, or appeal

CITATION FORMAT:
- Use specific codes and references: [OHIP Code A001 - Comprehensive Assessment]
- Include DINs for drugs: [Rosuvastatin - DIN 02247162]
- Reference Limited Use codes: [LU Code 513 - Statins]
- Link to official sources when available

IMPORTANT CONSIDERATIONS:
- Coverage can change - always note to verify current eligibility
- Consider Trillium Drug Program for high drug costs
- Some services require prior authorization
- Income testing may apply for certain programs
- Different coverage for seniors (65+) vs. general population

Remember: You have access to the comprehensive Ontario healthcare coverage databases through your MCP tools. Use them to provide specific, actionable information that helps clinicians optimize patient care while managing costs effectively."""

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
    
    async def query_stream(self, user_input: str, session_id: str = None):
        """Process a user query and stream the response."""
        logger.info(f"Processing streaming query: {user_input[:100]}...")
        
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
                agent = Agent(
                    name="Dr. OFF",
                    instructions=self._get_system_instructions(),
                    model="gpt-4o-mini",
                    mcp_servers=[server]
                )
                
                # Use run_streamed for streaming response with session
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
                            # Extract function name
                            tool_name = 'unknown'
                            tool_args = ''
                            
                            if hasattr(event.item, 'raw_item'):
                                raw_item = event.item.raw_item
                                if hasattr(raw_item, 'function'):
                                    tool_name = raw_item.function.name
                                    tool_args = raw_item.function.arguments
                                elif hasattr(raw_item, 'name'):
                                    tool_name = raw_item.name
                                    tool_args = str(getattr(raw_item, 'arguments', ''))
                            
                            tool_call_data = {
                                'name': tool_name,
                                'arguments': str(tool_args)
                            }
                            tool_calls.append(tool_call_data)
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
                
                # Send final completion event
                yield {
                    'type': 'complete',
                    'content': accumulated_text,
                    'tool_calls': tool_calls,
                    'citations': all_citations
                }
                
        except Exception as e:
            logger.error(f"Error in streaming query: {e}")
            yield {
                'type': 'error',
                'content': str(e)
            }
    
    async def query(self, user_input: str, session_id: str = None) -> Dict:
        """Process a user query and return the agent's response."""
        logger.info(f"Processing query: {user_input[:100]}...")
        
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
                agent = Agent(
                    name="Dr. OFF",
                    instructions=self._get_system_instructions(),
                    model="gpt-4o-mini",
                    mcp_servers=[server]
                )
                
                # Run the agent with the user input and session
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
                
                return {
                    'response': result.final_output,
                    'tool_calls': tool_calls,
                    'tools_used': [tc['name'] for tc in tool_calls],
                    'citations': unique_citations,
                    'confidence': confidence
                }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            error_response = self._create_error_response(str(e), user_input)
            return {
                'response': error_response,
                'tool_calls': [],
                'tools_used': [],
                'citations': [],
                'confidence': 0.0,
                'error': str(e)
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