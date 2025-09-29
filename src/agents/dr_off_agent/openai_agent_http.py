"""
Dr. OFF OpenAI Agent with HTTP MCP support for Railway deployment.
Extends the base agent to support HTTP-based MCP servers.
"""

import os
import logging
from typing import Optional
from pathlib import Path

# Set up path before imports
import sys
project_root = Path(__file__).parent.parent.parent.parent
original_path = sys.path.copy()
project_root_str = str(project_root)
if project_root_str in sys.path:
    sys.path.remove(project_root_str)
src_dir = str(project_root / "src")
if src_dir in sys.path:
    sys.path.remove(src_dir)

try:
    from agents.mcp.server import MCPServerStreamableHttp, MCPServerStreamableHttpParams, MCPServerStdio, MCPServerStdioParams
finally:
    sys.path = original_path

# Import the base agent
from src.agents.dr_off_agent.openai_agent import DrOffAgent

logger = logging.getLogger(__name__)

class DrOffAgentHTTP(DrOffAgent):
    """Dr. OFF Agent that can use either stdio or HTTP MCP servers"""
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize agent with appropriate MCP server based on environment"""
        # Initialize everything except MCP server
        super().__init__(session_id)
        
    def _initialize_mcp_server(self):
        """Initialize MCP server based on environment"""
        # Check if we're on Railway or should use HTTP mode
        if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("USE_HTTP_MCP"):
            logger.info("Initializing MCP server in HTTP mode for Railway")
            
            # Use HTTP mode - connect to the running HTTP MCP server
            mcp_url = os.environ.get("MCP_DR_OFF_URL", "http://localhost:8001")
            
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
            
            logger.info(f"Dr. OFF Agent using HTTP MCP server at: {mcp_url}")
        else:
            # Use stdio mode for local development
            logger.info("Initializing MCP server in stdio mode for local development")
            
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
                client_session_timeout_seconds=60.0
            )
            
            logger.info(f"Dr. OFF Agent using stdio MCP server")

async def create_dr_off_agent(session_id: Optional[str] = None) -> DrOffAgentHTTP:
    """Factory function to create a Dr. OFF agent with HTTP support"""
    return DrOffAgentHTTP(session_id)