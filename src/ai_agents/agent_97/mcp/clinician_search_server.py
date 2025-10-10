#!/usr/bin/env python3
"""
Agent 97 Clinician Search MCP Server

Provides evidence-based clinical search using Claude's web_search and web_fetch tools
with 97 trusted medical sources. Designed for healthcare clinicians, NOT patients.

Key differences from patient assistant:
- No safety guardrails (clinicians make clinical judgment)
- Clinician-focused system instructions
- Same 97 trusted domains from domains.yaml
- Uses Claude API with web tools (no domain limit like OpenAI)
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid

from fastmcp import FastMCP
from anthropic import Anthropic

# Add project root to path
# __file__ = .../src/ai_agents/agent_97/mcp/clinician_search_server.py
# Need to go up 5 levels: mcp -> agent_97 -> ai_agents -> src -> health_assistant
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import configuration
from src.config.settings import settings

# Load trusted domains from config
import yaml
domains_config_path = project_root / "src" / "config" / "domains.yaml"
with open(domains_config_path, 'r') as f:
    domains_data = yaml.safe_load(f)
    TRUSTED_DOMAINS = domains_data.get('trusted_domains', [])

# Create logs directory
LOG_DIR = Path("logs/agent_97")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Generate session ID
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
SESSION_LOG_FILE = LOG_DIR / f"clinician_search_session_{SESSION_ID}.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(SESSION_LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("agent-97-clinician-search")

# Initialize Anthropic client
anthropic_client = None

def get_anthropic_client() -> Anthropic:
    """Get or create the Anthropic client instance."""
    global anthropic_client
    if anthropic_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        anthropic_client = Anthropic(
            api_key=api_key,
            default_headers={
                "anthropic-beta": "web-search-2025-03-05,web-fetch-2025-09-10"
            }
        )
        logger.info("Anthropic client initialized successfully with web tools beta headers")
    return anthropic_client


def get_clinician_system_prompt() -> str:
    """Get system instructions for clinician-focused medical search."""
    return """You are a clinical evidence search assistant for healthcare professionals.

Your role is to help clinicians find evidence-based medical information from trusted sources to support their clinical decision-making.

IMPORTANT FRAMING:
- Your users are HEALTHCARE CLINICIANS (physicians, NPs, PAs), NOT patients
- Provide professional, evidence-based clinical guidance
- No safety guardrails or patient disclaimers needed
- Clinicians have medical training and make their own clinical judgments

SEARCH APPROACH:
When searching for clinical information:
1. Use web_search to find relevant medical sources
2. Prioritize high-quality evidence (guidelines, systematic reviews, RCTs)
3. Include practical clinical details (dosing, protocols, diagnostic criteria)
4. Cite sources clearly with URLs
5. Note evidence quality when relevant (e.g., "based on RCT", "expert consensus")

RESPONSE STYLE:
- Direct, professional clinical language
- Include specific details clinicians need (doses, protocols, criteria)
- Reference authoritative sources (medical societies, journals, guidelines)
- Note areas of controversy or evolving evidence
- NO patient safety disclaimers (users are clinicians, not patients)

TRUSTED SOURCES:
You have access to 97 trusted medical sources including:
- Medical journals (NEJM, Lancet, JAMA, BMJ)
- Clinical guidelines (NICE, AHA, ACC, ADA)
- Academic medical centers (Mayo, Hopkins, Cleveland Clinic)
- Health authorities (WHO, CDC, NIH, Health Canada)
- Canadian healthcare (Ontario Health, CPSO, Canadian medical associations)

Provide evidence-based, clinician-appropriate guidance."""


@mcp.tool(
    name="clinician_search",
    description="Search trusted medical sources for evidence-based clinical information (for healthcare professionals)"
)
async def clinician_search_handler(
    query: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    max_web_search_uses: int = 2,
    max_web_fetch_uses: int = 5
) -> Dict[str, Any]:
    """
    Search 97 trusted medical sources for clinical information.

    Args:
        query: The clinical question to research
        session_id: Optional session identifier for tracking
        user_id: Optional user identifier
        max_web_search_uses: Maximum number of web searches (default: 2)
        max_web_fetch_uses: Maximum number of sources to fetch (default: 5)

    Returns:
        Clinical guidance with citations from trusted medical sources
    """
    start_time = datetime.now()
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"[{request_id}] Clinician search query: {query[:100]}...")
    logger.debug(f"[{request_id}] Session: {session_id}, User: {user_id}")

    try:
        # Check for API key
        if not os.getenv("ANTHROPIC_API_KEY"):
            logger.warning(f"[{request_id}] ANTHROPIC_API_KEY not set")
            return {
                "success": False,
                "request_id": request_id,
                "error": "ANTHROPIC_API_KEY not configured",
                "content": "The clinician search service requires an Anthropic API key. Please set the ANTHROPIC_API_KEY environment variable.",
                "session_id": session_id or SESSION_ID,
                "processing_time": 0.0
            }

        # Get Anthropic client
        client = get_anthropic_client()

        # Build tools configuration with ALL 97 trusted domains
        # Claude web_search has NO domain limit (unlike OpenAI WebSearchTool which has 20 max)
        tools = [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_web_search_uses,  # Default 2 (Claude uses web_search more than web_fetch)
                "allowed_domains": TRUSTED_DOMAINS  # All 97 domains
            },
            {
                "type": "web_fetch_20250910",
                "name": "web_fetch",
                "allowed_domains": TRUSTED_DOMAINS,  # All 97 domains
                "max_uses": max_web_fetch_uses,  # Default 5
                "citations": {"enabled": True}
            }
        ]

        logger.info(f"[{request_id}] Configured tools with {len(TRUSTED_DOMAINS)} trusted domains")

        # Call Claude API with web tools
        response = client.messages.create(
            model=settings.primary_model,  # Use configured model (e.g., claude-3-5-sonnet-latest)
            max_tokens=3000,  # Higher limit for clinical detail
            temperature=0.3,  # Lower for factual clinical information
            system=get_clinician_system_prompt(),
            messages=[
                {"role": "user", "content": query}
            ],
            tools=tools
        )

        # Extract response text
        response_text = ""
        citations = []
        tool_calls = []

        for block in response.content:
            if hasattr(block, 'type'):
                if block.type == 'text':
                    response_text += block.text

                    # Extract citations if present
                    if hasattr(block, 'citations') and block.citations:
                        for citation in block.citations:
                            if hasattr(citation, 'url') and hasattr(citation, 'title'):
                                citations.append({
                                    "url": citation.url,
                                    "title": citation.title,
                                    "domain": citation.url.split('/')[2] if '/' in citation.url else ""
                                })

                # Track tool usage (for transparency)
                elif block.type == 'server_tool_use':
                    tool_calls.append({
                        "tool": block.name if hasattr(block, 'name') else "unknown",
                        "id": block.id if hasattr(block, 'id') else None
                    })

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        logger.info(f"[{request_id}] Search completed in {processing_time:.2f}s")
        logger.info(f"[{request_id}] Citations: {len(citations)}, Tool calls: {len(tool_calls)}")

        # Return clinician-focused response
        return {
            "success": True,
            "request_id": request_id,
            "content": response_text,
            "citations": citations,
            "tool_calls": tool_calls,
            "model": settings.primary_model,
            "usage": {
                "input_tokens": response.usage.input_tokens if hasattr(response, 'usage') else 0,
                "output_tokens": response.usage.output_tokens if hasattr(response, 'usage') else 0
            },
            "session_id": session_id or SESSION_ID,
            "processing_time": processing_time,
            "note": "Clinician-focused search from 97 trusted medical sources"
        }

    except Exception as e:
        logger.error(f"[{request_id}] Error processing search: {e}", exc_info=True)

        return {
            "success": False,
            "request_id": request_id,
            "error": str(e),
            "content": f"Unable to complete clinical search. Error: {str(e)}",
            "session_id": session_id or SESSION_ID,
            "processing_time": (datetime.now() - start_time).total_seconds()
        }


@mcp.tool(
    name="clinician_search_get_domains",
    description="Get the list of 97 trusted medical domains used for clinical searches"
)
async def clinician_search_get_domains_handler(
    include_categories: bool = False
) -> Dict[str, Any]:
    """
    Return the list of 97 trusted medical domains.

    Args:
        include_categories: Whether to include domain categorization

    Returns:
        List of trusted medical domains with optional categorization
    """
    logger.info("Retrieving trusted medical domains list")

    result = {
        "success": True,
        "total_domains": len(TRUSTED_DOMAINS),
        "domains": TRUSTED_DOMAINS,
        "note": "These domains are used for evidence-based clinical search"
    }

    if include_categories and 'categories' in domains_data:
        result["categories"] = domains_data['categories']
        logger.info(f"Returning {len(TRUSTED_DOMAINS)} domains with {len(domains_data['categories'])} categories")
    else:
        logger.info(f"Returning {len(TRUSTED_DOMAINS)} domains without categories")

    return result


@mcp.tool(
    name="clinician_search_health_check",
    description="Check the health status of the clinician search service"
)
async def clinician_search_health_check_handler() -> Dict[str, Any]:
    """
    Perform a health check on the clinician search service.

    Returns:
        Health status of service components
    """
    logger.info("Performing health check")

    health_status = {
        "success": True,
        "server": "healthy",
        "timestamp": datetime.now().isoformat(),
        "session_id": SESSION_ID,
        "components": {}
    }

    # Check Anthropic client
    try:
        client = get_anthropic_client()
        health_status["components"]["anthropic_client"] = "healthy"
    except Exception as e:
        health_status["components"]["anthropic_client"] = f"unhealthy: {str(e)}"
        health_status["success"] = False

    # Check API key
    if os.getenv("ANTHROPIC_API_KEY"):
        health_status["components"]["anthropic_api"] = "configured"
    else:
        health_status["components"]["anthropic_api"] = "not configured"
        health_status["success"] = False

    # Check domains configuration
    health_status["components"]["trusted_domains"] = {
        "status": "healthy",
        "count": len(TRUSTED_DOMAINS)
    }

    # Check logging
    health_status["components"]["logging"] = {
        "status": "healthy",
        "log_file": str(SESSION_LOG_FILE)
    }

    logger.info(f"Health check complete: {'healthy' if health_status['success'] else 'unhealthy'}")
    return health_status


# Server startup logging
def startup_message():
    """Log startup information."""
    logger.info("="*60)
    logger.info("Agent 97 Clinician Search MCP Server Starting")
    logger.info(f"Session ID: {SESSION_ID}")
    logger.info(f"Log file: {SESSION_LOG_FILE}")
    logger.info(f"Trusted domains: {len(TRUSTED_DOMAINS)}")
    logger.info(f"Server name: agent-97-clinician-search")
    logger.info(f"Primary model: {settings.primary_model}")
    logger.info("Available tools:")
    logger.info("  - clinician_search: Search 97 trusted medical sources")
    logger.info("  - clinician_search_get_domains: List trusted domains")
    logger.info("  - clinician_search_health_check: Check server health")
    logger.info("Target users: Healthcare clinicians (NO patient guardrails)")
    logger.info("="*60)


if __name__ == "__main__":
    startup_message()

    # Run the MCP server (synchronous)
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        logger.info(f"Server stopped. Session log: {SESSION_LOG_FILE}")
