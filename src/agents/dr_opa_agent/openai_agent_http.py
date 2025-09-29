"""
Dr. OPA OpenAI Agent with HTTP MCP support for Railway deployment.
Extends the base agent to support HTTP-based MCP servers.
"""

import os
import logging
from typing import Optional
from pathlib import Path

# Import MCP server classes from openai-agents
from agents.mcp.server import MCPServerStreamableHttp, MCPServerStreamableHttpParams, MCPServerStdio, MCPServerStdioParams

# Import the base agent
from src.agents.dr_opa_agent.openai_agent import DrOPAAgent

logger = logging.getLogger(__name__)

class DrOpaAgentHTTP(DrOPAAgent):
    """Dr. OPA Agent that can use either stdio or HTTP MCP servers"""
    
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
            # On Railway, the MCP servers run on the same container at different ports
            base_url = os.environ.get("MCP_DR_OPA_URL", "http://localhost:8002")
            mcp_url = f"{base_url}/mcp" if not base_url.endswith("/mcp") else base_url
            
            self.mcp_server = MCPServerStreamableHttp(
                params=MCPServerStreamableHttpParams(
                    url=mcp_url,
                    headers={},
                    timeout=60.0,
                    sse_read_timeout=120.0,
                    terminate_on_close=True
                ),
                name="dr-opa-server-http",
                client_session_timeout_seconds=60.0
            )
            
            logger.info(f"Dr. OPA Agent using HTTP MCP server at: {mcp_url}")
        else:
            # Use stdio mode for local development
            logger.info("Initializing MCP server in stdio mode for local development")
            
            mcp_server_command = [
                "python", "-m", "src.agents.dr_opa_agent.mcp.server"
            ]
            
            self.mcp_server = MCPServerStdio(
                params=MCPServerStdioParams(
                    command=mcp_server_command[0],
                    args=mcp_server_command[1:],
                    env=dict(os.environ),
                    cwd=str(self.project_root),
                    encoding="utf-8"
                ),
                name="dr-opa-server",
                client_session_timeout_seconds=60.0
            )
            
            logger.info(f"Dr. OPA Agent using stdio MCP server")

async def create_dr_opa_agent(session_id: Optional[str] = None) -> DrOpaAgentHTTP:
    """Factory function to create a Dr. OPA agent with HTTP support"""
    return DrOpaAgentHTTP(session_id)