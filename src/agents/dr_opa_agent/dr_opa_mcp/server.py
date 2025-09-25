"""
FastMCP server for Dr. OPA practice guidance tools.
Provides 6 tools for Ontario practice advice queries.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastmcp import FastMCP
import sys
import traceback

# Import retrieval clients
from .retrieval import SQLClient, VectorClient

# Import semantic search engine
from .search import SemanticSearchEngine

# Import Ontario Health Programs tool
from .tools.ontario_health_programs import get_client as get_ontario_health_client

# Import utilities
from .utils import calculate_confidence, resolve_conflicts
from .utils.confidence import OPAConfidenceScorer
from .utils.conflicts import OPAConflictResolver

# Import models
from .models.request import (
    SearchSectionsRequest,
    GetSectionRequest,
    PolicyCheckRequest,
    ProgramLookupRequest,
    IPACGuidanceRequest,
    FreshnessProbeRequest
)

# Add missing import
import sqlite3

from .models.response import (
    SearchSectionsResponse,
    GetSectionResponse,
    PolicyCheckResponse,
    ProgramLookupResponse,
    IPACGuidanceResponse,
    FreshnessProbeResponse,
    Section,
    Document,
    Citation,
    Highlight,
    Conflict,
    Update
)

# Configure logging with session-based file output
log_dir = Path("logs/dr_opa_agent")
log_dir.mkdir(parents=True, exist_ok=True)

# Session ID based on timestamp
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = log_dir / f"mcp_session_{session_id}.log"

# Configure both file and console logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Log session start
logger.info(f"="*60)
logger.info(f"Dr. OPA MCP Server Session: {session_id}")
logger.info(f"Log file: {log_file}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Environment: {os.environ.get('PYTHONPATH', 'Not set')}")
logger.info(f"="*60)

# Initialize FastMCP server
mcp = FastMCP("dr-opa-server")

# Initialize shared clients (lazy loading)
_sql_client = None
_vector_client = None
_semantic_search = None


def get_sql_client() -> SQLClient:
    """Get or create SQL client singleton."""
    global _sql_client
    if _sql_client is None:
        try:
            logger.info("Initializing SQL client...")
            _sql_client = SQLClient()
            logger.info("SQL client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SQL client: {e}")
            logger.error(traceback.format_exc())
            raise
    return _sql_client


def get_vector_client() -> VectorClient:
    """Get or create vector client singleton."""
    global _vector_client
    if _vector_client is None:
        try:
            logger.info("Initializing vector client...")
            _vector_client = VectorClient()
            logger.info("Vector client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector client: {e}")
            logger.error(traceback.format_exc())
            raise
    return _vector_client


def get_semantic_search() -> SemanticSearchEngine:
    """Get or create semantic search engine singleton."""
    global _semantic_search
    if _semantic_search is None:
        try:
            logger.info("Initializing semantic search engine...")
            vector_client = get_vector_client()
            _semantic_search = SemanticSearchEngine(vector_client)
            logger.info("Semantic search engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize semantic search: {e}")
            logger.error(traceback.format_exc())
            raise
    return _semantic_search


@mcp.tool(name="opa_search_sections", description="Hybrid search across OPA knowledge corpus")
async def search_sections_handler(
    query: str,
    sources: Optional[List[str]] = None,
    doc_types: Optional[List[str]] = None,
    topics: Optional[List[str]] = None,
    date_range: Optional[Dict[str, str]] = None,
    top_k: int = 10,
    include_superseded: bool = False
) -> Dict[str, Any]:
    """
    Hybrid search across OPA practice guidance corpus.
    Combines SQL full-text search and vector semantic search.
    
    Args:
        query: Clinical query or practice question
        sources: Specific sources to search
        doc_types: Document types to include
        topics: Topics to filter by
        date_range: Date range filter
        top_k: Number of results
        include_superseded: Include superseded documents
    
    Returns:
        Matching sections with documents, highlights, and confidence
    """
    logger.info(f"opa.search_sections called with query: {query[:100]}...")
    logger.debug(f"Parameters: sources={sources}, doc_types={doc_types}, topics={topics}, top_k={top_k}")
    
    try:
        semantic_search = get_semantic_search()
    except Exception as e:
        logger.error(f"Failed to get semantic search engine: {e}")
        return {
            "error": f"Search engine initialization failed: {str(e)}",
            "sections": [],
            "documents": [],
            "confidence": 0.0
        }
    
    # Use the new semantic search engine
    try:
        search_results = await semantic_search.search(
            query=query,
            sources=sources,
            document_types=doc_types,
            after_date=date_range.get('start') if date_range else None,
            top_k=top_k,
            use_reranking=True
        )
        
        logger.info(f"Semantic search returned {len(search_results)} results")
        
        # Format results for response
        formatted_results = semantic_search.format_results(search_results)
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        logger.error(traceback.format_exc())
        formatted_results = []
    
    # No conflicts in new approach - just semantic results
    conflicts = []
    resolved_data = {r['document_id']: r for r in formatted_results}
    
    # Convert to response format
    sections = []
    documents_map = {}
    
    for data in resolved_data.values():
        # Create section
        section = Section(
            section_id=data.get('section_id', data.get('chunk_id', '')),
            document_id=data.get('document_id', ''),
            heading=data.get('section_heading', ''),
            text=data.get('section_text', data.get('text', ''))[:500],  # Truncate for response
            chunk_type=data.get('chunk_type', 'unknown'),
            relevance_score=data.get('similarity_score', 0.8),
            metadata=data.get('metadata', {})
        )
        sections.append(section)
        
        # Track unique documents
        doc_id = data.get('document_id')
        if doc_id and doc_id not in documents_map:
            documents_map[doc_id] = Document(
                document_id=doc_id,
                title=data.get('document_title', data.get('title', '')),
                source_org=data.get('source_org', ''),
                document_type=data.get('document_type', ''),
                effective_date=data.get('effective_date'),
                topics=data.get('topics', []),
                url=data.get('source_url'),
                is_superseded=data.get('is_superseded', False)
            )
    
    # Create highlights from top results
    highlights = []
    for section in sections[:3]:
        highlight = Highlight(
            point=section.text[:200] + "...",
            citations=[Citation(
                source=section.metadata.get('title', 'Unknown'),
                source_org=section.metadata.get('source_org', ''),
                loc=section.heading,
                url=section.metadata.get('source_url')
            )]
        )
        highlights.append(highlight)
    
    # Calculate confidence based on semantic search results
    confidence = OPAConfidenceScorer.calculate(
        sql_hits=0,  # No SQL anymore
        vector_matches=len(sections),
        sources=sources,
        doc_types=doc_types,
        has_conflict=False  # No conflicts with single search
    )
    
    # Create response
    response = SearchSectionsResponse(
        sections=sections[:top_k],
        documents=list(documents_map.values()),
        provenance=['semantic_search'],
        confidence=confidence,
        highlights=highlights,
        conflicts=[],  # No conflicts with single search approach
        query_interpretation=f"Searching for: {query}"
    )
    
    return response.dict()


@mcp.tool(name="opa_get_section", description="Retrieve complete section details by ID")
async def get_section_handler(
    section_id: str,
    include_children: bool = True,
    include_context: bool = True
) -> Dict[str, Any]:
    """
    Retrieve complete section details by ID.
    
    Args:
        section_id: Section ID to retrieve
        include_children: Include child chunks
        include_context: Include surrounding sections
    
    Returns:
        Section with full content, document metadata, and context
    """
    logger.info(f"opa.get_section called for: {section_id}")
    
    sql_client = get_sql_client()
    
    # Get section with optional children and context
    section_data = await sql_client.get_section_by_id(
        section_id=section_id,
        include_children=include_children,
        include_context=include_context
    )
    
    if not section_data:
        return {
            "error": f"Section {section_id} not found",
            "section": None
        }
    
    # Create section object
    section = Section(
        section_id=section_data.get('section_id'),
        document_id=section_data.get('document_id'),
        heading=section_data.get('section_heading', ''),
        text=section_data.get('section_text', ''),
        chunk_type=section_data.get('chunk_type', 'unknown'),
        relevance_score=1.0,  # Direct retrieval
        metadata=section_data.get('metadata_json', {})
    )
    
    # Create document object
    document = Document(
        document_id=section_data.get('document_id'),
        title=section_data.get('document_title', ''),
        source_org=section_data.get('source_org', ''),
        document_type=section_data.get('document_type', ''),
        effective_date=section_data.get('effective_date'),
        topics=section_data.get('topics', []),
        url=section_data.get('source_url'),
        is_superseded=False
    )
    
    # Process children if included
    children = []
    if include_children and section_data.get('children'):
        for child_data in section_data['children']:
            children.append(Section(
                section_id=child_data.get('section_id'),
                document_id=child_data.get('document_id'),
                heading=child_data.get('section_heading', ''),
                text=child_data.get('section_text', ''),
                chunk_type='child',
                relevance_score=1.0,
                metadata={}
            ))
    
    # Process context if included
    context = []
    if include_context and section_data.get('context'):
        for ctx_data in section_data['context']:
            context.append(Section(
                section_id=ctx_data.get('section_id'),
                document_id=section_data.get('document_id'),
                heading=ctx_data.get('section_heading', ''),
                text='',  # Don't include full text for context
                chunk_type='context',
                relevance_score=0.8,
                metadata={'section_idx': ctx_data.get('section_idx')}
            ))
    
    # Create citations
    citations = [Citation(
        source=document.title,
        source_org=document.source_org,
        loc=section.heading,
        url=document.url
    )]
    
    # Create response
    response = GetSectionResponse(
        section=section,
        document=document,
        children=children,
        context=context,
        citations=citations
    )
    
    return response.dict()


@mcp.tool(name="opa_policy_check", description="CPSO-specific policy and advice retrieval")
async def policy_check_handler(
    topic: str,
    situation: Optional[str] = None,
    policy_level: str = "both",
    include_related: bool = True
) -> Dict[str, Any]:
    """
    CPSO-specific policy and advice retrieval.
    
    Args:
        topic: Clinical topic or practice area
        situation: Specific situation or context
        policy_level: 'expectation', 'advice', or 'both'
        include_related: Include related policies
    
    Returns:
        Relevant policies, expectations, advice with confidence
    """
    logger.info(f"opa.policy_check called for topic: {topic}")
    logger.debug(f"Parameters: situation={situation}, policy_level={policy_level}, include_related={include_related}")
    
    try:
        semantic_search = get_semantic_search()
    except Exception as e:
        logger.error(f"Failed to get semantic search engine: {e}")
        return PolicyCheckResponse(
            policies=[],
            expectations=[],
            advice=[],
            related=[],
            confidence=0.6,
            summary=f"CPSO Guidance for '{topic}': No specific CPSO guidance found for this topic"
        ).dict()
    
    # Search for CPSO policies using semantic search
    search_query = f"{topic} {situation}" if situation else topic
    
    # Use semantic search with CPSO filter
    try:
        search_results = await semantic_search.search(
            query=search_query,
            sources=['cpso'],
            policy_level=policy_level if policy_level != "both" else None,
            top_k=15,  # Get more for categorization
            use_reranking=True
        )
        
        logger.info(f"Semantic search found {len(search_results)} CPSO documents")
        
        # Format results
        policies_data = semantic_search.format_results(search_results)
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        logger.error(traceback.format_exc())
        policies_data = []
    
    # Organize results
    policies = []
    expectations = []
    advice_items = []
    
    for policy_data in policies_data:
        # Create document - use document_title for semantic search results
        doc = Document(
            document_id=policy_data.get('document_id'),
            title=policy_data.get('document_title') or policy_data.get('title'),
            source_org=policy_data.get('source_org', 'cpso'),
            document_type=policy_data.get('document_type'),
            effective_date=policy_data.get('effective_date'),
            topics=policy_data.get('topics', []),
            url=policy_data.get('source_url'),
            is_superseded=False
        )
        policies.append(doc)
        
        # Categorize by policy level
        level = policy_data.get('policy_level')
        doc_title = policy_data.get('document_title') or policy_data.get('title', 'Unknown')
        if level == 'expectation':
            expectations.append(Highlight(
                point=f"{doc_title}: Mandatory expectation",
                citations=[Citation(
                    source=doc_title,
                    source_org='cpso',
                    loc='Policy',
                    url=policy_data.get('source_url')
                )],
                policy_level='expectation'
            ))
        elif level == 'advice':
            advice_items.append(Highlight(
                point=f"{doc_title}: Professional advice",
                citations=[Citation(
                    source=doc_title,
                    source_org='cpso',
                    loc='Advice',
                    url=policy_data.get('source_url')
                )],
                policy_level='advice'
            ))
    
    # Find related documents if requested
    related = []
    if include_related and policies:
        # Get topics from main results
        all_topics = set()
        for p in policies:
            all_topics.update(p.topics)
        
        # Search for related by topics
        for related_topic in list(all_topics)[:3]:  # Limit to 3 topics
            related_data = await get_sql_client().search_policies(
                topic=related_topic,
                policy_level=None,
                include_related=False
            )
            
            for r_data in related_data[:2]:  # Limit to 2 per topic
                if r_data.get('document_id') not in [p.document_id for p in policies]:
                    related.append(Document(
                        document_id=r_data.get('document_id'),
                        title=r_data.get('title'),
                        source_org='cpso',
                        document_type=r_data.get('document_type'),
                        effective_date=r_data.get('effective_date'),
                        topics=r_data.get('topics', []),
                        url=r_data.get('source_url'),
                        is_superseded=False
                    ))
    
    # Calculate confidence
    confidence = OPAConfidenceScorer.calculate(
        sql_hits=len(policies_data),
        vector_matches=0,
        sources=['cpso'],
        doc_types=['policy', 'advice'],
        has_conflict=False
    )
    
    # Create summary
    summary_parts = []
    if expectations:
        summary_parts.append(f"Found {len(expectations)} mandatory expectation(s)")
    if advice_items:
        summary_parts.append(f"Found {len(advice_items)} professional advice item(s)")
    if not summary_parts:
        summary_parts.append("No specific CPSO guidance found for this topic")
    
    summary = f"CPSO Guidance for '{topic}': " + "; ".join(summary_parts)
    
    # Create response
    response = PolicyCheckResponse(
        policies=policies,
        expectations=expectations,
        advice=advice_items,
        related=related[:5],  # Limit related to 5
        confidence=confidence,
        summary=summary
    )
    
    return response.dict()


@mcp.tool(name="opa_program_lookup", description="Ontario Health clinical programs information (cancer, kidney, cardiac, etc.)")
async def program_lookup_handler(
    program: str,
    patient_age: Optional[int] = None,
    risk_factors: Optional[List[str]] = None,
    info_needed: List[str] = None
) -> Dict[str, Any]:
    """
    Ontario Health clinical programs information lookup using Claude with web search.
    Covers all Ontario Health programs including cancer care, kidney care, cardiac,
    stroke, mental health, palliative care, and more.
    
    Args:
        program: Clinical program name (e.g., "cancer screening", "kidney care", "cardiac", "stroke")
        patient_age: Patient age for eligibility
        risk_factors: Patient risk factors
        info_needed: Information types to retrieve (e.g., ["eligibility", "locations", "referral"])
    
    Returns:
        Program information including eligibility, procedures, locations, and resources
    """
    logger.info(f"opa.program_lookup called for program: {program}")
    logger.debug(f"Parameters: age={patient_age}, risk_factors={risk_factors}, info_needed={info_needed}")
    
    try:
        # Use the Ontario Health Programs client with Claude + web_search
        ontario_client = get_ontario_health_client()
        
        # Search for program information using Claude with restricted domain search
        program_info = ontario_client.search_program(
            program=program,
            patient_age=patient_age,
            risk_factors=risk_factors,
            info_needed=info_needed
        )
        
        # Check for errors from the client
        if "error" in program_info:
            logger.error(f"Ontario Health client error: {program_info['error']}")
            return {
                "error": program_info.get("error"),
                "program": program,
                "message": program_info.get("message", "Failed to retrieve program information")
            }
        
        # Extract structured information from the response
        eligibility = program_info.get("eligibility", {})
        access_info = program_info.get("access", {})
        services = program_info.get("services", [])
        locations = program_info.get("locations", [])
        resources = program_info.get("resources", [])
        citations = program_info.get("citations", [])
        
        # Convert to ProgramLookupResponse format for backward compatibility
        # Build procedures list from services
        procedures = services[:5] if services else []
        
        # Build intervals from eligibility info if available
        intervals = {}
        if "age_criteria" in eligibility:
            intervals["eligibility"] = eligibility.get("age_criteria")
        
        # Build follow-up from access info
        followup = {}
        if "referral_process" in access_info:
            followup["referral"] = access_info.get("referral_process")
        if "self_referral" in access_info:
            followup["self_referral"] = access_info.get("self_referral")
        
        # Patient-specific recommendations
        patient_specific = program_info.get("patient_specific")
        if not patient_specific and patient_age:
            # Generate basic recommendations based on age
            patient_specific = {
                "age": patient_age,
                "recommendation": f"Please consult the program eligibility criteria for age {patient_age}"
            }
            
            if risk_factors:
                patient_specific["risk_factors"] = risk_factors
                patient_specific["recommendation"] += " with consideration of risk factors"
        
        # Convert citations to Citation objects
        formatted_citations = []
        for cit in citations[:5]:  # Limit to 5 citations
            formatted_citations.append(Citation(
                source=cit.get("title", "Ontario Health"),
                source_org="ontario_health",
                loc=f"{program.capitalize()} Program",
                url=cit.get("url", "")
            ))
        
        # Add locations and resources to the response
        additional_info = {}
        if locations:
            additional_info["locations"] = locations
        if resources:
            additional_info["resources"] = resources
        if program_info.get("overview"):
            additional_info["overview"] = program_info["overview"]
        
        # Create response
        response = ProgramLookupResponse(
            program=program,
            eligibility=eligibility,
            intervals=intervals,
            procedures=procedures,
            followup=followup,
            patient_specific=patient_specific,
            citations=formatted_citations,
            last_updated=datetime.now().isoformat(),
            additional_info=additional_info  # Include extra information
        )
        
        logger.info(f"Successfully retrieved {program} program information with {len(formatted_citations)} citations")
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in program_lookup_handler: {e}")
        logger.error(traceback.format_exc())
        
        # Fallback to SQL client for backward compatibility with screening programs
        try:
            logger.info("Attempting fallback to SQL client for screening programs")
            sql_client = get_sql_client()
            
            # Try to get basic screening program info from database
            program_data = await sql_client.get_program_info(program)
            
            if program_data:
                # Use the old parsing logic for screening programs
                return _parse_screening_program_data(program_data, program, patient_age, risk_factors)
        except Exception as sql_error:
            logger.error(f"SQL fallback also failed: {sql_error}")
        
        # Return error response
        return {
            "error": str(e),
            "program": program,
            "message": "Failed to retrieve program information from Ontario Health sources"
        }


def _parse_screening_program_data(program_data: Dict, program: str, patient_age: Optional[int], risk_factors: Optional[List[str]]) -> Dict[str, Any]:
    """Helper function to parse screening program data from SQL database (backward compatibility)."""
    eligibility = {}
    intervals = {}
    procedures = []
    followup = {}
    
    # Extract information from sections (simplified version of old logic)
    for section in program_data.get('sections', []):
        text = section.get('text', '').lower()
        heading = section.get('heading', '').lower()
        
        if 'eligib' in heading:
            if '50' in text and '74' in text:
                eligibility['age_range'] = '50-74'
            elif '21' in text and '69' in text:
                eligibility['age_range'] = '21-69'
        
        if 'interval' in heading:
            if 'every 2 years' in text:
                intervals['standard'] = 'Every 2 years'
            elif 'every 3 years' in text:
                intervals['standard'] = 'Every 3 years'
    
    # Patient-specific recommendations
    patient_specific = None
    if patient_age:
        patient_specific = {
            'age': patient_age,
            'recommendation': f'Check eligibility for {program} screening at age {patient_age}'
        }
    
    # Create minimal citations
    citations = [Citation(
        source="Ontario Health Database",
        source_org='ontario_health',
        loc=f"{program.capitalize()} Screening Program",
        url=""
    )]
    
    response = ProgramLookupResponse(
        program=program,
        eligibility=eligibility,
        intervals=intervals,
        procedures=procedures,
        followup=followup,
        patient_specific=patient_specific,
        citations=citations,
        last_updated=None
    )
    
    return response.dict()


@mcp.tool(name="opa_ipac_guidance", description="PHO infection prevention and control guidance")
async def ipac_guidance_handler(
    setting: str,
    topic: str,
    pathogen: Optional[str] = None,
    include_checklists: bool = True
) -> Dict[str, Any]:
    """
    PHO infection prevention and control guidance.
    
    Args:
        setting: Healthcare setting (clinic, hospital, community, ltc)
        topic: IPAC topic (hand hygiene, PPE, sterilization, etc.)
        pathogen: Specific pathogen if applicable
        include_checklists: Include practical checklists
    
    Returns:
        IPAC guidelines, procedures, checklists, and resources
    """
    logger.info(f"opa.ipac_guidance called for {setting}/{topic}")
    
    # Build search query
    search_query = f"{setting} {topic}"
    if pathogen:
        search_query += f" {pathogen}"
    
    logger.info(f"IPAC guidance search: '{search_query}'")
    
    # Use semantic search for IPAC guidance
    semantic_search = get_semantic_search()
    
    try:
        search_results = await semantic_search.search(
            query=search_query,
            sources=['pho'],  # Focus on PHO for IPAC
            document_types=['guideline', 'tool', 'policy'],
            top_k=15,
            use_reranking=True
        )
        
        # Format results
        formatted_results = semantic_search.format_results(search_results)
        logger.info(f"Semantic search returned {len(formatted_results)} IPAC results")
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        logger.error(traceback.format_exc())
        formatted_results = []
    
    # Process results
    guidelines = []
    procedures = []
    checklists = []
    
    for result in formatted_results:
        text = result.get('text', '')
        heading = result.get('section_heading', '')
        
        # Create highlight for key guidelines
        if any(kw in heading.lower() for kw in ['requirement', 'must', 'standard']):
            guidelines.append(Highlight(
                point=text[:300],
                citations=[Citation(
                    source=result.get('document_title', ''),
                    source_org='pho',
                    loc=heading,
                    url=result.get('source_url')
                )]
            ))
        
        # Extract procedures
        if any(kw in heading.lower() for kw in ['procedure', 'step', 'process']):
            procedures.append({
                'title': heading,
                'steps': text[:500],
                'source': result.get('document_title', '')
            })
        
        # Extract checklists
        if include_checklists and any(kw in heading.lower() for kw in ['checklist', 'list', 'requirements']):
            checklists.append({
                'title': heading,
                'items': text[:400],
                'source': result.get('document_title', '')
            })
    
    # Pathogen-specific guidance
    pathogen_specific = None
    if pathogen:
        pathogen_results = [r for r in formatted_results if pathogen.lower() in r.get('text', '').lower()]
        if pathogen_results:
            pathogen_specific = {
                'pathogen': pathogen,
                'guidance': pathogen_results[0].get('text', '')[:500],
                'source': pathogen_results[0].get('document_title', '')
            }
    
    # Create citations
    citations = []
    seen_sources = set()
    for result in formatted_results[:5]:
        source = result.get('document_title', '')
        if source and source not in seen_sources:
            seen_sources.add(source)
            citations.append(Citation(
                source=source,
                source_org='pho',
                loc='IPAC Guidance',
                url=result.get('source_url')
            ))
    
    # Additional resources
    resources = [
        {'title': 'PHO IPAC Best Practices', 'url': 'https://www.publichealthontario.ca/ipac'},
        {'title': 'Hand Hygiene Resources', 'url': 'https://www.publichealthontario.ca/hand-hygiene'}
    ]
    
    # Create response
    response = IPACGuidanceResponse(
        setting=setting,
        topic=topic,
        guidelines=guidelines[:5],  # Limit to top 5
        procedures=procedures[:3],  # Limit to 3
        checklists=checklists[:3],  # Limit to 3
        pathogen_specific=pathogen_specific,
        citations=citations,
        resources=resources
    )
    
    return response.dict()


@mcp.tool(name="opa_freshness_probe", description="Check for guidance updates on a topic")
async def freshness_probe_handler(
    topic: str,
    current_date: Optional[str] = None,
    sources: Optional[List[str]] = None,
    check_web: bool = True
) -> Dict[str, Any]:
    """
    Check for guidance updates on a topic.
    
    Args:
        topic: Topic to check for updates
        current_date: Reference date for checking
        sources: Specific sources to check
        check_web: Check web for recent updates
    
    Returns:
        Current guidance status, recent updates, and recommendations
    """
    logger.info(f"opa.freshness_probe called for topic: {topic}")
    
    sql_client = get_sql_client()
    
    # Check current guidance in corpus
    freshness_data = await sql_client.check_freshness(
        topic=topic,
        sources=sources
    )
    
    current_guidance = freshness_data.get('current_guidance')
    last_updated = freshness_data.get('last_updated')
    
    if not current_guidance:
        return FreshnessProbeResponse(
            topic=topic,
            current_guidance=Document(
                document_id='none',
                title='No guidance found',
                source_org='',
                document_type='',
                effective_date=None,
                topics=[],
                url=None,
                is_superseded=False
            ),
            last_updated='Unknown',
            updates_found=False,
            recent_updates=[],
            recommended_action='No guidance in corpus - search for new sources',
            web_sources_checked=[]
        ).dict()
    
    # Convert to Document
    current_doc = Document(
        document_id=current_guidance.get('document_id', ''),
        title=current_guidance.get('title', ''),
        source_org=current_guidance.get('source_org', ''),
        document_type=current_guidance.get('document_type', ''),
        effective_date=current_guidance.get('effective_date'),
        topics=[],
        url=current_guidance.get('source_url'),
        is_superseded=False
    )
    
    # Calculate age of guidance
    updates_found = False
    recent_updates = []
    recommended_action = "Corpus is current"
    
    if last_updated:
        try:
            last_date = datetime.fromisoformat(last_updated.replace('Z', ''))
            days_old = (datetime.now() - last_date).days
            
            if days_old > 730:  # > 2 years
                recommended_action = "Guidance is over 2 years old - recommend checking for updates"
                updates_found = True
            elif days_old > 365:  # > 1 year
                recommended_action = "Guidance is over 1 year old - periodic review recommended"
            else:
                recommended_action = "Guidance is current (less than 1 year old)"
        except:
            pass
    
    # Mock web check (in production would actually search)
    web_sources_checked = []
    if check_web:
        web_sources_checked = [
            f"https://www.cpso.on.ca/search?q={topic}",
            f"https://www.ontariohealth.ca/search?q={topic}"
        ]
        
        # Simulate finding an update for old guidance
        if updates_found:
            recent_updates.append(Update(
                topic=topic,
                date=datetime.now().isoformat(),
                source="Web search (simulated)",
                summary="Newer guidance may be available - manual verification required",
                url=web_sources_checked[0]
            ))
    
    # Create response
    response = FreshnessProbeResponse(
        topic=topic,
        current_guidance=current_doc,
        last_updated=last_updated or 'Unknown',
        updates_found=updates_found,
        recent_updates=recent_updates,
        recommended_action=recommended_action,
        web_sources_checked=web_sources_checked
    )
    
    return response.dict()


@mcp.tool(name="opa_clinical_tools", description="CEP clinical decision support tools lookup")
async def clinical_tools_handler(
    condition: Optional[str] = None,
    tool_name: Optional[str] = None,
    category: Optional[str] = None,
    feature_type: Optional[str] = None,
    include_sections: bool = False
) -> Dict[str, Any]:
    """
    CEP clinical tools navigation and quick reference.
    Returns tool summaries with direct links to interactive features.
    
    Args:
        condition: Clinical condition (e.g., "dementia", "depression")
        tool_name: Specific tool name
        category: Tool category filter (mental_health, chronic_disease, etc.)
        feature_type: Type of clinical feature (algorithm, calculator, checklist)
        include_sections: Include section summaries
    
    Returns:
        Clinical tools with navigation links and key content
    """
    logger.info(f"opa.clinical_tools called - condition: {condition}, category: {category}")
    
    # Build search query
    search_parts = []
    if condition:
        search_parts.append(f"clinical tool for {condition}")
    if tool_name:
        search_parts.append(tool_name)
    if category:
        search_parts.append(f"{category} tools")
    if feature_type:
        search_parts.append(f"{feature_type} calculator algorithm checklist")
    
    # Default query if no specific criteria
    if not search_parts:
        search_query = "clinical decision support tools"
    else:
        search_query = " ".join(search_parts)
    
    logger.info(f"Clinical tools semantic search: '{search_query}'")
    
    # Use semantic search for clinical tools
    semantic_search = get_semantic_search()
    
    try:
        search_results = await semantic_search.search(
            query=search_query,
            sources=['cep'],  # Focus on CEP for clinical tools
            document_types=['clinical_tool'],
            top_k=20,  # Get more tools
            use_reranking=True
        )
        
        # Format results
        formatted_results = semantic_search.format_results(search_results)
        logger.info(f"Semantic search returned {len(formatted_results)} clinical tools")
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        logger.error(traceback.format_exc())
        formatted_results = []
    
    # Process results into tools
    tools = []
    for result in formatted_results:
        # Extract fields from semantic search results
        doc_id = result.get('document_id', '')
        title = result.get('document_title', '')
        url = result.get('source_url', '')
        last_updated = result.get('effective_date', '')
        text = result.get('text', '')
        
        # Parse metadata if available
        metadata = {}
        if 'metadata' in result:
            metadata = result['metadata']
        
        tool_data = {
            'tool_id': doc_id,
            'name': title,
            'url': url,
            'last_updated': last_updated,
            'category': category or 'general',
            'summary': text[:500] if text else '',
            'key_features': {}
        }
        
        # Extract features from text/metadata
        text_lower = text.lower() if text else ''
        if 'algorithm' in text_lower or 'assessment' in text_lower:
            tool_data['key_features']['assessment_algorithm'] = {
                'available': True,
                'url': f"{url}#assessment"
            }
        
        if 'calculator' in text_lower or 'calculate' in text_lower:
            tool_data['key_features']['calculator'] = {
                'available': True,
                'url': f"{url}#calculator"
            }
        
        if 'checklist' in text_lower or 'criteria' in text_lower:
            tool_data['key_features']['checklist'] = {
                'available': True,
                'url': f"{url}#checklist"
            }
        
        # Add sections if requested
        if include_sections and text:
            # Extract section-like content from text
            lines = text.split('\n')
            tool_data['sections'] = []
            for i, line in enumerate(lines[:5]):  # First 5 lines as sections
                if line.strip():
                    tool_data['sections'].append({
                        'title': f"Section {i+1}",
                        'summary': line[:200] + '...' if len(line) > 200 else line,
                        'url': url
                    })
        
        # Add quick links
        tool_data['quick_links'] = {
            'full_tool': url,
            'pdf_version': None  # CEP tools typically don't have PDFs
        }
        
        tools.append(tool_data)
    
    # Create response
    response = {
        'tools': tools,
        'total_tools': len(tools),
        'query_interpretation': f"Searching CEP clinical tools"
    }
    
    if condition:
        response['query_interpretation'] += f" for condition: {condition}"
    elif category:
        response['query_interpretation'] += f" in category: {category}"
    elif feature_type:
        response['query_interpretation'] += f" with feature: {feature_type}"
    
    return response


if __name__ == "__main__":
    logger.info("Starting Dr. OPA MCP server...")
    logger.info("Registered tools:")
    logger.info("  - opa.search_sections: Hybrid search across OPA corpus")
    logger.info("  - opa.get_section: Retrieve complete section by ID")
    logger.info("  - opa.policy_check: CPSO policy and advice retrieval")
    logger.info("  - opa.program_lookup: Ontario Health clinical programs (ALL programs via web search)")
    logger.info("  - opa.ipac_guidance: PHO infection prevention guidance")
    logger.info("  - opa.freshness_probe: Check for guidance updates")
    logger.info("  - opa.clinical_tools: CEP clinical decision support tools")
    
    # Try to initialize clients on startup but don't fail if database is missing
    try:
        logger.info("Attempting to initialize database clients...")
        get_sql_client()
        get_vector_client()
        logger.info("Dr. OPA MCP server ready with database connections")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.warning("Server will start but database operations may fail")
        logger.warning("Please ensure database is populated using ingestion scripts")
    
    logger.info(f"Server session log: {log_file}")
    
    # Run the server on stdio (what MCP CLI expects)
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Server crashed: {e}")
        logger.error(traceback.format_exc())
        raise