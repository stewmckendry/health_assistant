"""
HTTP version of the Dr. OPA MCP server for deployment on Railway.
Runs as a Streamable HTTP server instead of stdio.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the main server module from dr_opa_mcp directory
from ..dr_opa_mcp.server import mcp, logger
from datetime import datetime
import uuid

# Create session ID for this run
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]

def write_session_summary():
    """Write session summary at shutdown"""
    logger.info(f"{'=' * 80}")
    logger.info("Dr. OPA MCP Server Session ended")
    logger.info(f"Session ID: {SESSION_ID}")

async def run_http_server():
    """Run the MCP server in HTTP mode for Railway deployment"""
    try:
        # Get port from environment variable (Railway provides PORT)
        port = int(os.environ.get("MCP_DR_OPA_PORT", "8002"))
        host = "0.0.0.0"
        
        logger.info(f"Starting Dr. OPA MCP Server in HTTP mode")
        logger.info(f"Session ID: {SESSION_ID}")
        logger.info(f"Listening on http://{host}:{port}")
        logger.info(f"{'=' * 80}")
        logger.info("Registered tools:")
        logger.info("  - opa_search_sections: Hybrid search across OPA knowledge corpus")
        logger.info("  - opa_get_section: Retrieve complete section details by ID")
        logger.info("  - opa_policy_check: CPSO-specific policy and advice retrieval")
        logger.info("  - opa_program_lookup: Ontario Health clinical programs information")
        logger.info("  - opa_ipac_guidance: PHO infection prevention and control guidance")
        logger.info("  - opa_freshness_probe: Check for guidance updates on a topic")
        logger.info("  - opa_clinical_tools: CEP clinical decision support tools lookup")
        logger.info("  - opa_quality_standards: Ontario Health quality standards search")
        logger.info("  - opa_choosing_wisely: Choosing Wisely recommendations for avoiding unnecessary care")
        
        # Run as HTTP server (using new method)
        await mcp.run_http_async(host=host, port=port)
        
    except Exception as e:
        logger.error(f"HTTP server error: {e}")
        logger.exception("Full traceback:")
        raise
    finally:
        write_session_summary()

if __name__ == "__main__":
    # Run the HTTP server
    asyncio.run(run_http_server())