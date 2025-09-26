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

# Import tool handlers
from .tools.coverage import coverage_answer
from .tools.schedule import schedule_get
from .tools.adp import adp_get
from .tools.odb import odb_get
from .tools.source import source_passages

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
    "coverage.answer": 0,
    "schedule.get": 0,
    "adp.get": 0,
    "odb.get": 0,
    "source.passages": 0,
    "errors": 0
}

# Initialize FastMCP server
mcp = FastMCP("dr-off-server")


@mcp.tool(name="coverage.answer", description="Main orchestrator for clinical coverage questions")
async def coverage_answer_handler(
    question: str,
    hints: Dict[str, Any] = None,
    patient: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Main orchestrator for clinical coverage questions.
    Routes to appropriate domain tools and synthesizes response.
    
    Args:
        question: Free-text clinical question
        hints: Optional hints (codes, device, drug)
        patient: Optional patient context (age, setting, income)
    
    Returns:
        Comprehensive answer with decision, citations, and confidence
    """
    start_time = datetime.now()
    logger.info(f">>> coverage.answer called with question: {question[:100]}...")
    
    request = {
        "question": question,
        "hints": hints or {},
        "patient": patient or {}
    }
    
    logger.debug(f"Request data: {json.dumps(request, indent=2)}")
    request_stats["coverage.answer"] += 1
    
    try:
        response = await coverage_answer(request)
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info(f"coverage.answer completed in {duration_ms:.2f}ms")
        logger.debug(f"Response keys: {list(response.keys())}")
        if "confidence" in response:
            logger.info(f"Confidence: {response['confidence']}")
        if "decision" in response:
            logger.info(f"Decision: {response['decision']}")
        if "tools_used" in response:
            logger.info(f"Tools used: {response['tools_used']}")
        logger.debug(f"Full response: {json.dumps(response, indent=2)}")
        
        return response
    except Exception as e:
        logger.error(f"ERROR in coverage.answer: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        request_stats["errors"] += 1
        return {
            "error": str(e),
            "tools_used": [],
            "confidence": 0.0,
            "evidence": [],
            "provenance": []
        }


@mcp.tool(name="schedule.get", description="OHIP Schedule of Benefits lookup with dual-path retrieval")
async def schedule_get_handler(
    q: str,
    codes: list = None,
    include: list = None,
    top_k: int = 6
) -> Dict[str, Any]:
    """
    OHIP Schedule of Benefits lookup with dual-path retrieval.
    
    Args:
        q: Query text for schedule search
        codes: Specific fee codes to lookup
        include: Fields to include in response
        top_k: Number of results to return
    
    Returns:
        Schedule items with provenance, citations, and confidence
    """
    start_time = datetime.now()
    logger.info(f">>> schedule.get called with query: {q}")
    
    request = {
        "q": q,
        "codes": codes or [],
        "include": include or ["codes", "fee", "limits", "documentation"],
        "top_k": top_k
    }
    
    logger.debug(f"Request data: {json.dumps(request, indent=2)}")
    request_stats["schedule.get"] += 1
    
    try:
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


@mcp.tool(
    name="adp.get", 
    description="""ADP (Assistive Devices Program) eligibility and funding lookup.

    Accepts EITHER natural language OR structured format:
    
    NATURAL LANGUAGE (Recommended for LLMs):
    {"query": "Can my patient get funding for a CPAP?", "patient_income": 35000}
    {"query": "Is a power wheelchair covered by ADP?"}
    
    STRUCTURED FORMAT:
    Device categories: mobility, comm_aids (or communication), hearing_devices (or hearing), 
    visual_aids (or vision), respiratory, insulin_pump, glucose_monitoring, prosthesis, 
    maxillofacial, grants
    
    Example structured requests:
    1. Wheelchair: {"device": {"category": "mobility", "type": "wheelchair"}}
    2. Hearing aid: {"device": {"category": "hearing", "type": "hearing aid"}}  
    3. CPAP: {"device": {"category": "respiratory", "type": "CPAP"}}
    4. With income check: {..., "patient_income": 25000, "check": ["cep"]}
    """
)
async def adp_get_handler(
    query: str = None,  # Natural language query
    device: Dict[str, str] = None,  # Structured device spec
    check: list = None,
    use_case: Dict[str, Any] = None,
    patient_income: float = None
) -> Dict[str, Any]:
    """
    ADP (Assistive Devices Program) eligibility and funding lookup.
    
    Args:
        query: Natural language query (e.g., "Can I get funding for a CPAP?")
        device: Structured device specification (alternative to query)
        check: What to check - ["eligibility", "exclusions", "funding", "cep"]
        use_case: Optional usage details (daily use, location, etc)
        patient_income: Annual income in CAD for CEP eligibility check
    
    Returns:
        Enhanced response with summary field for easy LLM interpretation
    """
    start_time = datetime.now()
    
    # Build request based on input format
    if query:
        # Natural language format
        logger.info(f">>> adp.get called with query: {query}")
        request = {
            "query": query,
            "patient_income": patient_income
        }
    else:
        # Structured format
        logger.info(f">>> adp.get called for device: {device}")
        request = {
            "device": device,
            "check": check or ["eligibility", "exclusions", "funding"],
            "use_case": use_case or {},
            "patient_income": patient_income
        }
    
    logger.debug(f"Request data: {json.dumps(request, indent=2)}")
    request_stats["adp.get"] += 1
    
    try:
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


@mcp.tool(name="odb.get", description="ODB (Ontario Drug Benefit) formulary lookup")
async def odb_get_handler(
    drug: str,
    check_alternatives: bool = True,
    include_lu: bool = True,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    ODB (Ontario Drug Benefit) formulary lookup with interchangeables.
    
    Args:
        drug: Drug name, brand, or ingredient
        check_alternatives: Check for interchangeable alternatives
        include_lu: Include Limited Use criteria if applicable
        top_k: Number of alternatives to return
    
    Returns:
        Coverage status, interchangeables, lowest cost option
    """
    start_time = datetime.now()
    logger.info(f">>> odb.get called for drug: {drug}")
    
    request = {
        "drug": drug,
        "check_alternatives": check_alternatives,
        "include_lu": include_lu,
        "top_k": top_k
    }
    
    logger.debug(f"Request data: {json.dumps(request, indent=2)}")
    request_stats["odb.get"] += 1
    
    try:
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


@mcp.tool(name="source.passages", description="Retrieve exact text chunks by ID")
async def source_passages_handler(
    chunk_ids: list,
    highlight_terms: list = None
) -> Dict[str, Any]:
    """
    Retrieve exact text passages from vector store by chunk IDs.
    
    Args:
        chunk_ids: List of chunk IDs to retrieve
        highlight_terms: Optional terms to highlight in passages
    
    Returns:
        Retrieved passages with metadata
    """
    start_time = datetime.now()
    logger.info(f">>> source.passages called for {len(chunk_ids)} chunks")
    
    request = {
        "chunk_ids": chunk_ids,
        "highlight_terms": highlight_terms or []
    }
    
    logger.debug(f"Request data: {json.dumps(request, indent=2)}")
    request_stats["source.passages"] += 1
    
    try:
        response = await source_passages(request)
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        logger.info(f"source.passages completed in {duration_ms:.2f}ms")
        logger.debug(f"Full response: {json.dumps(response, indent=2)}")
        
        return response
    except Exception as e:
        logger.error(f"ERROR in source.passages: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        request_stats["errors"] += 1
        return {
            "passages": [],
            "errors": [str(e)]
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