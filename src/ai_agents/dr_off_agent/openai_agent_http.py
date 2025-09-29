"""
Dr. OFF OpenAI Agent with HTTP MCP support for Railway deployment.
Extends the base agent to support HTTP-based MCP servers.
"""

import os
import logging
from typing import Optional
from pathlib import Path

# Import MCP server classes from openai-agents package
try:
    # Try the normal import first
    from agents.mcp.server import MCPServerStreamableHttp, MCPServerStreamableHttpParams, MCPServerStdio, MCPServerStdioParams
except ImportError as e:
    # If it fails, it's likely due to path conflict with src/agents
    # Remove src from path temporarily
    import sys
    original_path = sys.path.copy()
    sys.path = [p for p in sys.path if not p.endswith('/src') and not p.endswith('/app/src')]
    try:
        from agents.mcp.server import MCPServerStreamableHttp, MCPServerStreamableHttpParams, MCPServerStdio, MCPServerStdioParams
    finally:
        sys.path = original_path

# Import the base agent
from src.ai_agents.dr_off_agent.openai_agent import DrOffAgent

logger = logging.getLogger(__name__)

class DrOffAgentHTTP(DrOffAgent):
    """Dr. OFF Agent that can use either stdio or HTTP MCP servers"""
    
    def __init__(self, session_id: Optional[str] = None, enable_langfuse: bool = True):
        """Initialize agent with appropriate MCP server based on environment"""
        # Check if we're on Railway or should use HTTP mode
        is_railway = os.environ.get("RAILWAY_ENVIRONMENT")
        use_http = os.environ.get("USE_HTTP_MCP")
        
        logger.info(f"DrOffAgentHTTP init - RAILWAY_ENVIRONMENT: {is_railway}, USE_HTTP_MCP: {use_http}")
        
        if is_railway or use_http:
            logger.info("Using HTTP MCP mode for Dr. OFF Agent")
            # Pass "skip" to prevent parent from creating stdio server
            super().__init__(mcp_server_command="skip", enable_langfuse=enable_langfuse)
            # Now initialize the HTTP MCP server
            self._initialize_http_mcp_server()
        else:
            logger.info("Using stdio MCP mode for Dr. OFF Agent")
            # Use default stdio initialization
            super().__init__(enable_langfuse=enable_langfuse)
        
    def _initialize_http_mcp_server(self):
        """Initialize HTTP MCP server for Railway deployment"""
        logger.info("Initializing HTTP MCP server for Dr. OFF Agent")
        
        try:
            # Use HTTP mode - connect to the running HTTP MCP server
            # On Railway, the MCP servers run on the same container at different ports
            base_url = os.environ.get("MCP_DR_OFF_URL", "http://localhost:8001")
            mcp_url = f"{base_url}/mcp" if not base_url.endswith("/mcp") else base_url
            
            logger.info(f"Creating MCPServerStreamableHttp with URL: {mcp_url}")
            
            self.mcp_server = MCPServerStreamableHttp(
                params=MCPServerStreamableHttpParams(
                    url=mcp_url,
                    headers={},
                    timeout=60.0,
                    sse_read_timeout=120.0,
                    terminate_on_close=True
                ),
                name="dr-off-server-http",
                client_session_timeout_seconds=60.0
            )
            
            logger.info(f"Successfully created Dr. OFF HTTP MCP server connection to: {mcp_url}")
            logger.info(f"MCP server object type: {type(self.mcp_server)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize HTTP MCP server for Dr. OFF: {e}")
            logger.exception("Full traceback:")
            raise

async def create_dr_off_agent(session_id: Optional[str] = None) -> DrOffAgentHTTP:
    """Factory function to create a Dr. OFF agent with HTTP support"""
    return DrOffAgentHTTP(session_id)