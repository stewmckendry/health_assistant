#!/usr/bin/env python3
"""
Agent 97 MCP Server

Wraps the health assistant (PatientAssistant) functionality to provide
medical education information from 97 trusted sources via MCP tools.
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

# Add project root to path
# When running as module, __file__ is the actual file path
# We need to go up from mcp/server.py to get to project root
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the health assistant components
from src.assistants.patient import PatientAssistant
from src.config.settings import settings

# Load trusted domains from config
import yaml
# Find domains.yaml relative to this file
# From server.py -> mcp -> agent_97 -> agents -> src -> (root), then config/domains.yaml is at src/config
domains_config_path = Path(__file__).resolve().parent.parent.parent.parent / "config" / "domains.yaml"
# If that doesn't exist, try the alternative path
if not domains_config_path.exists():
    domains_config_path = Path(__file__).resolve().parent.parent.parent.parent / "src" / "config" / "domains.yaml"
with open(domains_config_path, 'r') as f:
    domains_data = yaml.safe_load(f)
    TRUSTED_DOMAINS = domains_data.get('trusted_domains', [])

# Create logs directory
LOG_DIR = Path("logs/agent_97")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Generate session ID
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
SESSION_LOG_FILE = LOG_DIR / f"mcp_session_{SESSION_ID}.log"

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
mcp = FastMCP("agent-97-server")

# Create a singleton patient assistant instance
# We'll reuse this for all queries to maintain efficiency
patient_assistant = None

def get_patient_assistant() -> PatientAssistant:
    """Get or create the patient assistant instance."""
    global patient_assistant
    if patient_assistant is None:
        logger.info("Initializing PatientAssistant for Agent 97")
        patient_assistant = PatientAssistant(
            guardrail_mode="hybrid",  # Use hybrid guardrails for best safety
            session_settings={
                'enable_input_guardrails': True,
                'enable_output_guardrails': True,
                'guardrail_mode': 'hybrid'
            }
        )
        logger.info("PatientAssistant initialized successfully")
    return patient_assistant


@mcp.tool(
    name="agent_97_query",
    description="Process medical education queries using 97 trusted medical sources with built-in safety guardrails"
)
async def agent_97_query_handler(
    query: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    message_history: Optional[List[Dict[str, str]]] = None,
    guardrail_mode: str = "hybrid"
) -> Dict[str, Any]:
    """
    Process a medical education query with comprehensive safety guardrails.
    
    Args:
        query: The medical question to answer
        session_id: Optional session identifier for tracking
        user_id: Optional user identifier
        message_history: Optional conversation history for context
        guardrail_mode: "llm", "regex", or "hybrid" (default: "hybrid")
    
    Returns:
        Educational response with citations and metadata
    """
    start_time = datetime.now()
    request_id = str(uuid.uuid4())[:8]
    
    logger.info(f"[{request_id}] Processing query: {query[:100]}...")
    logger.debug(f"[{request_id}] Session: {session_id}, User: {user_id}, History items: {len(message_history) if message_history else 0}")
    
    try:
        # Check for API key first
        import os
        if not os.getenv("ANTHROPIC_API_KEY"):
            logger.warning(f"[{request_id}] ANTHROPIC_API_KEY not set - returning mock response")
            return {
                "success": False,
                "request_id": request_id,
                "error": "ANTHROPIC_API_KEY not configured",
                "content": (
                    "The medical education assistant requires an Anthropic API key to function. "
                    "Please set the ANTHROPIC_API_KEY environment variable."
                ),
                "session_id": session_id or SESSION_ID,
                "processing_time": 0.0
            }
        
        # Get the patient assistant
        assistant = get_patient_assistant()
        
        # Process the query through the health assistant
        response = assistant.query(
            query=query,
            session_id=session_id or SESSION_ID,
            user_id=user_id,
            message_history=message_history
        )
        
        # Log successful processing
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"[{request_id}] Query processed successfully in {processing_time:.2f}s")
        logger.info(f"[{request_id}] Citations: {len(response.get('citations', []))}, Guardrails applied: {response.get('guardrails_applied', False)}")
        
        # Format response for MCP
        return {
            "success": True,
            "request_id": request_id,
            "content": response.get("content", ""),
            "citations": response.get("citations", []),
            "guardrails_applied": response.get("guardrails_applied", False),
            "emergency_detected": response.get("emergency_detected", False),
            "mental_health_crisis": response.get("mental_health_crisis", False),
            "model": response.get("model", ""),
            "usage": response.get("usage", {}),
            "session_id": session_id or SESSION_ID,
            "trace_id": response.get("trace_id"),
            "processing_time": processing_time
        }
        
    except Exception as e:
        logger.error(f"[{request_id}] Error processing query: {e}", exc_info=True)
        
        return {
            "success": False,
            "request_id": request_id,
            "error": str(e),
            "content": (
                "I apologize, but I'm unable to process your medical question at the moment. "
                "Please try again or consult with a healthcare provider directly. "
                "If this is a medical emergency, please call 911 immediately."
            ),
            "session_id": session_id or SESSION_ID,
            "processing_time": (datetime.now() - start_time).total_seconds()
        }


@mcp.tool(
    name="agent_97_get_trusted_domains",
    description="Get the list of 97 trusted medical domains used for information retrieval"
)
async def agent_97_get_trusted_domains_handler(
    include_categories: bool = False
) -> Dict[str, Any]:
    """
    Return the list of 97 trusted medical domains.
    
    Args:
        include_categories: Whether to include domain categorization
    
    Returns:
        List of trusted domains with optional categorization
    """
    logger.info("Retrieving trusted domains list")
    
    result = {
        "success": True,
        "total_domains": len(TRUSTED_DOMAINS),
        "domains": TRUSTED_DOMAINS
    }
    
    if include_categories and 'categories' in domains_data:
        result["categories"] = domains_data['categories']
        logger.info(f"Returning {len(TRUSTED_DOMAINS)} domains with {len(domains_data['categories'])} categories")
    else:
        logger.info(f"Returning {len(TRUSTED_DOMAINS)} domains without categories")
    
    return result


@mcp.tool(
    name="agent_97_health_check",
    description="Check the health status of Agent 97 MCP server and its dependencies"
)
async def agent_97_health_check_handler() -> Dict[str, Any]:
    """
    Perform a health check on the Agent 97 server.
    
    Returns:
        Health status of server components
    """
    logger.info("Performing health check")
    
    health_status = {
        "success": True,
        "server": "healthy",
        "timestamp": datetime.now().isoformat(),
        "session_id": SESSION_ID,
        "components": {}
    }
    
    # Check PatientAssistant
    try:
        assistant = get_patient_assistant()
        health_status["components"]["patient_assistant"] = "healthy"
    except Exception as e:
        health_status["components"]["patient_assistant"] = f"unhealthy: {str(e)}"
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


@mcp.tool(
    name="agent_97_get_disclaimers",
    description="Get the medical disclaimers used by Agent 97"
)
async def agent_97_get_disclaimers_handler() -> Dict[str, Any]:
    """
    Return the medical disclaimers used in responses.
    
    Returns:
        Medical disclaimers and emergency resources
    """
    logger.info("Retrieving disclaimers")
    
    return {
        "success": True,
        "disclaimers": {
            "general": settings.disclaimer_patient,
            "emergency_redirect": settings.emergency_redirect,
            "mental_health_resources": settings.mental_health_resources
        },
        "purpose": "These disclaimers ensure safe medical education without providing diagnosis or treatment"
    }


@mcp.tool(
    name="agent_97_query_stream",
    description="Stream medical education responses for real-time display"
)
async def agent_97_query_stream_handler(
    query: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    message_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Stream a medical education query response.
    
    Note: This returns a structured response about streaming capability.
    Actual streaming would require WebSocket or SSE transport.
    
    Args:
        query: The medical question to answer
        session_id: Optional session identifier
        user_id: Optional user identifier
        message_history: Optional conversation history
    
    Returns:
        Information about streaming capability
    """
    logger.info(f"Stream query requested: {query[:100]}...")
    
    # For MCP STDIO transport, we can't truly stream
    # Instead, we'll process normally and indicate streaming capability
    response = await agent_97_query_handler(
        query=query,
        session_id=session_id,
        user_id=user_id,
        message_history=message_history
    )
    
    response["streaming_note"] = (
        "True streaming requires WebSocket or SSE transport. "
        "This response was processed in full. "
        "For streaming UI, implement client-side progressive rendering."
    )
    
    return response


# Server startup logging
def startup_message():
    """Log startup information."""
    logger.info("="*60)
    logger.info("Agent 97 MCP Server Starting")
    logger.info(f"Session ID: {SESSION_ID}")
    logger.info(f"Log file: {SESSION_LOG_FILE}")
    logger.info(f"Trusted domains: {len(TRUSTED_DOMAINS)}")
    logger.info(f"Server name: agent-97-server")
    logger.info("Available tools:")
    logger.info("  - agent_97_query: Process medical queries")
    logger.info("  - agent_97_query_stream: Stream responses")
    logger.info("  - agent_97_get_trusted_domains: List domains")
    logger.info("  - agent_97_health_check: Check server health")
    logger.info("  - agent_97_get_disclaimers: Get disclaimers")
    logger.info("="*60)


if __name__ == "__main__":
    startup_message()
    
    # Run the MCP server
    try:
        asyncio.run(mcp.run())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        logger.info(f"Server stopped. Session log: {SESSION_LOG_FILE}")