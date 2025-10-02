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
from .utils.response_formatter import standardize_mcp_response

# Import models
from .models.request import (
    SearchSectionsRequest,
    GetSectionRequest,
    PolicyCheckRequest,
    ProgramLookupRequest,
    IPACGuidanceRequest,
    FreshnessProbeRequest,
    QualityStandardsRequest,
    ChoosingWiselyRequest
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
    QualityStandardsResponse,
    QualityStatement,
    ChoosingWiselyResponse,
    ChoosingWiselyRecommendation,
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
    
    # Standardize response with top-level citations
    response_dict = response.dict()
    tool_name = "opa_search_sections"
    return standardize_mcp_response(response_dict, tool_name)


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
    # Parse metadata_json if it's a string
    metadata = section_data.get('metadata_json', {})
    if isinstance(metadata, str):
        try:
            import json
            metadata = json.loads(metadata)
        except:
            metadata = {}
    
    section = Section(
        section_id=section_data.get('section_id'),
        document_id=section_data.get('document_id'),
        heading=section_data.get('section_heading', ''),
        text=section_data.get('section_text', ''),
        chunk_type=section_data.get('chunk_type', 'unknown'),
        relevance_score=1.0,  # Direct retrieval
        metadata=metadata
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
    
    # Standardize response with top-level citations
    response_dict = response.dict()
    tool_name = "opa_get_section"
    return standardize_mcp_response(response_dict, tool_name)


@mcp.tool(name="opa_policy_check", description="CPSO-specific policy and advice retrieval")
async def policy_check_handler(
    topic: str,
    situation: Optional[str] = None,
    include_related: bool = True
) -> Dict[str, Any]:
    """
    CPSO-specific policy and advice retrieval.
    
    Args:
        topic: Clinical topic or practice area
        situation: Specific situation or context
        include_related: Include related policies
    
    Returns:
        Relevant policies, expectations, advice with confidence
    """
    logger.info(f"opa.policy_check called for topic: {topic}")
    logger.debug(f"Parameters: situation={situation}, include_related={include_related}")
    
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
            policy_level=None,  # Always search for both expectations and advice
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
    
    # Standardize response with top-level citations
    response_dict = response.dict()
    return standardize_mcp_response(response_dict, "opa_policy_check")


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
        
        # Standardize response with top-level citations
        response_dict = response.dict()
        tool_name = "opa_program_lookup"
        return standardize_mcp_response(response_dict, tool_name)
        
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
    
    # Standardize response with top-level citations
    response_dict = response.dict()
    tool_name = "opa_program_lookup"
    return standardize_mcp_response(response_dict, tool_name)


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
    
    # Standardize response with top-level citations
    response_dict = response.dict()
    tool_name = "opa_ipac_guidance"
    return standardize_mcp_response(response_dict, tool_name)


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
    
    # Standardize response with top-level citations
    response_dict = response.dict()
    tool_name = "opa_freshness_probe"
    return standardize_mcp_response(response_dict, tool_name)


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
    
    # Standardize response with top-level citations
    tool_name = "opa_clinical_tools"
    return standardize_mcp_response(response, tool_name)


@mcp.tool(name="opa_quality_standards", description="Ontario Health quality standards search")
async def quality_standards_handler(request: QualityStandardsRequest) -> Dict[str, Any]:
    """
    Search Ontario Health quality standards and retrieve quality statements.
    
    This tool searches the Ontario Health quality standards corpus for specific
    topics or conditions, and can retrieve all quality statements for a specific
    standard when requested.
    
    Args:
        request: QualityStandardsRequest with query and options
    
    Returns:
        Quality statements, standard information, and citations
    """
    logger.info(f"opa.quality_standards called - query: {request.query}")
    logger.info(f"  retrieve_all: {request.retrieve_all_statements}, type: {request.statement_type}")
    
    try:
        # Get semantic search engine
        semantic_search = get_semantic_search()
        
        # Step 1: Search for relevant quality standards
        search_results = await semantic_search.search(
            query=request.query,
            sources=['quality_standards'],
            document_types=['quality_standard_overview', 'quality_statement'] if request.statement_type == 'all' 
                         else ['quality_standard_overview'] if request.statement_type == 'overview'
                         else ['quality_statement'],
            top_k=request.top_k if not request.retrieve_all_statements else 50,
            use_reranking=True
        )
        
        logger.info(f"Search returned {len(search_results)} results")
        
        # Step 2: If retrieve_all_statements, find the best matching standard using LLM
        standard_title = None
        if request.retrieve_all_statements and search_results:
            # Collect all unique quality standard titles from results
            candidate_titles = []
            for result in search_results:
                if result.get('metadata', {}).get('chunk_type') == 'document':
                    title = result.get('metadata', {}).get('title', '')
                    if title and title not in candidate_titles:
                        candidate_titles.append(title)
            
            # Use LLM to match query to best standard title if we have candidates
            if candidate_titles:
                logger.info(f"Found {len(candidate_titles)} candidate standards: {candidate_titles[:5]}")
                
                # Use OpenAI to find best match
                try:
                    openai_client = semantic_search.openai_client
                    
                    prompt = f"""Given the user query and list of available Ontario Health Quality Standards, 
                    identify the BEST matching standard. Return ONLY the exact title from the list, nothing else.
                    
                    User Query: {request.query}
                    
                    Available Quality Standards:
                    {chr(10).join(f"- {title}" for title in candidate_titles[:10])}
                    
                    Return the exact title of the best matching standard:"""
                    
                    response = await openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a medical knowledge assistant that matches queries to quality standards."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0,
                        max_tokens=100
                    )
                    
                    matched_title = response.choices[0].message.content.strip()
                    
                    # Verify the matched title is in our list (LLM might hallucinate)
                    if matched_title in candidate_titles:
                        standard_title = matched_title
                        logger.info(f"LLM matched query '{request.query}' to standard: {standard_title}")
                    else:
                        # Fallback to first candidate if LLM response invalid
                        standard_title = candidate_titles[0]
                        logger.warning(f"LLM returned invalid title '{matched_title}', using first candidate: {standard_title}")
                        
                except Exception as e:
                    logger.error(f"LLM matching failed: {e}, falling back to first candidate")
                    standard_title = candidate_titles[0]
            
            # If we found a standard, get ALL its statements
            if standard_title:
                # Search again specifically for this standard's statements
                all_statements_results = await semantic_search.search(
                    query=standard_title,
                    sources=['quality_standards'],
                    document_types=['quality_statement'],
                    top_k=50,  # Get all statements
                    use_reranking=False  # Don't rerank when getting all
                )
                
                # Filter to only statements from this specific standard
                filtered_results = [
                    r for r in all_statements_results
                    if r.get('metadata', {}).get('title', '').lower() == standard_title.lower()
                ]
                
                logger.info(f"Found {len(filtered_results)} statements for {standard_title}")
                search_results = filtered_results
        
        # Step 3: Process results into quality statements
        statements = []
        executive_summary = None
        scope = None
        year = None
        citations_set = set()
        
        # If we didn't find a specific standard yet, try to identify from results
        if not standard_title and search_results:
            # Look for the most common title in results
            title_counts = {}
            for result in search_results:
                title = result.get('metadata', {}).get('title', '')
                if title:
                    title_counts[title] = title_counts.get(title, 0) + 1
            
            if title_counts:
                # Get the most common title
                standard_title = max(title_counts.items(), key=lambda x: x[1])[0]
                logger.info(f"Inferred standard from results: {standard_title}")
        
        for result in search_results:
            metadata = result.get('metadata', {})
            chunk_type = metadata.get('chunk_type', '')
            
            # Extract document-level information
            if chunk_type == 'document':
                text = result.get('text', '')
                # Extract executive summary
                if '## Executive Summary' in text:
                    start = text.find('## Executive Summary') + len('## Executive Summary')
                    end = text.find('\n##', start)
                    executive_summary = text[start:end if end != -1 else None].strip()
                
                # Extract scope
                if '## Scope' in text:
                    start = text.find('## Scope') + len('## Scope')
                    end = text.find('\n##', start)
                    scope = text[start:end if end != -1 else None].strip()
                
                year = metadata.get('year')
                
            # Extract statement information
            elif chunk_type == 'statement':
                stmt_num = metadata.get('statement_number', 0)
                stmt_title = metadata.get('statement_title', '')
                
                # Parse statement text
                text = result.get('text', '')
                brief = ""
                full = ""
                indicators = []
                for_patients = ""
                for_clinicians = ""
                
                # Extract brief statement
                if '## Statement' in text:
                    start = text.find('## Statement') + len('## Statement')
                    end = text.find('\n##', start)
                    brief = text[start:end if end != -1 else None].strip()
                
                # Extract full text (statement + background)
                if '## Background' in text:
                    start = text.find('## Background') + len('## Background')
                    end = text.find('\n##', start)
                    background = text[start:end if end != -1 else None].strip()
                    full = f"{brief}\n\nBackground:\n{background}" if brief else background
                else:
                    full = brief
                
                # Extract indicators
                if '## Quality Indicators' in text:
                    start = text.find('## Quality Indicators')
                    end = text.find('\n##', start)
                    indicators_text = text[start:end if end != -1 else None]
                    indicators = [line.strip('• ').strip() for line in indicators_text.split('\n') 
                                if line.strip().startswith('•')]
                
                # Extract patient info
                if '## For Patients' in text:
                    start = text.find('## For Patients') + len('## For Patients')
                    end = text.find('\n##', start)
                    for_patients = text[start:end if end != -1 else None].strip()
                
                # Extract clinician info
                if '## For Clinicians' in text:
                    start = text.find('## For Clinicians') + len('## For Clinicians')
                    end = text.find('\n##', start)
                    for_clinicians = text[start:end if end != -1 else None].strip()
                
                statement = QualityStatement(
                    statement_number=stmt_num,
                    title=stmt_title,
                    brief_statement=brief,
                    full_text=full if full != brief else None,
                    indicators=indicators,
                    for_patients=for_patients if for_patients else None,
                    for_clinicians=for_clinicians if for_clinicians else None
                )
                statements.append(statement)
            
            # Collect citations
            source_url = metadata.get('source_url', '')
            if source_url:
                citations_set.add((
                    metadata.get('title', 'Ontario Health Quality Standard'),
                    source_url,
                    'ontario_health'
                ))
        
        # Sort statements by number
        statements.sort(key=lambda s: s.statement_number)
        
        # Create citations list
        citations = [
            Citation(
                source=title,
                source_org='ontario_health',
                loc=f"Quality Standard",
                url=url
            )
            for title, url, org in citations_set
        ]
        
        # Calculate confidence
        confidence = 0.9 if statements else 0.3
        if request.retrieve_all_statements and standard_title:
            confidence = 0.95  # High confidence when we found specific standard
        
        # Create response
        response = QualityStandardsResponse(
            standard_title=standard_title,
            statements=statements,
            total_statements=len(statements),
            executive_summary=executive_summary,
            scope=scope,
            year=year,
            citations=citations,
            confidence=confidence
        )
        
        logger.info(f"Returning {len(statements)} quality statements")
        
        # Convert to dict and standardize
        response_dict = response.model_dump()
        return standardize_mcp_response(response_dict, "opa_quality_standards")
        
    except Exception as e:
        logger.error(f"Quality standards search failed: {e}")
        logger.error(traceback.format_exc())
        
        # Return error response
        return {
            'error': str(e),
            'standard_title': None,
            'statements': [],
            'total_statements': 0,
            'citations': [],
            'confidence': 0.0
        }


@mcp.tool(name="opa_choosing_wisely", description="Choosing Wisely recommendations for avoiding unnecessary tests and procedures")
async def choosing_wisely_handler(request: ChoosingWiselyRequest) -> Dict[str, Any]:
    """
    Search Choosing Wisely recommendations for unnecessary tests and procedures.
    
    This tool helps identify clinical scenarios where tests, procedures, or treatments
    may be unnecessary or overused according to Choosing Wisely Canada recommendations.
    
    Args:
        request: ChoosingWiselyRequest with query and options
    
    Returns:
        Choosing Wisely recommendations with specialty information and citations
    """
    logger.info(f"opa.choosing_wisely called - query: {request.query}")
    logger.info(f"  specialty: {request.specialty}, type: {request.recommendation_type}")
    
    try:
        # Get semantic search engine
        semantic_search = get_semantic_search()
        
        # Step 1: Map specialty if provided using LLM
        mapped_specialty = None
        if request.specialty:
            mapped_specialty = await _map_specialty_to_available(request.specialty, semantic_search)
            logger.info(f"Mapped specialty '{request.specialty}' to '{mapped_specialty}'")
        
        # Step 2: Build search query and filters
        search_query = request.query
        sources = ['choosing_wisely']
        
        # Document type filter based on recommendation_type
        document_types = None
        if request.recommendation_type == 'overview':
            document_types = ['choosing_wisely_overview']
        elif request.recommendation_type == 'recommendation':
            document_types = ['choosing_wisely_recommendation']
        # 'all' or None means search both types
        
        # Search for relevant recommendations
        search_results = await semantic_search.search(
            query=search_query,
            sources=sources,
            document_types=document_types,
            top_k=request.top_k if not mapped_specialty else 50,  # Get more if filtering by specialty
            use_reranking=True
        )
        
        logger.info(f"Search returned {len(search_results)} results")
        
        # Step 3: If specialty was mapped, filter results to that specialty
        if mapped_specialty:
            filtered_results = []
            for result in search_results:
                result_specialty = result.get('metadata', {}).get('specialty', '').lower()
                if mapped_specialty.lower() in result_specialty or result_specialty in mapped_specialty.lower():
                    filtered_results.append(result)
            
            search_results = filtered_results
            logger.info(f"Filtered to {len(search_results)} results for specialty '{mapped_specialty}'")
        
        # Step 4: Process results into recommendations
        recommendations = []
        specialty_overview = None
        organization = None
        last_updated = None
        citations_set = set()
        
        # Track the most common specialty in results
        specialty_counts = {}
        
        for result in search_results:
            metadata = result.get('metadata', {})
            chunk_type = metadata.get('chunk_type', '')
            
            # Extract specialty-level information from overview chunks
            if chunk_type == 'specialty_overview':
                specialty = metadata.get('specialty', '')
                text = result.get('text', '')
                
                if not specialty_overview and text:
                    specialty_overview = text[:500] + "..." if len(text) > 500 else text
                    organization = metadata.get('organization', '')
                    last_updated = metadata.get('last_updated', '')
                
                # Count specialty occurrences
                if specialty:
                    specialty_counts[specialty] = specialty_counts.get(specialty, 0) + 1
                
            # Extract recommendation information
            elif chunk_type == 'recommendation':
                rec_num = metadata.get('recommendation_number', 0)
                rec_title = metadata.get('recommendation_title', '')
                specialty = metadata.get('specialty', '')
                org = metadata.get('organization', '')
                
                # Count specialty occurrences
                if specialty:
                    specialty_counts[specialty] = specialty_counts.get(specialty, 0) + 1
                
                # Parse recommendation text
                text = result.get('text', '')
                
                # Extract title and description
                title = rec_title if rec_title else "Recommendation"
                description = ""
                references = []
                
                # Try to parse structured text
                if "Recommendation #" in text:
                    lines = text.split('\n')
                    description_lines = []
                    in_references = False
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('Recommendation #'):
                            # Extract title from this line
                            if ':' in line:
                                title = line.split(':', 1)[1].strip()
                        elif line.startswith('References:') or line == 'References:':
                            in_references = True
                        elif in_references and line.startswith('-'):
                            references.append(line[1:].strip())
                        elif not in_references and line and not line.startswith('='):
                            description_lines.append(line)
                    
                    description = '\n'.join(description_lines).strip()
                else:
                    # Fallback - use first 300 chars as description
                    description = text[:300] + "..." if len(text) > 300 else text
                
                recommendation = ChoosingWiselyRecommendation(
                    recommendation_number=rec_num,
                    title=title,
                    description=description,
                    specialty=specialty,
                    organization=org,
                    references=references
                )
                recommendations.append(recommendation)
            
            # Collect citations
            source_url = metadata.get('source_url', '')
            if source_url:
                citations_set.add((
                    metadata.get('specialty', 'Choosing Wisely Canada'),
                    source_url,
                    'choosing_wisely_canada'
                ))
        
        # Determine the primary specialty from results
        primary_specialty = None
        if specialty_counts:
            primary_specialty = max(specialty_counts.items(), key=lambda x: x[1])[0]
        elif mapped_specialty:
            primary_specialty = mapped_specialty
        
        # Sort recommendations by number
        recommendations.sort(key=lambda r: r.recommendation_number)
        
        # Create citations list
        citations = [
            Citation(
                source=title,
                source_org='choosing_wisely_canada',
                loc=f"Choosing Wisely Recommendations",
                url=url
            )
            for title, url, org in citations_set
        ]
        
        # Calculate confidence
        confidence = 0.9 if recommendations else 0.3
        if mapped_specialty and primary_specialty:
            confidence = 0.95  # High confidence when specialty matched
        
        # Create query interpretation
        query_interpretation = f"Searching for unnecessary care recommendations"
        if primary_specialty:
            query_interpretation += f" in {primary_specialty}"
        if mapped_specialty and mapped_specialty != primary_specialty:
            query_interpretation += f" (mapped from '{request.specialty}')"
        
        # Create response
        response = ChoosingWiselyResponse(
            specialty_title=primary_specialty,
            recommendations=recommendations,
            total_recommendations=len(recommendations),
            specialty_overview=specialty_overview,
            organization=organization,
            last_updated=last_updated,
            citations=citations,
            confidence=confidence,
            query_interpretation=query_interpretation
        )
        
        logger.info(f"Returning {len(recommendations)} Choosing Wisely recommendations")
        
        # Convert to dict and standardize
        response_dict = response.model_dump()
        return standardize_mcp_response(response_dict, "opa_choosing_wisely")
        
    except Exception as e:
        logger.error(f"Choosing Wisely search failed: {e}")
        logger.error(traceback.format_exc())
        
        # Return error response
        return {
            'error': str(e),
            'specialty_title': None,
            'recommendations': [],
            'total_recommendations': 0,
            'citations': [],
            'confidence': 0.0
        }


async def _map_specialty_to_available(specialty_input: str, semantic_search) -> Optional[str]:
    """Map user input specialty to one of our available specialties using LLM."""
    
    # First get list of available specialties from our data
    AVAILABLE_SPECIALTIES = [
        "Allergy and Clinical Immunology", "Anesthesiology", "Blood and Marrow Transplant",
        "Burns", "Cardiology", "Critical Care", "Dermatology", "Emergency Medicine",
        "Endocrinology and Metabolism", "Family Medicine", "Fertility and Andrology",
        "Gastroenterology", "General Surgery", "Geriatrics", "Headache", "Hematology",
        "Hepatology", "Hospital Dentistry", "Hospital Medicine", "Hospital Pharmacy",
        "Infectious Disease", "Internal Medicine", "Long-term Care", "Medical Biochemistry",
        "Medical Education: Residents", "Medical Education: Students", "Medical Genetics",
        "Medical Laboratory Science", "Medical Microbiology", "Medical Radiation Technology",
        "Nephrology", "Neurology", "Nuclear Medicine", "Nurse Practitioner", "Nursing",
        "Nursing: Critical Care", "Nursing: Gerontology", "Nursing: Infection Prevention and Control",
        "Obstetrics and Gynaecology", "Occupational Medicine", "Oncology", "Orthopaedics",
        "Otolaryngology: Head and Neck Surgery", "Otolaryngology: Otology and Neurotology",
        "Otolaryngology: Rhinology", "Paediatric Surgery", "Paediatrics", "Palliative Care",
        "Pathology", "Pediatric Infectious Diseases and Medical Microbiology", "Pediatric Neurosurgery",
        "Pediatric Otolaryngology", "Pediatric Rheumatology", "Pediatric Sport and Exercise Medicine",
        "Pediatrics", "Perinatal Transfusion Medicine", "Pharmacist", "Physical Medicine and Rehabilitation",
        "Psychiatry", "Public Health", "Radiology", "Respiratory Medicine", "Rheumatology",
        "Rural Medicine", "Spine", "Sport and Exercise Medicine", "Transfusion Medicine",
        "Trauma", "Urology", "Vascular Surgery"
    ]
    
    # Quick exact match first
    specialty_lower = specialty_input.lower()
    for available in AVAILABLE_SPECIALTIES:
        if specialty_lower == available.lower():
            return available
    
    # Check for partial matches
    for available in AVAILABLE_SPECIALTIES:
        if specialty_lower in available.lower() or available.lower() in specialty_lower:
            return available
    
    # Use LLM for fuzzy matching
    try:
        openai_client = semantic_search.openai_client
        
        prompt = f"""Given the user's specialty input and list of available Choosing Wisely specialties, 
        identify the BEST matching specialty. Return ONLY the exact specialty name from the list, nothing else.
        If no good match exists, return "None".
        
        User Input: {specialty_input}
        
        Available Specialties:
        {chr(10).join(f"- {spec}" for spec in AVAILABLE_SPECIALTIES)}
        
        Return the exact specialty name that best matches the user input:"""
        
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a medical specialty mapping assistant that matches user input to available specialties."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=50
        )
        
        matched_specialty = response.choices[0].message.content.strip()
        
        # Verify the matched specialty is in our list
        if matched_specialty in AVAILABLE_SPECIALTIES:
            return matched_specialty
        elif matched_specialty.lower() == "none":
            return None
        else:
            # LLM returned something not in our list, try partial match
            for available in AVAILABLE_SPECIALTIES:
                if matched_specialty.lower() in available.lower():
                    return available
            
            return None
        
    except Exception as e:
        logger.error(f"LLM specialty mapping failed: {e}")
        return None


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
    logger.info("  - opa.quality_standards: Ontario Health quality standards search")
    logger.info("  - opa.choosing_wisely: Choosing Wisely recommendations for avoiding unnecessary care")
    
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