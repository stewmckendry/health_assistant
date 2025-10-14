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

    def __init__(self, session_id: Optional[str] = None, enable_langfuse: bool = True, reasoning_effort: str = "low"):
        """Initialize orchestrator with session ID and reasoning effort."""
        # Call parent constructor first with reasoning_effort
        super().__init__(enable_langfuse=enable_langfuse, reasoning_effort=reasoning_effort)
        # Override session_id if provided
        if session_id:
            self.session_id = session_id
        # Setup logger
        self.session_logger = logger
    
    async def initialize(self):
        """Initialize the orchestrator with HTTP-aware sub-agents"""
        self.session_logger.info("Initializing Clinical Intelligence Orchestrator with HTTP support")

        try:
            # Initialize Dr. OPA wrapper with HTTP support - disable Langfuse to avoid conflicts
            self.dr_opa_wrapper = DrOpaAgent(session_id=self.session_id, enable_langfuse=False, reasoning_effort=self.reasoning_effort)
            await self.dr_opa_wrapper.initialize_mcp_tools()
            self.session_logger.info("Dr. OPA wrapper initialized with HTTP MCP (Langfuse disabled for sub-agent)")

            # Initialize Dr. OFF wrapper with HTTP support - disable Langfuse to avoid conflicts
            self.dr_off_wrapper = DrOffAgent(session_id=self.session_id, enable_langfuse=False, reasoning_effort=self.reasoning_effort)
            await self.dr_off_wrapper.initialize_mcp_tools()
            self.session_logger.info("Dr. OFF wrapper initialized with HTTP MCP (Langfuse disabled for sub-agent)")

            # Initialize Agent 97 wrapper - disable Langfuse to avoid conflicts
            from src.ai_agents.agent_97.openai_agent import Agent97Agent
            self.agent_97_wrapper = Agent97Agent(enable_langfuse=False, reasoning_effort=self.reasoning_effort)
            await self.agent_97_wrapper.initialize_mcp_tools()
            self.session_logger.info("Agent 97 wrapper initialized (Langfuse disabled for sub-agent)")

            self.session_logger.info("All agent wrappers initialized successfully with HTTP MCP support")

        except Exception as e:
            self.session_logger.error(f"Error initializing agent wrappers: {e}")
            raise

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