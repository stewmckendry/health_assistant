"""
HTTP version of the Dr. OFF MCP server for deployment on Railway.
Runs as a Streamable HTTP server instead of stdio.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the main server module
# Use relative import since we're in the same package
from .server import mcp, logger, SESSION_ID, write_session_summary

async def run_http_server():
    """Run the MCP server in HTTP mode for Railway deployment"""
    try:
        # Get port from environment variable (Railway provides PORT)
        port = int(os.environ.get("MCP_DR_OFF_PORT", "8001"))
        host = "0.0.0.0"
        
        logger.info(f"Starting Dr. OFF MCP Server in HTTP mode")
        logger.info(f"Session ID: {SESSION_ID}")
        logger.info(f"Listening on http://{host}:{port}")
        logger.info(f"{'=' * 80}")
        logger.info("Registered tools:")
        logger.info("  - coverage.answer: Main orchestrator for clinical questions")
        logger.info("  - schedule.get: OHIP Schedule lookup")
        logger.info("  - adp.get: ADP device eligibility and funding")
        logger.info("  - odb.get: ODB drug formulary lookup")
        logger.info("  - source.passages: Retrieve exact text chunks")
        
        # Run as Streamable HTTP server
        await mcp.run_streamable_http_async(host=host, port=port)
        
    except Exception as e:
        logger.error(f"HTTP server error: {e}")
        logger.exception("Full traceback:")
        raise
    finally:
        write_session_summary()

if __name__ == "__main__":
    # Run the HTTP server
    asyncio.run(run_http_server())