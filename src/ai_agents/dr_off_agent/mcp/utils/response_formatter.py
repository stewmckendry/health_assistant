"""
Response formatter utilities for Dr. OFF MCP tools.
Standardizes citations and response formats across all tools.
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime


def create_citation(
    source: str,
    source_org: str,
    loc: str = "",
    url: str = "",
    snippet: str = "",
    relevance_score: float = 0.9,
    section_path: str = ""
) -> Dict[str, Any]:
    """
    Create a standardized citation object with hierarchical source path.

    Args:
        source: Document or source title
        source_org: Organization name (e.g., "Ontario Ministry of Health")
        loc: Location in document (e.g., "Section 3.2", "Page 5")
        url: Source URL if available
        snippet: Relevant text snippet
        relevance_score: Confidence score (0-1)
        section_path: Hierarchical breadcrumb (e.g., "OHIP > Surgery > Neurosurgery (04)")

    Returns:
        Standardized citation dictionary
    """
    return {
        "id": f"cite_{uuid.uuid4().hex[:8]}",
        "source": source,
        "source_org": source_org,
        "loc": loc,
        "section_path": section_path,  # Hierarchical source path for structured citations
        "url": url,
        "snippet": snippet,
        "relevance_score": relevance_score,
        "access_date": datetime.now().isoformat()
    }


def deduplicate_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate citations based on source, org, and location.
    
    Args:
        citations: List of citation dictionaries
    
    Returns:
        Deduplicated list of citations
    """
    seen = set()
    unique_citations = []
    
    for citation in citations:
        # Create unique key from source, org, and location
        key = f"{citation.get('source', '')}_{citation.get('source_org', '')}_{citation.get('loc', '')}"
        
        if key not in seen:
            seen.add(key)
            unique_citations.append(citation)
    
    return unique_citations


def format_ohip_response(
    codes: List[Dict[str, Any]],
    query: str,
    confidence: float = 0.8
) -> Dict[str, Any]:
    """
    Format OHIP Schedule of Benefits response with citations.
    
    Args:
        codes: List of OHIP billing codes and details
        query: Original search query
        confidence: Response confidence score
    
    Returns:
        Formatted response with standardized citations
    """
    citations = []
    formatted_codes = []
    
    for code in codes:
        # Create citation for each code
        citation = create_citation(
            source=f"OHIP Schedule of Benefits - Code {code.get('code', '')}",
            source_org="Ontario Ministry of Health",
            loc=f"Fee Code: {code.get('code', '')}",
            url="https://www.ontario.ca/page/ohip-schedule-benefits-and-fees",
            snippet=code.get('description', '')[:200],
            relevance_score=code.get('score', 0.8)
        )
        citations.append(citation)
        
        # Format code details
        formatted_codes.append({
            "code": code.get('code', ''),
            "description": code.get('description', ''),
            "fee": code.get('fee', ''),
            "effective_date": code.get('effective_date', ''),
            "requirements": code.get('requirements', []),
            "citation_id": citation['id']
        })
    
    return {
        "type": "ohip_schedule",
        "query": query,
        "codes": formatted_codes,
        "citations": deduplicate_citations(citations),
        "confidence": confidence,
        "timestamp": datetime.now().isoformat()
    }


def format_adp_response(
    device_info: Dict[str, Any],
    eligibility: Dict[str, Any],
    query: str
) -> Dict[str, Any]:
    """
    Format ADP (Assistive Devices Program) response with citations.
    
    Args:
        device_info: Device coverage details
        eligibility: Eligibility criteria and requirements
        query: Original query
    
    Returns:
        Formatted response with standardized citations
    """
    citations = []
    
    # Create citations for device coverage
    if device_info.get('covered'):
        citation = create_citation(
            source=f"ADP Coverage - {device_info.get('device_type', 'Device')}",
            source_org="Assistive Devices Program",
            loc=device_info.get('category', ''),
            url="https://www.ontario.ca/page/assistive-devices-program",
            snippet=device_info.get('coverage_details', '')[:200],
            relevance_score=0.95
        )
        citations.append(citation)
    
    # Create citations for eligibility requirements
    if eligibility:
        citation = create_citation(
            source="ADP Eligibility Criteria",
            source_org="Assistive Devices Program",
            loc="Eligibility Requirements",
            url="https://www.ontario.ca/page/assistive-devices-program",
            snippet=str(eligibility.get('requirements', []))[:200],
            relevance_score=0.9
        )
        citations.append(citation)
    
    return {
        "type": "adp_coverage",
        "query": query,
        "device": device_info,
        "eligibility": eligibility,
        "funding_amount": device_info.get('funding_amount', 'Varies by device'),
        "citations": deduplicate_citations(citations),
        "confidence": 0.9 if device_info.get('covered') else 0.7,
        "timestamp": datetime.now().isoformat()
    }


def format_odb_response(
    drugs: List[Dict[str, Any]],
    query: str,
    alternatives: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Format ODB (Ontario Drug Benefit) formulary response with citations.
    
    Args:
        drugs: List of drug coverage details
        query: Original drug query
        alternatives: Optional list of alternative medications
    
    Returns:
        Formatted response with standardized citations
    """
    citations = []
    formatted_drugs = []
    
    for drug in drugs:
        # Create citation for each drug
        citation = create_citation(
            source=f"ODB Formulary - {drug.get('name', '')}",
            source_org="Ontario Drug Benefit Program",
            loc=f"DIN: {drug.get('din', '')}",
            url="https://www.ontario.ca/page/check-medication-coverage/",
            snippet=f"{drug.get('coverage_criteria', '')}",
            relevance_score=drug.get('score', 0.85)
        )
        citations.append(citation)
        
        # Format drug details
        formatted_drugs.append({
            "name": drug.get('name', ''),
            "din": drug.get('din', ''),
            "covered": drug.get('covered', False),
            "limited_use": drug.get('limited_use', False),
            "lu_code": drug.get('lu_code', ''),
            "criteria": drug.get('coverage_criteria', ''),
            "generic_available": drug.get('generic_available', False),
            "citation_id": citation['id']
        })
    
    # Add citations for alternatives if provided
    if alternatives:
        for alt in alternatives:
            citation = create_citation(
                source=f"ODB Alternative - {alt.get('name', '')}",
                source_org="Ontario Drug Benefit Program",
                loc="Alternative Medication",
                url="https://www.ontario.ca/page/check-medication-coverage/",
                snippet=alt.get('reason', '')[:200],
                relevance_score=0.8
            )
            citations.append(citation)
    
    return {
        "type": "odb_formulary",
        "query": query,
        "drugs": formatted_drugs,
        "alternatives": alternatives or [],
        "citations": deduplicate_citations(citations),
        "confidence": 0.9 if formatted_drugs else 0.6,
        "timestamp": datetime.now().isoformat()
    }


def format_error_response(
    error_message: str,
    tool_name: str,
    query: str
) -> Dict[str, Any]:
    """
    Format error response with helpful information.
    
    Args:
        error_message: Error details
        tool_name: Name of the tool that failed
        query: Original query
    
    Returns:
        Formatted error response
    """
    return {
        "type": "error",
        "tool": tool_name,
        "query": query,
        "error": error_message,
        "citations": [],
        "suggestions": [
            "Try rephrasing your query",
            "Check if the service code or drug name is correct",
            "Verify the device category for ADP queries"
        ],
        "confidence": 0.0,
        "timestamp": datetime.now().isoformat()
    }