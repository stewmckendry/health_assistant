"""
FastMCP server for Dr. OFF clinical decision support tools.
Provides 5 tools for Ontario healthcare coverage queries.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import uuid
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import tool handlers
from .tools.schedule import schedule_get
from .tools.adp import adp_get
from .tools.odb import odb_get
from .models.request import StandardToolRequest

# Create logs directory
LOG_DIR = Path("logs/dr_off_agent")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Generate session ID
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
SESSION_LOG_FILE = LOG_DIR / f"session_{SESSION_ID}.log"

# Configure comprehensive logging
class SessionFormatter(logging.Formatter):
    def format(self, record):
        record.session_id = SESSION_ID
        return super().format(record)

# Set up file handler with detailed formatting
file_handler = logging.FileHandler(SESSION_LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_formatter = SessionFormatter(
    '%(asctime)s - [%(session_id)s] - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
file_handler.setFormatter(file_formatter)

# Set up console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

# Track request stats
request_stats = {
    "schedule_get": 0,
    "adp_get": 0,
    "odb_get": 0,
    "errors": 0
}

# Initialize FastMCP server
mcp = FastMCP("dr-off-server")


@mcp.tool(name="schedule_get", description="OHIP Schedule of Benefits lookup with dual-path retrieval")
async def schedule_get_handler(query: str, k: int = 6, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    OHIP Schedule of Benefits lookup with dual-path retrieval.

    Args:
        query: OHIP billing query
        k: Number of results to return (default: 6)
        filters: Optional dict with codes, include

    Returns:
        Schedule items with provenance, citations, and confidence
    """
    start_time = datetime.now()
    logger.info(f">>> schedule.get called with query: {query}")

    # Build standardized request dict (query, k, filters)
    request = {
        "query": query,
        "k": k,
        "filters": filters or {}
    }

    logger.debug(f"Request data: {json.dumps(request, indent=2)}")
    request_stats["schedule_get"] += 1

    try:
        # Call tool wrapper function with standardized request
        response = await schedule_get(request)

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"schedule.get completed in {duration_ms:.2f}ms")
        if "items" in response:
            logger.info(f"Found {len(response['items'])} schedule items")
            codes_found = [item.get("code", "unknown") for item in response["items"][:3]]
            logger.info(f"Sample codes: {codes_found}")
        if "confidence" in response:
            logger.info(f"Confidence: {response['confidence']}")
        logger.debug(f"Full response: {json.dumps(response, indent=2)}")

        return response
    except Exception as e:
        logger.error(f"ERROR in schedule.get: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        request_stats["errors"] += 1
        return {
            "provenance": [],
            "confidence": 0.0,
            "items": [],
            "citations": [],
            "conflicts": []
        }


@mcp.tool(name="adp_get", description="ADP (Assistive Devices Program) eligibility and funding lookup")
async def adp_get_handler(query: str, k: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    ADP (Assistive Devices Program) eligibility and funding lookup.

    Args:
        query: Natural language query
        k: Number of results (default: 10)
        filters: Optional dict with device, check, use_case, patient_income

    Returns:
        Enhanced response with summary field
    """
    start_time = datetime.now()
    logger.info(f">>> adp.get called with query: {query}")

    # Build standardized request dict (query, k, filters)
    request = {
        "query": query,
        "k": k,
        "filters": filters or {}
    }

    logger.debug(f"Request data: {json.dumps(request, indent=2)}")
    request_stats["adp_get"] += 1

    try:
        # Call tool wrapper function with standardized request
        response = await adp_get(request)
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"adp.get completed in {duration_ms:.2f}ms")
        if "funding" in response and response["funding"]:
            logger.info(f"ADP funding: {response['funding'].get('adp_contribution')}% / Client: {response['funding'].get('client_share_percent')}%")
        if "cep" in response and response["cep"]:
            logger.info(f"CEP eligible: {response['cep'].get('eligible')}, Income threshold: ${response['cep'].get('income_threshold')}")
        logger.debug(f"Full response: {json.dumps(response, indent=2)}")

        return response
    except Exception as e:
        logger.error(f"ERROR in adp.get: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        request_stats["errors"] += 1
        return {
            "provenance": [],
            "confidence": 0.0,
            "eligibility": None,
            "exclusions": [],
            "funding": None,
            "cep": None,
            "citations": [],
            "conflicts": []
        }


@mcp.tool(name="odb_get", description="ODB (Ontario Drug Benefit) formulary lookup")
async def odb_get_handler(query: str, k: int = 5, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    ODB (Ontario Drug Benefit) formulary lookup with interchangeables.

    Args:
        query: Drug name, brand, or ingredient
        k: Number of alternatives (default: 5)
        filters: Optional dict with check_alternatives, include_lu, formulary_only

    Returns:
        Coverage status, interchangeables, lowest cost option
    """
    start_time = datetime.now()
    logger.info(f">>> odb.get called for drug: {query}")

    # Build standardized request dict (query, k, filters)
    request = {
        "query": query,
        "k": k,
        "filters": filters or {}
    }

    logger.debug(f"Request data: {json.dumps(request, indent=2)}")
    request_stats["odb_get"] += 1

    try:
        # Call tool wrapper function with standardized request
        response = await odb_get(request)
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"odb.get completed in {duration_ms:.2f}ms")
        if "coverage" in response and response["coverage"]:
            coverage = response["coverage"]
            logger.info(f"Drug covered: {coverage.get('covered')}, DIN: {coverage.get('din')}, LU required: {coverage.get('lu_required')}")
        if "interchangeable" in response:
            logger.info(f"Found {len(response['interchangeable'])} interchangeable drugs")
        logger.debug(f"Full response: {json.dumps(response, indent=2)}")

        return response
    except Exception as e:
        logger.error(f"ERROR in odb.get: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        request_stats["errors"] += 1
        return {
            "provenance": [],
            "confidence": 0.0,
            "coverage": None,
            "interchangeable": [],
            "lowest_cost": None,
            "citations": [],
            "conflicts": []
        }


def write_session_summary():
    """Write session summary at shutdown"""
    logger.info(f"{'=' * 80}")
    logger.info("SESSION SUMMARY")
    logger.info(f"Session ID: {SESSION_ID}")
    logger.info(f"Total requests: {sum(v for k, v in request_stats.items() if k != 'errors')}")
    for tool, count in request_stats.items():
        if count > 0:
            logger.info(f"  {tool}: {count}")
    logger.info(f"Log file: {SESSION_LOG_FILE}")
    logger.info(f"{'=' * 80}")
    
    # Write summary JSON file
    summary_file = LOG_DIR / f"session_{SESSION_ID}_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "session_id": SESSION_ID,
            "timestamp": datetime.now().isoformat(),
            "log_file": str(SESSION_LOG_FILE),
            "request_stats": request_stats
        }, f, indent=2)
    logger.info(f"Session summary written to: {summary_file}")


if __name__ == "__main__":
    try:
        logger.info(f"{'=' * 80}")
        logger.info(f"Dr. OFF MCP Server Session Started")
        logger.info(f"Session ID: {SESSION_ID}")
        logger.info(f"Log file: {SESSION_LOG_FILE}")
        logger.info(f"{'=' * 80}")
        logger.info("Registered tools:")
        logger.info("  - coverage.answer: Main orchestrator for clinical questions")
        logger.info("  - schedule.get: OHIP Schedule lookup")
        logger.info("  - adp.get: ADP device eligibility and funding")
        logger.info("  - odb.get: ODB drug formulary lookup")
        logger.info("  - source.passages: Retrieve exact text chunks")
        
        # Run the server on stdio (what MCP CLI expects)
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}")
        logger.exception("Full traceback:")
    finally:
        write_session_summary()