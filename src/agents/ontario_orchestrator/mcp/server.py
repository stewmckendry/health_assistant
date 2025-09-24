"""
FastMCP server for Dr. OFF clinical decision support tools.
Provides 5 tools for Ontario healthcare coverage queries.
"""

import asyncio
import logging
from typing import Dict, Any
from fastmcp import FastMCP

# Import tool handlers
from .tools.coverage import coverage_answer
from .tools.schedule import schedule_get
from .tools.adp import adp_get
from .tools.odb import odb_get
from .tools.source import source_passages

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    logger.info(f"coverage.answer called with question: {question[:100]}...")
    
    request = {
        "question": question,
        "hints": hints or {},
        "patient": patient or {}
    }
    
    response = await coverage_answer(request)
    return response


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
    logger.info(f"schedule.get called with query: {q}")
    
    request = {
        "q": q,
        "codes": codes or [],
        "include": include or ["codes", "fee", "limits", "documentation"],
        "top_k": top_k
    }
    
    response = await schedule_get(request)
    return response


@mcp.tool(name="adp.get", description="ADP (Assistive Devices Program) eligibility and funding lookup")
async def adp_get_handler(
    device: Dict[str, str],
    check: list = None,
    use_case: Dict[str, Any] = None,
    patient_income: float = None
) -> Dict[str, Any]:
    """
    ADP (Assistive Devices Program) eligibility and funding lookup.
    
    Args:
        device: Device specification (category, type)
        check: Aspects to check (eligibility, exclusions, funding, cep)
        use_case: Device use case details
        patient_income: Annual income for CEP eligibility
    
    Returns:
        Eligibility, funding, exclusions, and CEP information
    """
    logger.info(f"adp.get called for device: {device}")
    
    request = {
        "device": device,
        "check": check or ["eligibility", "exclusions", "funding"],
        "use_case": use_case or {},
        "patient_income": patient_income
    }
    
    response = await adp_get(request)
    return response


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
    logger.info(f"odb.get called for drug: {drug}")
    
    request = {
        "drug": drug,
        "check_alternatives": check_alternatives,
        "include_lu": include_lu,
        "top_k": top_k
    }
    
    response = await odb_get(request)
    return response


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
    logger.info(f"source.passages called for {len(chunk_ids)} chunks")
    
    request = {
        "chunk_ids": chunk_ids,
        "highlight_terms": highlight_terms or []
    }
    
    response = await source_passages(request)
    return response


if __name__ == "__main__":
    logger.info("Starting Dr. OFF MCP server...")
    logger.info("Registered tools:")
    logger.info("  - coverage.answer: Main orchestrator for clinical questions")
    logger.info("  - schedule.get: OHIP Schedule lookup")
    logger.info("  - adp.get: ADP device eligibility and funding")
    logger.info("  - odb.get: ODB drug formulary lookup")
    logger.info("  - source.passages: Retrieve exact text chunks")
    
    # Run the server on stdio (what MCP CLI expects)
    mcp.run()