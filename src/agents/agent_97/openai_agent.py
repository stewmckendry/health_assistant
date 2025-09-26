#!/usr/bin/env python3
"""
Agent 97 OpenAI Agent Implementation

An intelligent medical education assistant that provides information from
97 trusted medical sources using the OpenAI Agents SDK with MCP integration.
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
import re

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import yaml for loading trusted domains
try:
    import yaml
except ImportError:
    yaml = None

from agents import Agent
from agents.mcp.server import MCPServerStdio, MCPServerStdioParams

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
log_dir = Path("logs/agent_97")
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


class Agent97:
    """Agent 97 - Medical Education AI Assistant with 97 trusted sources."""
    
    def __init__(self, mcp_server_command: str = None):
        """Initialize Agent 97 with MCP server connection."""
        self.session_id = session_id
        self.project_root = project_root
        
        # Initialize MCP server connection using STDIO
        if mcp_server_command is None:
            # Default command to run our Agent 97 MCP server
            mcp_server_command = [
                "python", "-m", "src.agents.agent_97.mcp.server"
            ]
        
        self.mcp_server = MCPServerStdio(
            params=MCPServerStdioParams(
                command=mcp_server_command[0],
                args=mcp_server_command[1:],
                env=dict(os.environ),  # Pass current environment variables
                cwd=str(self.project_root),  # Set working directory
                encoding="utf-8"
            ),
            name="agent-97-server",
            client_session_timeout_seconds=120.0  # Increase timeout to 2 minutes for Claude API calls
        )
        
        logger.info(f"Agent 97 initialized - Session: {self.session_id}")
        logger.info(f"MCP Server Command: {mcp_server_command}")
    
    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for the agent."""
        return """You are Agent 97, a medical education AI assistant that provides reliable health information from 97 trusted medical sources.

Your mission is to deliver accurate, educational health information to patients and the public, with strict safety guardrails to ensure responses are appropriate and never replace professional medical advice.

CORE PRINCIPLES:
1. **Educational Purpose Only**: Provide health education, never diagnose conditions or prescribe treatments
2. **Trusted Sources**: Use information exclusively from the 97 vetted medical domains
3. **Safety First**: Apply comprehensive guardrails for emergency detection and crisis intervention
4. **Clear Communication**: Use accessible language appropriate for patients
5. **Proper Citations**: Always cite sources with links to trusted medical websites
6. **Medical Disclaimers**: Include appropriate disclaimers about seeking professional care

THE 97 TRUSTED DOMAINS include:
- **Canadian Authorities**: Ontario Health, CPSO, Public Health Ontario, Health Canada
- **US Medical Centers**: Mayo Clinic, Johns Hopkins, Cleveland Clinic, Stanford Medicine
- **Medical Journals**: NEJM, Lancet, JAMA, BMJ, Nature Medicine
- **Global Health**: WHO, CDC, NIH, NHS
- **Disease Organizations**: Heart & Stroke, Cancer Society, Diabetes Association
- **Evidence-Based**: UpToDate, Cochrane, Clinical Trials

TOOL USAGE STRATEGY:
You have access to MCP tools for processing medical queries:

- **agent_97_query**: Main tool for medical education queries
  Use for: All health questions requiring comprehensive responses
  Features: Built-in guardrails, citation extraction, emergency detection
  
- **agent_97_get_trusted_domains**: List all 97 trusted sources
  Use when: User asks about your sources or wants to know which sites you use
  
- **agent_97_health_check**: Verify system status
  Use when: Troubleshooting or user reports issues
  
- **agent_97_get_disclaimers**: Retrieve medical disclaimers
  Use when: User asks about safety measures or disclaimers

RESPONSE GUIDELINES:

1. **For General Health Questions**:
   - Use agent_97_query to get comprehensive, cited response
   - Include educational content with proper medical terminology explained
   - Add relevant preventive care or lifestyle recommendations
   - Suggest when to see a healthcare provider

2. **For Symptom Inquiries**:
   - Provide general educational information about conditions
   - NEVER diagnose based on symptoms
   - Always recommend professional evaluation
   - Include emergency warning signs if relevant

3. **For Medication Questions**:
   - Provide general drug information and common uses
   - Include typical side effects from trusted sources
   - NEVER recommend dosages or medication changes
   - Emphasize consulting prescribing physician

4. **For Emergency Content**:
   - The guardrails will detect emergencies automatically
   - Support the emergency redirect response
   - Don't try to override safety measures

5. **For Mental Health Concerns**:
   - Show empathy and understanding
   - Let guardrails handle crisis situations
   - Provide general mental health education
   - Include professional resources

EXAMPLE INTERACTIONS:

User: "What are the symptoms of diabetes?"
Approach: Use agent_97_query to provide comprehensive education about diabetes types, symptoms, risk factors, and importance of screening.

User: "I'm having severe chest pain"
Approach: The guardrails will detect this emergency and provide appropriate emergency response. Support this safety measure.

User: "What does metformin do?"
Approach: Use agent_97_query to explain the medication's purpose, how it works, common uses, and general side effects, while emphasizing consulting with prescribing physician.

User: "What medical sources do you use?"
Approach: Use agent_97_get_trusted_domains to show the 97 vetted sources, explaining the rigorous selection criteria.

IMPORTANT REMINDERS:
- Never diagnose conditions ("You have...")
- Never prescribe treatments ("You should take...")
- Never contradict emergency responses from guardrails
- Always maintain educational tone
- Include disclaimers naturally in responses
- Cite sources to build trust
- Show empathy while maintaining boundaries

Remember: You are powered by sophisticated guardrails that ensure safe responses. Trust the system to handle emergencies and crisis situations appropriately. Your role is to provide excellent medical education while the safety systems protect users."""

    async def initialize_mcp_tools(self):
        """Initialize and connect to MCP server tools."""
        try:
            logger.info("MCP server is configured with Agent constructor")
            logger.info("Available MCP tools: agent_97_query, agent_97_query_stream, agent_97_get_trusted_domains, agent_97_health_check, agent_97_get_disclaimers")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP tools: {e}")
            logger.warning("Agent will operate without MCP tools - responses will be limited")
            return False
    
    async def query(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a user query and return the agent's response."""
        logger.info(f"Processing query: {user_input[:100]}...")
        
        try:
            # Import Runner here to avoid circular imports
            from agents import Runner
            
            # Use the MCP server within an async context manager
            async with self.mcp_server as server:
                # Create agent with the connected MCP server
                agent = Agent(
                    name="Agent 97",
                    instructions=self._get_system_instructions(),
                    model="gpt-4o-mini",
                    mcp_servers=[server]
                )
                
                # Run the agent with the user input
                result = await Runner.run(
                    starting_agent=agent,
                    input=user_input,
                    context=context
                )
                
                # Extract tool calls and citations from the result
                tool_calls = []
                all_citations = []
                
                logger.debug(f"Examining {len(result.new_items)} result items for tool calls")
                
                for i, item in enumerate(result.new_items):
                    # Check various patterns for tool calls
                    if hasattr(item, 'name') and hasattr(item, 'arguments'):
                        tool_call = {
                            'name': item.name,
                            'arguments': str(item.arguments) if hasattr(item, 'arguments') else ''
                        }
                        tool_calls.append(tool_call)
                        
                        # Extract citations from tool result if available
                        if hasattr(item, 'result'):
                            citations = self._extract_citations_from_tool_result(item.result)
                            all_citations.extend(citations)
                            
                    elif hasattr(item, 'tool_calls') and item.tool_calls:
                        for tool_call in item.tool_calls:
                            tool_calls.append({
                                'name': tool_call.function.name,
                                'arguments': tool_call.function.arguments
                            })
                
                # Also check raw_responses for tool calls
                for response in result.raw_responses:
                    if hasattr(response, 'choices'):
                        for choice in response.choices:
                            if hasattr(choice, 'message') and hasattr(choice.message, 'tool_calls'):
                                if choice.message.tool_calls:
                                    for tool_call in choice.message.tool_calls:
                                        tool_calls.append({
                                            'name': tool_call.function.name,
                                            'arguments': tool_call.function.arguments
                                        })
                
                # Deduplicate citations by URL
                unique_citations = []
                seen_urls = set()
                for citation in all_citations:
                    url = citation.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_citations.append(citation)
                
                # Create simple highlights from key citations
                highlights = []
                for i, citation in enumerate(unique_citations[:3]):  # Top 3 citations
                    highlights.append({
                        'point': f"Information from {citation.get('title', 'trusted medical source')}",
                        'citations': [citation['id']],
                        'confidence': 0.9,
                        'policy_level': 'guideline'
                    })
                
                # Calculate confidence based on citations
                confidence = 0.8  # Base confidence
                if unique_citations:
                    trusted_count = sum(1 for c in unique_citations if c.get('is_trusted', False))
                    if trusted_count > 0:
                        confidence = min(0.95, 0.8 + (trusted_count * 0.03))
                
                # Log tool calls and citations
                if tool_calls:
                    logger.info(f"MCP Tools called: {[tc['name'] for tc in tool_calls]}")
                    for tc in tool_calls:
                        logger.info(f"  - {tc['name']}: {tc['arguments'][:100]}...")
                else:
                    logger.info("No MCP tools were called")
                
                if unique_citations:
                    trusted_count = sum(1 for c in unique_citations if c.get('is_trusted', False))
                    logger.info(f"Extracted {len(unique_citations)} citations ({trusted_count} trusted)")
                
                logger.info(f"Query processed successfully. Response length: {len(result.final_output)}")
                
                # Return enhanced response with structured citations
                return {
                    'response': result.final_output,
                    'tool_calls': tool_calls,
                    'tools_used': [tc['name'] for tc in tool_calls],
                    'citations': unique_citations,
                    'highlights': highlights,
                    'confidence': confidence,
                    'session_id': self.session_id
                }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            error_response = self._create_error_response(str(e), user_input)
            return {
                'response': error_response,
                'tool_calls': [],
                'tools_used': [],
                'citations': [],
                'highlights': [],
                'confidence': 0.0,
                'error': str(e),
                'session_id': self.session_id
            }
    
    def _extract_citations_from_tool_result(self, tool_result: Any) -> List[Dict]:
        """Extract citations from MCP tool result (lightweight approach)."""
        citations = []
        
        try:
            # Handle different result formats
            if isinstance(tool_result, dict):
                result_data = tool_result
            elif hasattr(tool_result, '__dict__'):
                result_data = tool_result.__dict__
            else:
                return citations
            
            # The MCP tool returns citations in the 'citations' field
            if 'citations' in result_data and isinstance(result_data['citations'], list):
                for cite in result_data['citations']:
                    if isinstance(cite, dict):
                        # Convert to standardized format if needed
                        citation = {
                            'id': f"agent97_{uuid.uuid4().hex[:8]}",
                            'title': cite.get('title', cite.get('source', 'Medical Source')),
                            'source': cite.get('source', cite.get('organization', 'Unknown')),
                            'source_type': cite.get('type', 'website'),
                            'url': cite.get('url', ''),
                            'domain': self._extract_domain(cite.get('url', '')),
                            'is_trusted': cite.get('is_trusted', False),
                            'access_date': datetime.now().isoformat(),
                            'snippet': cite.get('snippet', cite.get('excerpt', '')),
                            'relevance_score': cite.get('relevance_score', 0.8)
                        }
                        citations.append(citation)
        except Exception as e:
            logger.warning(f"Error extracting citations from tool result: {e}")
        
        return citations
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            if url:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                return domain.replace('www.', '') if domain.startswith('www.') else domain
        except:
            pass
        return ''
    
    def _create_error_response(self, error_message: str, query: str) -> str:
        """Create a fallback response for errors."""
        return f"""I apologize, but I'm experiencing technical difficulties accessing the medical information database.

For your query: "{query[:100]}..."

Please try:
1. Consulting trusted medical sources directly:
   - Mayo Clinic: https://www.mayoclinic.org/
   - CDC: https://www.cdc.gov/
   - NIH: https://www.nih.gov/
   - WHO: https://www.who.int/

2. Speaking with your healthcare provider for personalized medical advice

3. Trying your query again in a few minutes

If this is a medical emergency, please call 911 immediately.

Technical details: {error_message}"""


async def create_agent_97(mcp_server_command: list = None) -> Agent97:
    """Factory function to create and initialize Agent 97."""
    
    # Create agent instance with MCP server command
    agent = Agent97(mcp_server_command)
    
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
    
    agent = await create_agent_97()
    
    # Test queries
    test_queries = [
        "What are the symptoms of diabetes?",
        "What medical sources do you use?",
        # "Check your system health status"  # Would trigger health check tool
    ]
    
    for test_query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {test_query}")
        print("-" * 60)
        
        result = await agent.query(test_query)
        
        # Handle enhanced response format with citations
        if isinstance(result, dict):
            print(f"🔧 Tools Used: {', '.join(result['tools_used']) if result['tools_used'] else 'None'}")
            print(f"📊 Tool Calls: {len(result['tool_calls'])} tools called")
            print(f"📚 Citations: {len(result.get('citations', []))} ({sum(1 for c in result.get('citations', []) if c.get('is_trusted', False))} trusted)")
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
                    print(f"     Citations: {len(highlight.get('citations', []))}")
                    print()
            
            if result['tool_calls']:
                print("\n🔧 Detailed Tool Calls:")
                for i, tc in enumerate(result['tool_calls'], 1):
                    print(f"  {i}. {tc['name']}")
                    if tc.get('arguments'):
                        # Parse and display arguments nicely
                        try:
                            import json
                            args = json.loads(tc['arguments']) if isinstance(tc['arguments'], str) else tc['arguments']
                            for key, value in args.items():
                                if isinstance(value, str) and len(value) > 100:
                                    value = value[:100] + "..."
                                print(f"     - {key}: {value}")
                        except:
                            print(f"     Arguments: {tc['arguments'][:200]}...")
        else:
            # Backward compatibility for string responses
            print(result)


if __name__ == "__main__":
    asyncio.run(test_agent())