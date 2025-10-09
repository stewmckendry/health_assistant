"""
Clinical Intelligence Orchestrator with HTTP MCP support for Railway deployment.
Extends the base orchestrator to support HTTP-based MCP servers.
"""

import os
import logging
from typing import Optional
from pathlib import Path

# Import MCP server classes from openai-agents package
try:
    # Try the normal import first
    from agents.mcp.server import MCPServerStreamableHttp, MCPServerStreamableHttpParams
except ImportError as e:
    # If it fails, it's likely due to path conflict with src/agents
    # Remove src from path temporarily
    import sys
    original_path = sys.path.copy()
    sys.path = [p for p in sys.path if not p.endswith('/src') and not p.endswith('/app/src')]
    try:
        from agents.mcp.server import MCPServerStreamableHttp, MCPServerStreamableHttpParams
    finally:
        sys.path = original_path

# Import base components
from src.ai_agents.diagnostic_orchestrator.orchestrator_agent import DiagnosticOrchestrator

# Use HTTP versions of the sub-agents on Railway
if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("USE_HTTP_MCP"):
    from src.ai_agents.dr_opa_agent.openai_agent_http import DrOpaAgentHTTP as DrOpaAgent
    from src.ai_agents.dr_off_agent.openai_agent_http import DrOffAgentHTTP as DrOffAgent
else:
    from src.ai_agents.dr_opa_agent.openai_agent import DrOPAAgent as DrOpaAgent
    from src.ai_agents.dr_off_agent.openai_agent import DrOffAgent

logger = logging.getLogger(__name__)

class ClinicalIntelligenceOrchestratorHTTP(DiagnosticOrchestrator):
    """Orchestrator that can use either stdio or HTTP MCP servers"""
    
    def __init__(self, session_id: Optional[str] = None, enable_langfuse: bool = True):
        """Initialize orchestrator with session ID."""
        # Call parent constructor first
        super().__init__(enable_langfuse=enable_langfuse)
        # Override session_id if provided
        if session_id:
            self.session_id = session_id
        # Setup logger
        self.session_logger = logger
    
    async def initialize(self):
        """Initialize the orchestrator with HTTP-aware sub-agents"""
        self.session_logger.info("Initializing Clinical Intelligence Orchestrator with HTTP support")

        # Initialize sub-agents with HTTP support
        self.dr_opa_wrapper = DrOpaAgent(session_id=self.session_id)
        self.dr_off_wrapper = DrOffAgent(session_id=self.session_id)

        # Agent 97 doesn't need MCP servers directly
        # It uses the patient assistant which has its own web search

        self.session_logger.info("Sub-agents initialized with HTTP MCP support")

    async def query(self, clinical_query: str, session_id: str = None, user_id: str = None):
        """Wrapper for orchestrate method to match test interface"""
        return await self.orchestrate(clinical_query, session_id=session_id, user_id=user_id)
    
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
                client_session_timeout_seconds=90.0  # Extended to 90s for complex queries
            )
            return agent_97_mcp

async def create_orchestrator_http(session_id: Optional[str] = None) -> ClinicalIntelligenceOrchestratorHTTP:
    """Factory function to create an orchestrator with HTTP support"""
    orchestrator = ClinicalIntelligenceOrchestratorHTTP(session_id=session_id)
    await orchestrator.initialize()
    return orchestrator