"""
Clinical Intelligence Orchestrator with HTTP MCP support for Railway deployment.
Extends the base orchestrator to support HTTP-based MCP servers.
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
    from agents.mcp.server import MCPServerStreamableHttp, MCPServerStreamableHttpParams
finally:
    sys.path = original_path

# Import base components
from src.agents.diagnostic_orchestrator.orchestrator_agent import DiagnosticOrchestrator

# Use HTTP versions of the sub-agents on Railway
if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("USE_HTTP_MCP"):
    from src.agents.dr_opa_agent.openai_agent_http import DrOpaAgentHTTP as DrOpaAgent
    from src.agents.dr_off_agent.openai_agent_http import DrOffAgentHTTP as DrOffAgent
else:
    from src.agents.dr_opa_agent.openai_agent import DrOPAAgent as DrOpaAgent
    from src.agents.dr_off_agent.openai_agent import DrOffAgent

logger = logging.getLogger(__name__)

class ClinicalIntelligenceOrchestratorHTTP(DiagnosticOrchestrator):
    """Orchestrator that can use either stdio or HTTP MCP servers"""
    
    async def initialize(self):
        """Initialize the orchestrator with HTTP-aware sub-agents"""
        self.session_logger.info("Initializing Clinical Intelligence Orchestrator with HTTP support")
        
        # Initialize sub-agents with HTTP support
        self.dr_opa_wrapper = DrOpaAgent(session_id=self.session_id)
        self.dr_off_wrapper = DrOffAgent(session_id=self.session_id)
        
        # Agent 97 doesn't need MCP servers directly
        # It uses the patient assistant which has its own web search
        
        self.session_logger.info("Sub-agents initialized with HTTP MCP support")
    
    def _create_agent_97_mcp(self):
        """Create MCP server for Agent 97 based on environment"""
        if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("USE_HTTP_MCP"):
            # Agent 97 doesn't have its own MCP server, it uses web search directly
            # Return None for HTTP mode
            return None
        else:
            # Use stdio mode for local development
            from agents.mcp.server import MCPServerStdio, MCPServerStdioParams
            
            agent_97_mcp = MCPServerStdio(
                params=MCPServerStdioParams(
                    command="python",
                    args=["-m", "src.assistants.patient"],
                    env=dict(os.environ),
                    cwd=str(self.project_root),
                    encoding="utf-8"
                ),
                name="agent-97-server",
                client_session_timeout_seconds=60.0
            )
            return agent_97_mcp

async def create_orchestrator_http(session_id: Optional[str] = None) -> ClinicalIntelligenceOrchestratorHTTP:
    """Factory function to create an orchestrator with HTTP support"""
    orchestrator = ClinicalIntelligenceOrchestratorHTTP(session_id)
    await orchestrator.initialize()
    return orchestrator