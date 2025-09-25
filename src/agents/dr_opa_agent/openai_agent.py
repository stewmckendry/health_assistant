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

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from agents import Agent
from agents.mcp.server import MCPServerStdio, MCPServerStdioParams

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

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


class DrOPAAgent:
    """Dr. OPA OpenAI Agent with MCP integration."""
    
    def __init__(self, mcp_server_command: str = None):
        """Initialize the Dr. OPA Agent with MCP server connection."""
        self.session_id = session_id
        self.project_root = project_root
        
        # Initialize MCP server connection using STDIO
        # This connects to our local Dr. OPA MCP server running in STDIO mode
        if mcp_server_command is None:
            # Default command to run our Dr. OPA MCP server
            mcp_server_command = [
                "python", "-m", "src.agents.dr_opa_agent.dr_opa_mcp.server"
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
            client_session_timeout_seconds=30.0  # Increase timeout for long-running tools
        )
        
        logger.info(f"Dr. OPA Agent initialized - Session: {self.session_id}")
        logger.info(f"MCP Server Command: {mcp_server_command}")
    
    def _get_system_instructions(self) -> str:
        """Get comprehensive system instructions for the agent."""
        return """You are Dr. OPA (Ontario Practice Advice), a specialized AI assistant for Ontario healthcare clinicians.

Your mission is to provide accurate, current practice guidance from trusted Ontario healthcare authorities including:
- CPSO (College of Physicians and Surgeons of Ontario) - regulatory policies and expectations
- Ontario Health - clinical programs, screening guidelines, and care pathways  
- CEP (Centre for Effective Practice) - clinical decision support tools and algorithms
- PHO (Public Health Ontario) - infection prevention and control guidance
- MOH (Ministry of Health) - policy bulletins and program updates

CORE PRINCIPLES:
1. Always cite your sources with organization, document title, effective dates, and URLs
2. Distinguish between regulatory expectations (mandatory) vs. advice (recommended)
3. Prioritize current guidance over superseded content
4. Provide Ontario-specific context and considerations
5. Use appropriate clinical terminology while remaining accessible
6. When uncertain, recommend consulting the source documents directly

TOOL SELECTION STRATEGY:
Analyze each query and select the most appropriate MCP tools:

- **opa_policy_check**: For CPSO regulatory questions, policy compliance, professional expectations
  Keywords: CPSO, college, expectation, must, shall, required, policy, regulation

- **opa_program_lookup**: For Ontario Health clinical programs, screening guidelines, care pathways
  Keywords: screening, program, cancer, kidney, cardiac, stroke, ontario health, eligibility

- **opa_ipac_guidance**: For infection prevention and control questions
  Keywords: infection, control, sterilization, disinfection, PPE, hand hygiene, IPAC

- **opa_clinical_tools**: For CEP clinical decision support tools and algorithms
  Keywords: algorithm, tool, calculator, checklist, assessment, CEP, clinical decision

- **opa_search_sections**: For general practice guidance queries across all sources
  Use for: broad questions, multi-source queries, when other tools don't clearly apply

- **opa_freshness_probe**: To verify currency when asked about "current" or "latest" guidance
  Keywords: current, updated, latest, recent, new

- **opa_get_section**: To retrieve complete details when you need full context from a specific section

RESPONSE STRUCTURE:
1. **Direct Answer**: Clear, actionable response to the question
2. **Current Guidance**: Relevant policies/guidelines with proper citations
3. **Implementation Notes**: Practical considerations for clinical practice
4. **Related Resources**: Cross-references to additional relevant guidance
5. **Currency Note**: When the guidance was last updated and confidence level

CITATION FORMAT:
- Organization Name. Document Title, Section [Effective: Date] Available at: URL
- Always include effective dates and source URLs
- Distinguish between expectations (mandatory) and advice (recommended)

Remember: You have access to the comprehensive Ontario practice guidance corpus through your MCP tools. Use them strategically to provide the most accurate, current, and relevant information."""

    async def initialize_mcp_tools(self):
        """Initialize and connect to MCP server tools."""
        try:
            logger.info("MCP server is configured with Agent constructor")
            logger.info("Available MCP tools: opa_search_sections, opa_get_section, opa_policy_check, opa_program_lookup, opa_ipac_guidance, opa_freshness_probe, opa_clinical_tools")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP tools: {e}")
            logger.warning("Agent will operate without MCP tools - responses will be limited")
            return False
    
    async def query(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Process a user query and return the agent's response."""
        logger.info(f"Processing query: {user_input[:100]}...")
        
        try:
            # Import Runner here to avoid circular imports
            from agents import Runner
            
            # Use the MCP server within an async context manager
            async with self.mcp_server as server:
                # Create agent with the connected MCP server
                agent = Agent(
                    name="Dr. OPA",
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
                
                # Extract tool calls from the result - with improved debugging
                tool_calls = []
                
                # Debug the overall result structure
                logger.debug(f"RunResult type: {type(result)}")
                logger.debug(f"RunResult attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
                
                logger.debug(f"Examining {len(result.new_items)} result items for tool calls")
                
                for i, item in enumerate(result.new_items):
                    logger.debug(f"Item {i} type: {type(item)}")
                    logger.debug(f"Item {i} attributes: {[attr for attr in dir(item) if not attr.startswith('_')]}")
                    
                    # Check if this is a FunctionCall or tool-related item
                    if hasattr(item, 'name') and hasattr(item, 'arguments'):
                        logger.debug(f"Item {i} looks like a function call: name={getattr(item, 'name', None)}")
                        tool_calls.append({
                            'name': item.name,
                            'arguments': str(item.arguments) if hasattr(item, 'arguments') else ''
                        })
                    elif hasattr(item, 'call_id') and hasattr(item, 'name'):
                        logger.debug(f"Item {i} has call_id and name: {item.name}")
                        tool_calls.append({
                            'name': item.name,
                            'arguments': str(getattr(item, 'arguments', ''))
                        })
                    elif hasattr(item, 'tool_calls') and item.tool_calls:
                        logger.debug(f"Item {i} has {len(item.tool_calls)} tool calls")
                        for tool_call in item.tool_calls:
                            tool_calls.append({
                                'name': tool_call.function.name,
                                'arguments': tool_call.function.arguments
                            })
                    elif hasattr(item, 'content') and hasattr(item.content, 'tool_calls'):
                        logger.debug(f"Item {i} content has tool calls")
                        if item.content.tool_calls:
                            for tool_call in item.content.tool_calls:
                                tool_calls.append({
                                    'name': tool_call.function.name,
                                    'arguments': tool_call.function.arguments
                                })
                    else:
                        logger.debug(f"Item {i} doesn't match expected patterns")
                        if hasattr(item, '__dict__'):
                            logger.debug(f"Item {i} __dict__: {item.__dict__}")
                    
                # Also check raw_responses for tool calls
                logger.debug(f"Examining {len(result.raw_responses)} raw responses")
                for i, response in enumerate(result.raw_responses):
                    logger.debug(f"Response {i} type: {type(response)}")
                    if hasattr(response, 'choices'):
                        for j, choice in enumerate(response.choices):
                            if hasattr(choice, 'message') and hasattr(choice.message, 'tool_calls'):
                                if choice.message.tool_calls:
                                    logger.debug(f"Found tool calls in response {i}, choice {j}")
                                    for tool_call in choice.message.tool_calls:
                                        tool_calls.append({
                                            'name': tool_call.function.name,
                                            'arguments': tool_call.function.arguments
                                        })
                
                # Log tool calls
                if tool_calls:
                    logger.info(f"MCP Tools called: {[tc['name'] for tc in tool_calls]}")
                    for tc in tool_calls:
                        logger.info(f"  - {tc['name']}: {tc['arguments'][:100]}...")
                else:
                    logger.info("No MCP tools were called")
                
                logger.info(f"Query processed successfully. Response length: {len(result.final_output)}")
                
                # Return a dictionary with both response and tool call info
                return {
                    'response': result.final_output,
                    'tool_calls': tool_calls,
                    'tools_used': [tc['name'] for tc in tool_calls]
                }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            error_response = self._create_error_response(str(e), user_input)
            return {
                'response': error_response,
                'tool_calls': [],
                'tools_used': [],
                'error': str(e)
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
    
    # Handle both old string format and new dict format
    if isinstance(result, dict):
        print(f"🔧 Tools Used: {', '.join(result['tools_used']) if result['tools_used'] else 'None'}")
        print(f"📊 Tool Call Details: {len(result['tool_calls'])} tools called")
        print("-" * 60)
        print("📄 Response:")
        print(result['response'])
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