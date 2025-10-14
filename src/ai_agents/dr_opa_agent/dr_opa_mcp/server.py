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

# Import triage classifiers
from .search.cep_triage import classify_cep_query_cached, get_tool_url
from .search.qs_triage import classify_quality_standards_query_cached
from .search.choosing_wisely_triage import classify_choosing_wisely_query_cached

# Import Ontario Health Programs tool
from .tools.ontario_health_programs import get_client as get_ontario_health_client

# Import PHO web search client
from .tools.pho_web_search import PHOWebSearchClient

# Import utilities
from .utils import calculate_confidence, resolve_conflicts
from .utils.confidence import OPAConfidenceScorer
from .utils.conflicts import OPAConflictResolver
from .utils.response_formatter import standardize_mcp_response

# Import models
from .models.request import StandardToolRequest

# Add missing import
import sqlite3
from openai import AsyncOpenAI

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

# Load CEP Tool Catalog for two-tier retrieval
CEP_TOOL_CATALOG_FILE = Path(__file__).parent / "cep_tool_catalog.json"
CEP_TOOL_CATALOG = []

try:
    if CEP_TOOL_CATALOG_FILE.exists():
        with open(CEP_TOOL_CATALOG_FILE, 'r') as f:
            CEP_TOOL_CATALOG = json.load(f)
        logger.info(f"Loaded {len(CEP_TOOL_CATALOG)} tools from CEP catalog")
    else:
        logger.warning(f"CEP tool catalog not found at {CEP_TOOL_CATALOG_FILE}")
except Exception as e:
    logger.error(f"Failed to load CEP tool catalog: {e}")

# Initialize shared clients (lazy loading)
_sql_client = None
_vector_client = None
_semantic_search = None
_openai_client = None


# SQL client removed - all tools use semantic search only
# def get_sql_client() -> SQLClient:
#     """Get or create SQL client singleton."""
#     global _sql_client
#     if _sql_client is None:
#         try:
#             logger.info("Initializing SQL client...")
#             _sql_client = SQLClient()
#             logger.info("SQL client initialized successfully")
#         except Exception as e:
#             logger.error(f"Failed to initialize SQL client: {e}")
#             logger.error(traceback.format_exc())
#             raise
#     return _sql_client


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


def get_openai_client() -> AsyncOpenAI:
    """Get or create OpenAI client singleton."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _openai_client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI client initialized")
    return _openai_client


@mcp.tool(name="opa_search_sections", description="Hybrid search across OPA knowledge corpus")
async def search_sections_handler(query: str, k: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Hybrid search across OPA practice guidance corpus.
    Combines SQL full-text search and vector semantic search.

    Args:
        query: Clinical query or practice question
        k: Number of results to return (default 10)
        filters: Optional dict with:
            - sources: List of sources to search (e.g., ["pho", "cpso"])
            - doc_types: Document types to include (e.g., ["guideline"])
            - topics: Topics to filter by (e.g., ["infection_prevention"])
            - date_range: Date range filter (dict with 'start' and 'end')
            - include_superseded: Include superseded documents (bool)

    Returns:
        Matching sections with documents, highlights, and confidence
    """
    # Extract sources filter only (other filters are passthrough/ignored)
    filters = filters or {}
    sources = filters.get('sources')
    doc_types = filters.get('doc_types', [])

    logger.info(f"opa.search_sections called with query: {query[:100] if query else 'None'}...")
    logger.debug(f"Parameters: sources={sources}, k={k}")
    
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
    
    # Use the new semantic search engine with hybrid mode
    try:
        search_results = await semantic_search.search(
            query=query,
            sources=sources,
            k=k,
            use_reranking=True,  # Enable LLM reranking (CE disabled)
            use_hybrid=False,  # Disable hybrid (Issue #2 showed no improvement)
            use_ce_reranking=False  # Disable cross-encoder, use LLM reranking instead
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
        # Create section (Option A minimal schema)
        raw_score = data.get('relevance_score', 0.8)
        # Normalize LLM reranker score (0-10) to 0-1 range
        normalized_score = raw_score / 10.0 if raw_score > 1.0 else raw_score

        section = Section(
            id=data.get('document_id', ''),
            text=data.get('text', '')[:500],  # Truncate for response
            relevance_score=normalized_score,
            source=data.get('document_id', ''),
            metadata={
                'chunk_type': data.get('chunk_type', 'unknown'),
                'section_id': data.get('section_id', data.get('chunk_id', '')),
                'document_id': data.get('document_id', ''),
                'section_heading': data.get('section_heading', ''),
                'document_title': data.get('document_title', data.get('title', '')),
                'source_org': data.get('source_org', ''),
                'document_type': data.get('document_type', ''),
                'effective_date': data.get('effective_date'),
                'topics': data.get('topics', []),
                'source_url': data.get('source_url'),
                'is_superseded': data.get('is_superseded', False),
                **data.get('metadata', {})  # Include any additional metadata
            }
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
                source=section.metadata.get('document_title', 'Unknown'),
                source_org=section.metadata.get('source_org', ''),
                loc=section.metadata.get('section_heading', ''),
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
        items=sections[:k],
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


# Tool disabled - requires SQL database (opa.db) which is deprecated
# @mcp.tool(name="opa_get_section", description="Retrieve complete section details by ID")
async def get_section_handler_DISABLED(
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
    
    # Create section object (Option A minimal schema)
    # Parse metadata_json if it's a string
    metadata_json = section_data.get('metadata_json', {})
    if isinstance(metadata_json, str):
        try:
            import json
            metadata_json = json.loads(metadata_json)
        except:
            metadata_json = {}

    section = Section(
        id=section_data.get('section_id', ''),
        text=section_data.get('section_text', ''),
        relevance_score=1.0,  # Direct retrieval
        source=section_data.get('document_id', ''),
        metadata={
            'chunk_type': section_data.get('chunk_type', 'unknown'),
            'section_id': section_data.get('section_id', ''),
            'document_id': section_data.get('document_id', ''),
            'section_heading': section_data.get('section_heading', ''),
            'document_title': section_data.get('document_title', ''),
            'source_org': section_data.get('source_org', ''),
            'document_type': section_data.get('document_type', ''),
            'effective_date': section_data.get('effective_date'),
            'topics': section_data.get('topics', []),
            'source_url': section_data.get('source_url'),
            'is_superseded': False,
            **metadata_json  # Include any additional metadata
        }
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
    
    # Process children if included (Option A minimal schema)
    children = []
    if include_children and section_data.get('children'):
        for child_data in section_data['children']:
            children.append(Section(
                id=child_data.get('section_id', ''),
                text=child_data.get('section_text', ''),
                relevance_score=1.0,
                source=child_data.get('document_id', ''),
                metadata={
                    'chunk_type': 'child',
                    'section_id': child_data.get('section_id', ''),
                    'document_id': child_data.get('document_id', ''),
                    'section_heading': child_data.get('section_heading', '')
                }
            ))

    # Process context if included (Option A minimal schema)
    context = []
    if include_context and section_data.get('context'):
        for ctx_data in section_data['context']:
            context.append(Section(
                id=ctx_data.get('section_id', ''),
                text='',  # Don't include full text for context
                relevance_score=0.8,
                source=section_data.get('document_id', ''),
                metadata={
                    'chunk_type': 'context',
                    'section_id': ctx_data.get('section_id', ''),
                    'document_id': section_data.get('document_id', ''),
                    'section_heading': ctx_data.get('section_heading', ''),
                    'section_idx': ctx_data.get('section_idx')
                }
            ))
    
    # Create citations
    citations = [Citation(
        source=document.title,
        source_org=document.source_org,
        loc=section.metadata.get('section_heading', ''),
        url=document.url
    )]
    
    # Create response (consolidate section, children, context into items list)
    items = [section] + children + context
    response = GetSectionResponse(
        items=items,
        document=document,
        citations=citations
    )
    
    # Standardize response with top-level citations
    response_dict = response.dict()
    tool_name = "opa_get_section"
    return standardize_mcp_response(response_dict, tool_name)


@mcp.tool(name="opa_policy_check", description="CPSO-specific policy and advice retrieval with two-tier architecture")
async def policy_check_handler(query: str, k: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    CPSO-specific policy and advice retrieval with two-tier architecture.

    Tier 1: LLM classifies query and identifies relevant policies
    Tier 2: Retrieval scoped to those policies only

    Args:
        query: Clinical topic or practice area
        k: Number of results to return (default 10)
        filters: Optional dict with:
            - policy_scope: Manual policy ID override (List[str])
            - policy_level: CPSO policy level ("expectation", "advice", "both")
            - intent: Manual intent override ("policy_discovery" | "specific_requirement")
            - include_related: Include related policies (bool)

    Returns:
        Relevant policies, expectations, advice with confidence
    """
    # Extract filters
    filters = filters or {}
    policy_scope = filters.get('policy_scope')  # Manual override
    policy_level = filters.get('policy_level')
    intent = filters.get('intent')
    include_related = filters.get('include_related', False)

    logger.info(f"opa.policy_check called for query: {query}")
    logger.debug(f"Parameters: k={k}, policy_scope={policy_scope}, intent={intent}")

    try:
        semantic_search = get_semantic_search()
    except Exception as e:
        logger.error(f"Failed to get semantic search engine: {e}")
        return PolicyCheckResponse(
            items=[],
            confidence=0.6,
            summary=f"CPSO Guidance for '{query}': No specific CPSO guidance found for this topic"
        ).dict()

    # STEP 1: Classify query (unless overridden)
    if policy_scope and intent:
        classification = {
            "intent": intent,
            "relevant_policies": policy_scope,
            "policy_level_focus": policy_level or "both",
            "confidence": 1.0,
            "reasoning": "Manual override"
        }
        logger.info("Using manual policy scope override")
    else:
        from .search.cpso_triage import classify_cpso_query_cached

        # Get OpenAI client from semantic search
        openai_client = semantic_search.openai_client

        classification = await classify_cpso_query_cached(query, openai_client)
        logger.info(f"Policy triage: {classification['intent']}, {len(classification.get('relevant_policies', []))} policies")

    # STEP 1.5: Check if no relevant policies found - compute fallback suggestions
    if not classification.get("relevant_policies") or len(classification.get("relevant_policies", [])) == 0:
        logger.info("No exact policy matches found, computing semantic fallback suggestions")

        from .search.cpso_triage import load_policy_catalog
        from .utils.catalog_fallback import (
            compute_catalog_similarity,
            format_suggestions_response
        )

        try:
            catalog = load_policy_catalog()

            suggestions = await compute_catalog_similarity(
                query=query,
                catalog=catalog,
                openai_client=openai_client,
                catalog_type="cpso_policies",
                top_k=3,
                min_similarity=0.40
            )

            if suggestions:
                suggestion_text = format_suggestions_response(
                    query=query,
                    suggestions=suggestions,
                    catalog_type="cpso_policies"
                )

                return PolicyCheckResponse(
                    items=[],
                    confidence=0.5,
                    summary=suggestion_text,
                    suggestions=suggestions,
                    no_exact_match=True
                ).dict()
            else:
                return PolicyCheckResponse(
                    items=[],
                    confidence=0.3,
                    summary=f"No CPSO policies found for: {query}",
                    no_exact_match=True
                ).dict()
        except Exception as e:
            logger.error(f"Fallback computation failed: {e}", exc_info=True)
            return PolicyCheckResponse(
                items=[],
                confidence=0.3,
                summary=f"No CPSO policies found for: {query}",
                no_exact_match=True
            ).dict()

    # STEP 2: Retrieve chunks scoped to relevant policies
    from .search.cpso_helpers import (
        retrieve_policy_overviews,
        retrieve_detailed_chunks,
        format_policy_response
    )

    try:
        # Check for catalog/"all" queries - return catalog directly instead of retrieval
        if classification.get("scope") == "all":
            logger.info("Scope is 'all' - returning full policy catalog instead of retrieval")
            from .search.cpso_triage import load_policy_catalog

            catalog = load_policy_catalog()

            # Convert catalog to Section objects
            policies_data = []
            for policy in catalog:
                # Create a brief overview from catalog metadata
                overview_text = f"{policy['policy_title']}\n\n"
                overview_text += f"Policy Level: {policy['policy_level'].title()}\n"
                overview_text += f"Practice Domain: {policy['practice_domain'].replace('_', ' ').title()}\n"

                if policy.get('topics'):
                    overview_text += f"Topics: {', '.join(policy['topics'][:5])}\n"

                if policy.get('key_requirements'):
                    overview_text += f"\nKey Requirements:\n"
                    for req in policy['key_requirements'][:3]:
                        overview_text += f"- {req}\n"

                overview_text += f"\nSource: {policy['source_url']}"

                # Create a Section-like dict
                policies_data.append({
                    'document_id': policy['policy_id'],
                    'text': overview_text,
                    'relevance_score': 0.9,  # All policies equally relevant for catalog queries
                    'document_title': policy['policy_title'],
                    'policy_level': policy['policy_level'],
                    'source_url': policy['source_url'],
                    'topics': policy.get('topics', []),
                    'source_org': 'cpso',
                    'document_type': 'policy',
                    'effective_date': policy.get('effective_date'),
                    'section_heading': 'Policy Overview',
                    'section_id': f"{policy['policy_id']}_overview"
                })

            logger.info(f"Returning all {len(policies_data)} policies from catalog")

        elif classification["intent"] == "policy_discovery":
            # Get policy overviews
            logger.info("Using policy discovery mode (overviews)")
            policies_data = await retrieve_policy_overviews(
                semantic_search=semantic_search,
                query=query,
                policy_ids=classification["relevant_policies"],
                k=min(k, len(classification["relevant_policies"]) * 2)
            )
        else:
            # Get detailed chunks + parent context
            logger.info("Using specific requirement mode (detailed)")
            policies_data = await retrieve_detailed_chunks(
                semantic_search=semantic_search,
                query=query,
                policy_ids=classification["relevant_policies"],
                policy_level=classification.get("policy_level_focus"),
                k=k
            )

        logger.info(f"Retrieved {len(policies_data)} chunks")

    except Exception as e:
        logger.error(f"Policy retrieval failed: {e}")
        logger.error(traceback.format_exc())
        policies_data = []
    
    # Convert results to Section objects (Option A minimal schema)
    items = []
    expectation_count = 0
    advice_count = 0

    for policy_data in policies_data:
        # Determine chunk_type from policy_level
        policy_level = policy_data.get('policy_level', 'policy_document')
        if policy_level == 'expectation':
            chunk_type = 'expectation'
            expectation_count += 1
        elif policy_level == 'advice':
            chunk_type = 'advice'
            advice_count += 1
        else:
            chunk_type = 'policy_document'

        # Create Section object with all domain-specific fields in metadata
        raw_score = policy_data.get('relevance_score', 0.8)
        # Normalize LLM reranker score (0-10) to 0-1 range
        normalized_score = raw_score / 10.0 if raw_score > 1.0 else raw_score

        section = Section(
            id=policy_data.get('document_id', ''),
            text=policy_data.get('text', ''),
            relevance_score=normalized_score,
            source=policy_data.get('document_id', ''),
            metadata={
                'chunk_type': chunk_type,
                'policy_level': policy_level,
                'section_id': policy_data.get('section_id', ''),
                'document_id': policy_data.get('document_id', ''),
                'document_title': policy_data.get('document_title') or policy_data.get('title', ''),
                'section_heading': policy_data.get('section_heading', ''),
                'source_org': policy_data.get('source_org', 'cpso'),
                'document_type': policy_data.get('document_type', ''),
                'effective_date': policy_data.get('effective_date'),
                'topics': policy_data.get('topics', []),
                'source_url': policy_data.get('source_url'),
                'is_superseded': False
            }
        )
        items.append(section)

    # Find related documents if requested
    if include_related and items:
        # Get topics from main results
        all_topics = set()
        for item in items:
            all_topics.update(item.metadata.get('topics', []))

        # SQL-based related search removed - semantic search already provides comprehensive results
        # for related_topic in list(all_topics)[:3]:  # Limit to 3 topics
        #     try:
        #         related_data = await get_sql_client().search_policies(...)
        pass
    
    # RELEVANCE THRESHOLD FILTERING
    MIN_RELEVANCE = 0.4
    filtered_items = []
    relevance_scores = []

    for policy_data in policies_data:
        raw_score = policy_data.get('relevance_score', 0.8)
        # Normalize LLM reranker score (0-10) to 0-1 range
        normalized_score = raw_score / 10.0 if raw_score > 1.0 else raw_score

        if normalized_score >= MIN_RELEVANCE:
            filtered_items.append(policy_data)
            relevance_scores.append(normalized_score)
        else:
            logger.debug(f"Filtered out low-relevance result (score={normalized_score:.2f}): {policy_data.get('document_title', 'unknown')}")

    # Check if filtering removed all results
    if not filtered_items and policies_data:
        avg_score = sum(p.get('relevance_score', 0) / 10.0 if p.get('relevance_score', 0) > 1.0 else p.get('relevance_score', 0) for p in policies_data) / len(policies_data)
        logger.warning(f"All {len(policies_data)} results filtered out. Avg relevance: {avg_score:.2f}")

        # Return "no results" with cross-tool suggestions
        disease_keywords = ['diabetes', 'hypertension', 'copd', 'asthma', 'cancer', 'cardiac', 'kidney', 'stroke', 'mental health']
        if any(kw in query.lower() for kw in disease_keywords):
            return PolicyCheckResponse(
                items=[],
                confidence=0.3,
                summary=f"No specific CPSO guidance found for '{query}'. For disease-specific guidance, try: opa_quality_standards, opa_clinical_tools, or opa_program_lookup",
                no_exact_match=True,
                suggestions=[
                    {"tool": "opa_quality_standards", "reason": "Ontario Health quality standards for disease management"},
                    {"tool": "opa_clinical_tools", "reason": "CEP clinical decision support tools"},
                    {"tool": "opa_program_lookup", "reason": "Ontario Health disease-specific programs"}
                ]
            ).dict()
        else:
            return PolicyCheckResponse(
                items=[],
                confidence=0.3,
                summary=f"No relevant CPSO policies found for '{query}' (all results below relevance threshold of {MIN_RELEVANCE})",
                no_exact_match=True
            ).dict()

    # Use filtered results
    policies_data = filtered_items

    # Calculate confidence (incorporate triage confidence AND retrieval quality)
    triage_confidence = classification.get('confidence', 0.8)

    # Retrieval quality based on actual relevance scores
    if relevance_scores:
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        retrieval_quality = avg_relevance  # Direct score from reranker
    else:
        retrieval_quality = 0.0

    # Weighted confidence: 30% triage, 70% retrieval quality
    confidence = (triage_confidence * 0.3) + (retrieval_quality * 0.7)

    # Create summary with policy context
    from .search.cpso_triage import get_policy_info

    policy_context = []
    for policy_id in classification.get('relevant_policies', [])[:5]:  # Max 5
        policy_info = get_policy_info(policy_id)
        if policy_info:
            policy_context.append(f"{policy_info['policy_title']}")

    summary_parts = []

    # Add intent-specific context
    if classification["intent"] == "policy_discovery":
        summary_parts.append(f"Found {len(classification.get('relevant_policies', []))} relevant policies")
        if policy_context:
            summary_parts.append(f"Policies: {', '.join(policy_context[:3])}")
    else:
        if expectation_count > 0:
            summary_parts.append(f"Found {expectation_count} mandatory expectation(s)")
        if advice_count > 0:
            summary_parts.append(f"Found {advice_count} professional advice item(s)")

    if not summary_parts:
        summary_parts.append("No specific CPSO guidance found for this topic")

    summary = f"CPSO Guidance for '{query}': " + "; ".join(summary_parts)

    # STEP 3: CONDITIONAL DECISIONAL SYNTHESIS (NEW)
    if classification.get('is_decisional', False):
        logger.info("Decisional query detected - synthesizing compliance answer")

        from .search.cpso_helpers import synthesize_compliance_answer

        try:
            decisional_answer = await synthesize_compliance_answer(
                query=query,
                classification=classification,
                retrieved_chunks=policies_data,
                llm_client=semantic_search.openai_client
            )

            # Return decisional format with structured answer + supporting evidence
            return {
                'decisional_answer': decisional_answer,
                'supporting_evidence': items,  # Full Section objects for transparency
                'classification': {
                    'intent': classification['intent'],
                    'query_type': classification.get('query_type', 'compliance_check'),
                    'relevant_policies': classification.get('relevant_policies', []),
                    'is_decisional': True,
                    'confidence': classification.get('confidence', 0.8)
                },
                'response_type': 'decisional',
                'query_interpretation': f"Compliance check for: {query}",
                'summary': summary,
                # Add top-level fields for test framework compatibility
                'confidence': decisional_answer.get('confidence', 0.8),
                'citations': [{'source_url': item.metadata.get('source_url', ''),
                               'title': item.metadata.get('document_title', '')}
                              for item in items if item.metadata.get('source_url')],
                'items': items  # Include for backwards compatibility
            }

        except Exception as e:
            logger.error(f"Decisional synthesis failed: {e}", exc_info=True)
            # Fall through to standard informational response
            logger.info("Falling back to informational response due to synthesis error")

    # Create response with classification metadata (informational query path)
    response = PolicyCheckResponse(
        items=items,
        confidence=confidence,
        summary=summary
    )

    # Standardize response with top-level citations
    response_dict = response.dict()

    # Add two-tier classification metadata to response
    response_dict['classification'] = {
        'intent': classification.get('intent'),
        'relevant_policies': classification.get('relevant_policies', []),
        'policy_level_focus': classification.get('policy_level_focus'),
        'triage_confidence': triage_confidence,
        'reasoning': classification.get('reasoning')
    }
    response_dict['tools_searched'] = classification.get('relevant_policies', [])

    return standardize_mcp_response(response_dict, "opa_policy_check")


@mcp.tool(name="opa_program_lookup", description="Ontario Health clinical programs information (cancer, kidney, cardiac, etc.)")
async def program_lookup_handler(query: str, k: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Ontario Health clinical programs information lookup using Claude with web search.
    Covers all Ontario Health programs including cancer care, kidney care, cardiac,
    stroke, mental health, palliative care, and more.

    Args:
        query: Clinical program name (e.g., "cancer screening", "kidney care")
        k: Number of results to return (default 10)
        filters: Optional dict with:
            - patient_age: Patient age for eligibility (int)
            - risk_factors: Patient risk factors (list of strings)
            - info_needed: Information types to retrieve (list of strings)

    Returns:
        Program information including eligibility, procedures, locations, and resources
    """
    # Handle default filters
    filters = filters or {}
    program = query
    patient_age = filters.get('patient_age')
    risk_factors = filters.get('risk_factors')
    info_needed = filters.get('info_needed')

    logger.info(f"opa.program_lookup called for program: {program}")
    logger.debug(f"Parameters: age={patient_age}, risk_factors={risk_factors}, info_needed={info_needed}, k={k}")
    
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

        # Convert web_search citations to Section objects (Option A minimal schema)
        items = []
        # Get the full raw_response text once for all items
        raw_text = program_info.get("raw_response", "")
        # Use the raw response if available, otherwise try overview, otherwise use fallback message
        section_text = raw_text if raw_text else program_info.get("overview", "Program information retrieved from Ontario Health")

        for idx, cit in enumerate(citations[:10]):  # Up to 10 web sources

            section = Section(
                id=f"web_source_{idx}_{program.replace(' ', '_')}",
                text=section_text,
                relevance_score=0.9,  # High relevance for web search results
                source=cit.get("url", ""),
                metadata={
                    "chunk_type": "web_search_result",
                    "title": cit.get("title", "Ontario Health"),
                    "url": cit.get("url", ""),
                    "program": program,
                    "source_org": "ontario_health",
                    "document_type": "program_information"
                }
            )
            items.append(section)

        # Create response
        response = ProgramLookupResponse(
            items=items,
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
        # SQL fallback removed - semantic search is the only retrieval method
        # try:
        #     logger.info("Attempting fallback to SQL client for screening programs")
        #     sql_client = get_sql_client()
        #     program_data = await sql_client.get_program_info(program)
        #     if program_data:
        #         return _parse_screening_program_data(program_data, program, patient_age, risk_factors)
        # except Exception as sql_error:
        #     logger.error(f"SQL fallback also failed: {sql_error}")
        pass
        
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

    # Convert sections to Section objects (Option A minimal schema)
    items = []
    for idx, section in enumerate(program_data.get('sections', [])[:10]):  # Up to 10 sections
        section_obj = Section(
            id=f"sql_section_{idx}_{program.replace(' ', '_')}",
            text=section.get('text', '')[:500],  # Truncate to 500 chars
            relevance_score=0.8,  # Database retrieval
            source=section.get('document_id', 'ontario_health_database'),
            metadata={
                "chunk_type": "database_section",
                "heading": section.get('heading', ''),
                "program": program,
                "source_org": "ontario_health",
                "document_type": "screening_program"
            }
        )
        items.append(section_obj)

    response = ProgramLookupResponse(
        items=items,
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


@mcp.tool(name="opa_ipac_guidance", description="PHO IPAC guidance (indexed corpus + current web search)")
async def ipac_guidance_handler(query: str, k: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    PHO infection prevention and control guidance.
    Searches BOTH indexed corpus (2013 IPAC PDF) AND current PHO website for comprehensive results.

    Args:
        query: IPAC topic or question
        k: Number of results to return (default 10)
        filters: Optional dict with:
            - setting: Healthcare setting ("clinic", "hospital", "community", "ltc")
            - pathogen: Specific pathogen if applicable (string)
            - include_checklists: Include practical checklists (bool)
            - search_web: Include web search for current guidance (default True)

    Returns:
        IPAC guidelines, procedures, checklists, and resources from both indexed and current sources
    """
    # Handle default filters
    filters = filters or {}
    topic = query
    setting = filters.get('setting', '')
    pathogen = filters.get('pathogen')
    include_checklists = filters.get('include_checklists', True)
    search_web = filters.get('search_web', True)

    logger.info(f"opa.ipac_guidance called for setting={setting}, topic={topic}, search_web={search_web}")

    # Build search query
    search_query = topic
    if setting:
        search_query = f"{setting} {topic}"
    if pathogen:
        search_query += f" {pathogen}"

    logger.info(f"IPAC guidance search: '{search_query}'")

    # PART 1: Search indexed corpus (2013 IPAC PDF)
    semantic_search = get_semantic_search()
    formatted_results = []

    try:
        search_results = await semantic_search.search(
            query=search_query,
            sources=['pho'],  # Focus on PHO for IPAC
            k=k * 2,  # Get more for processing
            use_reranking=True,  # Enable LLM reranking (CE disabled)
            use_hybrid=False,  # Disable hybrid (Issue #2 showed no improvement)
            use_ce_reranking=False  # Disable cross-encoder, use LLM reranking instead
        )

        # Format results
        formatted_results = semantic_search.format_results(search_results)
        logger.info(f"Indexed corpus search returned {len(formatted_results)} IPAC results")

    except Exception as e:
        logger.error(f"Indexed corpus search failed: {e}")
        logger.error(traceback.format_exc())

    # PART 2: Web search for current PHO guidance
    web_summary = None
    web_links = []

    if search_web:
        try:
            logger.info("Searching current PHO website for guidance...")
            pho_client = PHOWebSearchClient()

            # Prepare subtopics and setting for web search
            subtopics = [pathogen] if pathogen else None

            web_results = pho_client.search_pho_guidance(
                topic=topic,
                subtopics=subtopics,
                clinical_setting=setting,
                resource_type=None
            )

            if web_results.get('success'):
                web_summary = web_results.get('search_summary', '')
                web_links = web_results.get('links', [])
                logger.info(f"Web search returned summary and {len(web_links)} PHO links")
            else:
                logger.warning(f"Web search failed: {web_results.get('error')}")

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            logger.error(traceback.format_exc())

    # Convert formatted_results to Section objects (Option A minimal schema)
    items = []
    for idx, result in enumerate(formatted_results):
        # Normalize relevance_score to 0-1 range (might be distance-based or other scale)
        raw_score = result.get('relevance_score', 0.0)
        relevance_score = min(max(raw_score, 0.0), 1.0) if raw_score <= 10 else (1.0 / (1.0 + raw_score))

        section = Section(
            id=result.get('document_id', '') + f"_section_{idx}",
            text=result.get('text', ''),
            relevance_score=relevance_score,
            source=result.get('document_id', ''),
            metadata={
                'document_title': result.get('document_title', ''),
                'section_heading': result.get('section_heading', ''),
                'source_org': result.get('source_org', 'pho'),
                'document_type': result.get('document_type', ''),
                'chunk_type': result.get('chunk_type', 'unknown'),
                'policy_level': result.get('policy_level', ''),
                'effective_date': result.get('effective_date', ''),
                'source_url': result.get('source_url', ''),
                'topics': result.get('topics', []),
                'distance': result.get('distance', 1.0)
            }
        )
        items.append(section)

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
    
    # Additional resources - include web search links
    resources = [
        {'title': 'PHO IPAC Best Practices', 'url': 'https://www.publichealthontario.ca/ipac'},
        {'title': 'Hand Hygiene Resources', 'url': 'https://www.publichealthontario.ca/hand-hygiene'}
    ]

    # Add web search links to resources
    for idx, link in enumerate(web_links[:5]):  # Top 5 web links
        resources.append({
            'title': f'PHO Current Guidance {idx + 1}',
            'url': link
        })

    # Create response with web search summary
    response_dict = {
        'setting': setting,
        'topic': topic,
        'items': items,  # All retrieved chunks in Option A minimal schema
        'guidelines': guidelines[:5],  # Limit to top 5
        'procedures': procedures[:3],  # Limit to 3
        'checklists': checklists[:3],  # Limit to 3
        'pathogen_specific': pathogen_specific,
        'citations': citations,
        'resources': resources,
        'web_search_summary': web_summary if web_summary else None,
        'sources_searched': ['indexed_corpus'] + (['pho_website'] if search_web else [])
    }

    # Standardize response with top-level citations
    tool_name = "opa_ipac_guidance"
    return standardize_mcp_response(response_dict, tool_name)


# Tool disabled - requires SQL database (opa.db) which is deprecated
# @mcp.tool(name="opa_freshness_probe", description="Check for guidance updates on a topic")
async def freshness_probe_handler_DISABLED(
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


@mcp.tool(name="opa_clinical_tools", description="CEP clinical decision support tools lookup with two-tier architecture")
async def clinical_tools_handler(query: str, k: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    CEP clinical tools navigation and quick reference with two-tier architecture.

    Tier 1: LLM classifies query and identifies relevant clinical tools
    Tier 2: Retrieval scoped to those tools only

    Args:
        query: Clinical condition, tool name, or general query
        k: Number of results to return (default 10)
        filters: Optional dict with:
            - tool_scope: Manual tool ID override (List[str])
            - intent: Manual intent override ("tool_discovery" | "specific_question")
            - tool_type: Specific tool category (string)
            - feature_type: Type of clinical feature ("algorithm", "calculator", "checklist")
            - include_sections: Include section summaries (bool)

    Returns:
        Clinical tools with navigation links and key content
    """
    # Handle default filters
    filters = filters or {}
    tool_scope = filters.get('tool_scope')  # Manual override
    intent = filters.get('intent')
    tool_type = filters.get('tool_type')
    feature_type = filters.get('feature_type')
    include_sections = filters.get('include_sections', False)

    logger.info(f"opa.clinical_tools called for query: {query}")
    logger.debug(f"Parameters: k={k}, tool_scope={tool_scope}, intent={intent}")

    try:
        semantic_search = get_semantic_search()
    except Exception as e:
        logger.error(f"Failed to get semantic search engine: {e}")
        return {
            'items': [],
            'total_tools': 0,
            'query_interpretation': f"Searching CEP clinical tools for: {query}",
            'error': 'Search engine unavailable'
        }

    # STEP 1: Classify query (unless overridden)
    if tool_scope and intent:
        classification = {
            "intent": intent,
            "relevant_tools": tool_scope,
            "scope": "single" if len(tool_scope) == 1 else "multiple",
            "confidence": 1.0,
            "reasoning": "Manual override"
        }
        logger.info("Using manual tool scope override")
    else:
        from .search.cep_triage import classify_cep_query_cached

        # Get OpenAI client from semantic search
        openai_client = semantic_search.openai_client

        classification = await classify_cep_query_cached(query, openai_client)
        logger.info(f"Tool triage: {classification['intent']}, {len(classification.get('relevant_tools', []))} tools")

    # STEP 1.5: Check if no relevant tools found - compute fallback suggestions
    if not classification.get("relevant_tools") or len(classification.get("relevant_tools", [])) == 0:
        logger.info("No exact matches found, computing semantic fallback suggestions")

        from .search.cep_triage import load_tool_catalog
        from .utils.catalog_fallback import (
            compute_catalog_similarity,
            format_suggestions_response
        )

        try:
            catalog = load_tool_catalog()

            suggestions = await compute_catalog_similarity(
                query=query,
                catalog=catalog,
                openai_client=openai_client,
                catalog_type="cep_tools",
                top_k=3,
                min_similarity=0.40
            )

            if suggestions:
                suggestion_text = format_suggestions_response(
                    query=query,
                    suggestions=suggestions,
                    catalog_type="cep_tools"
                )

                return {
                    'items': [],
                    'suggestions': suggestions,
                    'total_tools': 0,
                    'confidence': 0.5,
                    'query_interpretation': suggestion_text,
                    'no_exact_match': True,
                    'classification': {
                        'intent': classification.get('intent'),
                        'relevant_tools': [],
                        'clinical_domain': classification.get('clinical_domain'),
                        'triage_confidence': classification.get('confidence', 0.3),
                        'reasoning': classification.get('reasoning')
                    }
                }
            else:
                return {
                    'items': [],
                    'total_tools': 0,
                    'confidence': 0.3,
                    'query_interpretation': f"No CEP clinical tools found for: {query}",
                    'no_exact_match': True,
                    'classification': {
                        'intent': classification.get('intent'),
                        'relevant_tools': [],
                        'clinical_domain': classification.get('clinical_domain'),
                        'triage_confidence': classification.get('confidence', 0.3),
                        'reasoning': classification.get('reasoning')
                    }
                }
        except Exception as e:
            logger.error(f"Fallback computation failed: {e}", exc_info=True)
            return {
                'items': [],
                'total_tools': 0,
                'confidence': 0.3,
                'query_interpretation': f"No CEP clinical tools found for: {query}",
                'no_exact_match': True
            }

    # STEP 2: Retrieve chunks scoped to relevant tools
    from .search.cep_helpers import (
        retrieve_tool_overviews,
        retrieve_detailed_chunks,
        format_tool_response
    )
    from .search.cep_triage import load_tool_catalog

    try:
        # Special case: scope="all" means return entire catalog
        if classification.get("scope") == "all":
            logger.info("Scope is 'all' - returning full tool catalog instead of vector search")
            catalog = load_tool_catalog()

            # Format catalog entries as tool data
            tools_data = []
            for entry in catalog[:k]:
                tools_data.append({
                    'document_id': entry['tool_id'],
                    'document_title': entry['tool_name'],
                    'source_url': entry['source_url'],
                    'text': f"# {entry['tool_name']}\n\n**Clinical Domain:** {entry['clinical_domain']}\n**Conditions:** {', '.join(entry['conditions'])}\n**Capabilities:** {', '.join(entry['capabilities'])}\n**Topics:** {', '.join(entry.get('topics', []))}\n**Chunk Count:** {entry['chunk_count']}",
                    'chunk_type': 'catalog',
                    'relevance_score': 1.0,
                    'metadata': {
                        'clinical_domain': entry['clinical_domain'],
                        'conditions': entry['conditions'],
                        'capabilities': entry['capabilities'],
                        'chunk_count': entry['chunk_count']
                    }
                })

        elif classification["intent"] == "tool_discovery":
            # Get tool overviews
            logger.info("Using tool discovery mode (overviews)")
            tools_data = await retrieve_tool_overviews(
                semantic_search=semantic_search,
                query=query,
                tool_ids=classification["relevant_tools"],
                k=min(k, len(classification["relevant_tools"]) * 2)
            )
        else:
            # Get detailed chunks
            logger.info("Using specific question mode (detailed)")
            tools_data = await retrieve_detailed_chunks(
                semantic_search=semantic_search,
                query=query,
                tool_ids=classification["relevant_tools"],
                k=k
            )

        logger.info(f"Retrieved {len(tools_data)} chunks")

    except Exception as e:
        logger.error(f"Tool retrieval failed: {e}")
        logger.error(traceback.format_exc())
        tools_data = []

    # Process results into tools (maintain backward compatibility with existing format)
    tools = []
    for result in tools_data:
        # Extract fields from semantic search results
        doc_id = result.get('document_id', '')
        title = result.get('document_title', result.get('title', ''))
        url = result.get('source_url', '')
        last_updated = result.get('effective_date', '')
        text = result.get('text', '')

        # Parse metadata if available
        metadata = {}
        category = None
        if 'metadata' in result:
            metadata = result['metadata']
            category = metadata.get('category')

        tool_data = {
            'tool_id': doc_id,
            'name': title,
            'url': url,
            'last_updated': last_updated,
            'category': category or 'general',
            'summary': text[:500] if text else '',
            'text': text,  # Full text for evaluation framework
            'relevance_score': result.get('relevance_score', 0.8),
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

    # Calculate confidence (incorporate triage confidence)
    triage_confidence = classification.get('confidence', 0.8)
    retrieval_confidence = OPAConfidenceScorer.calculate(
        sql_hits=len(tools_data),
        vector_matches=0,
        sources=['cep'],
        doc_types=['clinical_tool'],
        has_conflict=False
    )
    # Weighted average: 40% triage, 60% retrieval
    confidence = (triage_confidence * 0.4) + (retrieval_confidence * 0.6)

    # Create response (using 'items' to match eval framework expectation)
    response = {
        'items': tools,
        'total_tools': len(tools),
        'confidence': confidence,
        'query_interpretation': f"Searching CEP clinical tools for: {query}"
    }

    if tool_type:
        response['query_interpretation'] += f" (category: {tool_type})"
    if feature_type:
        response['query_interpretation'] += f" (feature: {feature_type})"

    # Add two-tier classification metadata to response
    response['classification'] = {
        'intent': classification.get('intent'),
        'relevant_tools': classification.get('relevant_tools', []),
        'clinical_domain': classification.get('clinical_domain'),
        'triage_confidence': triage_confidence,
        'reasoning': classification.get('reasoning')
    }
    response['tools_searched'] = classification.get('relevant_tools', [])

    # Standardize response with top-level citations
    tool_name = "opa_clinical_tools"
    return standardize_mcp_response(response, tool_name)


@mcp.tool(name="opa_quality_standards", description="Ontario Health quality standards search with two-tier architecture")
async def quality_standards_handler(query: str, k: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Search Ontario Health quality standards with two-tier architecture.

    Tier 1: LLM classifies query and identifies relevant standards
    Tier 2: Retrieval scoped to those standards only

    Args:
        query: Clinical topic or condition (e.g., 'diabetes', 'hip fracture')
        k: Number of results to return (default 10)
        filters: Optional dict with:
            - standard_scope: Manual standard ID override (List[str])
            - intent: Manual intent override ("standard_discovery" | "specific_indicator")
            - query_focus: "overview" | "statements" | "indicators" | "implementation"
            - retrieve_all_statements: Retrieve all statements for a standard (bool) [BACKWARD COMPAT]
            - statement_type: Type of content [BACKWARD COMPAT]

    Returns:
        Quality statements, standard information, and citations
    """
    # Extract filters
    filters = filters or {}
    standard_scope = filters.get('standard_scope')  # Manual override
    intent = filters.get('intent')
    query_focus = filters.get('query_focus')

    # Backward compatibility
    retrieve_all_statements = filters.get('retrieve_all_statements', False)
    statement_type = filters.get('statement_type', 'all')

    logger.info(f"opa.quality_standards called - query: {query}")
    logger.debug(f"Parameters: k={k}, standard_scope={standard_scope}, intent={intent}, query_focus={query_focus}")

    try:
        semantic_search = get_semantic_search()
    except Exception as e:
        logger.error(f"Failed to get semantic search engine: {e}")
        return QualityStandardsResponse(
            standard_title=None,
            items=[],
            total_statements=0,
            citations=[],
            confidence=0.3
        ).model_dump()

    # STEP 1: Classify query (unless overridden)
    if standard_scope and intent:
        classification = {
            "intent": intent,
            "relevant_standards": standard_scope,
            "query_focus": query_focus or "statements",
            "confidence": 1.0,
            "reasoning": "Manual override"
        }
        logger.info("Using manual standard scope override")
    else:
        # Get OpenAI client from semantic search
        openai_client = semantic_search.openai_client

        classification = await classify_quality_standards_query_cached(query, openai_client)
        logger.info(f"QS triage: {classification['intent']}, {len(classification.get('relevant_standards', []))} standards")

    # STEP 1.5: Check if no relevant standards found - compute fallback suggestions
    if not classification.get("relevant_standards") or len(classification.get("relevant_standards", [])) == 0:
        logger.info("No exact quality standards matches found, computing semantic fallback suggestions")

        from .search.qs_triage import load_quality_standards_catalog
        from .utils.catalog_fallback import (
            compute_catalog_similarity,
            format_suggestions_response
        )

        try:
            catalog = load_quality_standards_catalog()

            suggestions = await compute_catalog_similarity(
                query=query,
                catalog=catalog,
                openai_client=openai_client,
                catalog_type="quality_standards",
                top_k=3,
                min_similarity=0.40
            )

            if suggestions:
                suggestion_text = format_suggestions_response(
                    query=query,
                    suggestions=suggestions,
                    catalog_type="quality_standards"
                )

                return QualityStandardsResponse(
                    standard_title=None,
                    items=[],
                    total_statements=0,
                    citations=[],
                    confidence=0.5,
                    suggestions=suggestions,
                    no_exact_match=True
                ).model_dump()
            else:
                return QualityStandardsResponse(
                    standard_title=None,
                    items=[],
                    total_statements=0,
                    citations=[],
                    confidence=0.3,
                    no_exact_match=True
                ).model_dump()
        except Exception as e:
            logger.error(f"Fallback computation failed: {e}", exc_info=True)
            return QualityStandardsResponse(
                standard_title=None,
                items=[],
                total_statements=0,
                citations=[],
                confidence=0.3,
                no_exact_match=True
            ).model_dump()

    # STEP 2: Retrieve chunks scoped to relevant standards
    from .search.qs_helpers import (
        retrieve_standard_overviews,
        retrieve_detailed_statements
    )
    from .search.qs_triage import load_quality_standards_catalog

    try:
        # Special case: scope="all" means return entire catalog
        if classification.get("scope") == "all":
            logger.info("Scope is 'all' - returning full quality standards catalog instead of vector search")
            catalog = load_quality_standards_catalog()

            # Format catalog entries as search results
            search_results = []
            for entry in catalog:
                # Build overview text from catalog metadata
                overview_text = f"# {entry['standard_title']}\n\n"
                overview_text += f"**Clinical Domain:** {entry['clinical_domain'].replace('_', ' ').title()}\n"
                overview_text += f"**Conditions:** {', '.join(entry.get('conditions', []))}\n"
                overview_text += f"**Care Focus:** {', '.join(entry.get('care_focus', []))}\n"

                if entry.get('key_statements'):
                    overview_text += f"\n**Key Quality Statements:**\n"
                    for stmt in entry['key_statements'][:5]:
                        overview_text += f"- {stmt}\n"

                overview_text += f"\n**Statement Count:** {entry.get('statement_count', 0)}"

                search_results.append({
                    'text': overview_text,
                    'metadata': {
                        'title': entry['standard_title'],
                        'standard_id': entry['standard_id'],
                        'clinical_domain': entry['clinical_domain'],
                        'conditions': entry.get('conditions', []),
                        'care_focus': entry.get('care_focus', []),
                        'statement_count': entry.get('statement_count', 0),
                        'chunk_type': 'catalog_overview'
                    },
                    'relevance_score': 0.95  # High but not perfect for catalog browsing
                })

        elif classification["intent"] == "standard_discovery":
            # Get standard overviews
            logger.info("Using standard discovery mode (overviews)")
            search_results = await retrieve_standard_overviews(
                semantic_search=semantic_search,
                query=query,
                standard_ids=classification["relevant_standards"],
                k=min(k, len(classification["relevant_standards"]) * 2)
            )
        else:
            # Get detailed statement chunks
            logger.info("Using specific indicator mode (detailed)")
            search_results = await retrieve_detailed_statements(
                semantic_search=semantic_search,
                query=query,
                standard_ids=classification["relevant_standards"],
                query_focus=classification.get("query_focus", "statements"),
                k=k if not retrieve_all_statements else 50
            )

        logger.info(f"Retrieved {len(search_results)} chunks")

    except Exception as e:
        logger.error(f"Quality standards retrieval failed: {e}")
        logger.error(traceback.format_exc())
        search_results = []

    # STEP 3: Process results into quality statements
    statements = []
    executive_summary = None
    scope = None
    year = None
    citations_set = set()

    # Determine the primary standard from results
    standard_title = None
    if search_results:
        # Look for the most common title in results
        title_counts = {}
        for result in search_results:
            title = result.get('metadata', {}).get('title', '')
            if title:
                title_counts[title] = title_counts.get(title, 0) + 1

        if title_counts:
            # Get the most common title
            standard_title = max(title_counts.items(), key=lambda x: x[1])[0]
            logger.info(f"Primary standard from results: {standard_title}")

    for result in search_results:
        metadata = result.get('metadata', {})
        chunk_type = metadata.get('chunk_type', '')

        # Extract document-level information
        if chunk_type == 'document':
            text = result.get('text', '')
            title = metadata.get('title', '')

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

            # For discovery mode, convert document chunks to statement items
            if classification["intent"] == "standard_discovery":
                # Create a QualityStatement from the document overview
                statement = QualityStatement(
                    id=f"{title}:overview",
                    text=text,  # Full document overview text
                    relevance_score=result.get('relevance_score', 0.9),
                    source=title or 'Ontario Health Quality Standard',
                    metadata={
                        'statement_number': 0,  # N/A for overviews
                        'title': title,
                        'standard_id': metadata.get('standard_id', ''),
                        'chunk_type': 'document',
                        'executive_summary': executive_summary if executive_summary else None,
                        'scope': scope if scope else None,
                        'year': year
                    }
                )
                statements.append(statement)

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

            # Create QualityStatement
            statement = QualityStatement(
                id=f"{standard_title or 'unknown'}:statement_{stmt_num}",
                text=full if full else brief,
                relevance_score=result.get('relevance_score', 0.9),
                source=standard_title or 'Ontario Health Quality Standard',
                metadata={
                    'statement_number': stmt_num,
                    'title': stmt_title,
                    'brief_statement': brief,
                    'full_text': full if full != brief else None,
                    'indicators': indicators,
                    'for_patients': for_patients if for_patients else None,
                    'for_clinicians': for_clinicians if for_clinicians else None,
                    'chunk_type': 'statement'
                }
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
    statements.sort(key=lambda s: s.metadata.get('statement_number', 0))

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

    # Calculate confidence (incorporate triage confidence)
    triage_confidence = classification.get('confidence', 0.8)
    retrieval_confidence = OPAConfidenceScorer.calculate(
        sql_hits=len(search_results),
        vector_matches=0,
        sources=['ontario_health_quality_standards'],
        doc_types=['quality_standard'],
        has_conflict=False
    )
    # Weighted average: 40% triage, 60% retrieval
    confidence = (triage_confidence * 0.4) + (retrieval_confidence * 0.6)

    # DECISIONAL SYNTHESIS (NEW)
    if classification.get('is_decisional', False):
        logger.info("Decisional query detected - synthesizing practice validation")

        from .search.qs_helpers import synthesize_validation_answer

        try:
            decisional_answer = await synthesize_validation_answer(
                query=query,
                classification=classification,
                retrieved_chunks=standards_data,
                llm_client=openai_client
            )

            # Return decisional format with structured answer + supporting evidence
            return {
                'decisional_answer': decisional_answer,
                'supporting_evidence': statements,  # Full statement objects
                'classification': {
                    'intent': classification['intent'],
                    'query_type': classification.get('query_type', 'practice_validation'),
                    'relevant_standards': classification.get('relevant_standards', []),
                    'query_focus': classification.get('query_focus'),
                    'is_decisional': True,
                    'confidence': classification.get('confidence', 0.8)
                },
                'response_type': 'decisional',
                'query_interpretation': f"Practice validation for: {query}",
                'standards_searched': classification.get('relevant_standards', []),
                # Add top-level fields for test framework compatibility
                'confidence': decisional_answer.get('confidence', 0.8),
                'citations': citations,
                'items': statements  # Include for backwards compatibility
            }

        except Exception as e:
            logger.error(f"Decisional synthesis failed: {e}", exc_info=True)
            # Fall through to standard informational response
            logger.info("Falling back to informational response due to synthesis error")

    # Create response (informational query path)
    response = QualityStandardsResponse(
        standard_title=standard_title,
        items=statements,
        total_statements=len(statements),
        executive_summary=executive_summary,
        scope=scope,
        year=year,
        citations=citations,
        confidence=confidence
    )

    logger.info(f"Returning {len(statements)} quality statements")

    # Convert to dict and add classification metadata
    response_dict = response.model_dump()

    # Add two-tier classification metadata to response
    response_dict['classification'] = {
        'intent': classification.get('intent'),
        'relevant_standards': classification.get('relevant_standards', []),
        'query_focus': classification.get('query_focus'),
        'clinical_domain': classification.get('clinical_domain'),
        'triage_confidence': triage_confidence,
        'reasoning': classification.get('reasoning')
    }
    response_dict['standards_searched'] = classification.get('relevant_standards', [])

    return standardize_mcp_response(response_dict, "opa_quality_standards")


@mcp.tool(name="opa_choosing_wisely", description="Choosing Wisely recommendations with two-tier specialty triage")
async def choosing_wisely_handler(query: str, k: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Search Choosing Wisely recommendations for unnecessary tests and procedures.

    Uses two-tier retrieval architecture:
    1. LLM classifies query intent and identifies relevant specialties
    2. Retrieval is scoped to those specialties only

    Args:
        query: Test, procedure, or clinical scenario to check
        k: Number of results to return (default 10)
        filters: Optional dict with:
            - specialty_scope: Manual specialty ID override (List[str])
            - intent: Manual intent override ("specialty_discovery" | "specific_recommendation")
            - all_specialty_recommendations: Return ALL recommendations for specialty (bool)

    Returns:
        Choosing Wisely recommendations with specialty information, classification, and citations
    """
    # Use filters if provided
    filters = filters or {}
    specialty_scope = filters.get('specialty_scope')  # Manual override (list of specialty_ids)
    intent = filters.get('intent')  # Manual intent override
    all_specialty_recommendations = filters.get('all_specialty_recommendations', False)

    logger.info(f"opa.choosing_wisely called - query: {query}")
    logger.info(f"  specialty_scope: {specialty_scope}, intent: {intent}, all_recommendations: {all_specialty_recommendations}, k: {k}")

    try:
        # Get semantic search engine
        semantic_search = get_semantic_search()

        # Get OpenAI client for LLM triage
        openai_client = get_openai_client()

        # TIER 1: Classify query (unless overridden)
        if specialty_scope and intent:
            classification = {
                "intent": intent,
                "relevant_specialties": specialty_scope,
                "confidence": 1.0,
                "reasoning": "Manual override"
            }
            logger.info("Using manual specialty scope and intent")
        else:
            classification = await classify_choosing_wisely_query_cached(query, openai_client)
            logger.info(f"LLM Classification: {classification}")

        specialty_ids = classification.get('relevant_specialties', [])

        # TIER 1.5: Check if no relevant specialties found - compute fallback suggestions
        if not specialty_ids or len(specialty_ids) == 0:
            logger.info("No exact Choosing Wisely specialty matches found, computing semantic fallback suggestions")

            from .search.choosing_wisely_triage import load_specialty_catalog
            from .utils.catalog_fallback import (
                compute_catalog_similarity,
                format_suggestions_response
            )

            try:
                catalog = load_specialty_catalog()

                suggestions = await compute_catalog_similarity(
                    query=query,
                    catalog=catalog,
                    openai_client=openai_client,
                    catalog_type="choosing_wisely",
                    top_k=3,
                    min_similarity=0.40
                )

                if suggestions:
                    suggestion_text = format_suggestions_response(
                        query=query,
                        suggestions=suggestions,
                        catalog_type="choosing_wisely"
                    )

                    return ChoosingWiselyResponse(
                        specialty_title=None,
                        items=[],
                        total_recommendations=0,
                        citations=[],
                        confidence=0.5,
                        query_interpretation=suggestion_text,
                        suggestions=suggestions,
                        no_exact_match=True
                    ).model_dump()
                else:
                    return ChoosingWiselyResponse(
                        specialty_title=None,
                        items=[],
                        total_recommendations=0,
                        citations=[],
                        confidence=0.3,
                        query_interpretation=f"No Choosing Wisely recommendations found for: {query}",
                        no_exact_match=True
                    ).model_dump()
            except Exception as e:
                logger.error(f"Fallback computation failed: {e}", exc_info=True)
                return ChoosingWiselyResponse(
                    specialty_title=None,
                    items=[],
                    total_recommendations=0,
                    citations=[],
                    confidence=0.3,
                    query_interpretation=f"No Choosing Wisely recommendations found for: {query}",
                    no_exact_match=True
                ).model_dump()

        # TIER 2: Retrieve chunks based on intent and specialty scope
        from .search.choosing_wisely_helpers import (
            retrieve_specialty_overviews,
            retrieve_detailed_recommendations,
            retrieve_complete_specialty,
            format_choosing_wisely_response
        )
        from .search.choosing_wisely_triage import get_specialty_name

        # Handle three retrieval modes
        if all_specialty_recommendations and specialty_ids:
            # Mode 1: Complete specialty retrieval - get ALL chunks from database
            specialty_name = get_specialty_name(specialty_ids[0])
            if specialty_name:
                logger.info(f"Mode 1: Complete retrieval for '{specialty_name}' - fetching ALL chunks from database")

                # Use .get() with exact filter to retrieve ALL chunks for this specialty
                # This bypasses vector search entirely and guarantees 100% recall
                vector_client = semantic_search.vector_client
                collection = vector_client.collection

                all_chunks = collection.get(
                    where={"specialty": {"$eq": specialty_name}},
                    include=['documents', 'metadatas']
                )

                logger.info(f"Retrieved {len(all_chunks['ids'])} total chunks for '{specialty_name}'")

                # Format chunks to match expected structure
                search_results = []
                for chunk_id, doc, metadata in zip(all_chunks['ids'], all_chunks['documents'], all_chunks['metadatas']):
                    search_results.append({
                        'text': doc,
                        'metadata': metadata,
                        'relevance_score': 1.0  # All chunks equally relevant for complete retrieval
                    })

                # Sort: parent chunks first, then children
                parent_results = [r for r in search_results if r['metadata'].get('chunk_type') == 'parent']
                child_results = [r for r in search_results if r['metadata'].get('chunk_type') == 'child']
                search_results = parent_results + child_results

                logger.info(f"Returning {len(search_results)} chunks ({len(parent_results)} parent, {len(child_results)} children)")
            else:
                logger.error(f"Specialty name not found for ID: {specialty_ids[0]}")
                search_results = []

        elif classification['intent'] == 'specialty_discovery' and specialty_ids:
            # Mode 2: Specialty discovery (overview chunks)
            logger.info(f"Mode 2: Discovery - retrieving overviews for {len(specialty_ids)} specialties")
            formatted_chunks = await retrieve_specialty_overviews(
                semantic_search,
                query,
                specialty_ids,
                k=k
            )
            # Convert to search results format
            search_results = [
                {'text': c['text'], 'metadata': c, 'relevance_score': c.get('relevance_score', 0.8)}
                for c in formatted_chunks
            ]

        elif specialty_ids:
            # Mode 3: Specific recommendations (scoped semantic search)
            logger.info(f"Mode 3: Specific - retrieving detailed recommendations from {len(specialty_ids)} specialties")
            formatted_chunks = await retrieve_detailed_recommendations(
                semantic_search,
                query,
                specialty_ids,
                k=k
            )
            # Convert to search results format
            search_results = [
                {'text': c['text'], 'metadata': c, 'relevance_score': c.get('relevance_score', 0.8)}
                for c in formatted_chunks
            ]

        else:
            # Mode 4: Fallback - general semantic search (no triage)
            logger.warning("No specialties identified - falling back to general search")
            search_results = await semantic_search.search(
                query=query,
                sources=['choosing_wisely'],
                k=k,
                use_reranking=True,
                use_hybrid=False,
                use_ce_reranking=False
            )

        logger.info(f"Retrieved {len(search_results)} chunks")
        
        # Step 4: Process results into recommendations
        recommendations = []
        specialty_overview = None
        organization = None
        last_updated = None
        citations_set = set()
        
        # Track the most common specialty in results
        specialty_counts = {}
        
        # Track recommendations by (specialty, recommendation_number) to avoid duplicates
        seen_recommendations = {}
        
        for result in search_results:
            metadata = result.get('metadata', {})

            # ChromaDB nests metadata in a 'metadata' field - extract it
            nested_metadata = metadata.get('metadata', {})
            if nested_metadata:
                # Use nested metadata if present (ChromaDB format)
                chunk_type = nested_metadata.get('chunk_type', metadata.get('chunk_type', ''))
                doc_type = nested_metadata.get('doc_type', metadata.get('doc_type', ''))
                # Merge nested metadata into top-level for easier access
                metadata = {**metadata, **nested_metadata}
            else:
                # Fallback to top-level metadata
                chunk_type = metadata.get('chunk_type', '')
                doc_type = metadata.get('doc_type', '')

            # Extract specialty-level information from overview chunks
            # Handle both old format (chunk_type='specialty_overview') and new format (doc_type='choosing_wisely_overview')
            is_overview = (chunk_type == 'specialty_overview' or
                          chunk_type == 'parent' and doc_type == 'choosing_wisely_overview')

            if is_overview:
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
            # Handle both old format (chunk_type='recommendation') and new format (doc_type='choosing_wisely_recommendation')
            is_recommendation = (chunk_type == 'recommendation' or
                                chunk_type == 'child' and doc_type == 'choosing_wisely_recommendation')

            if is_recommendation:
                rec_num = metadata.get('recommendation_number', 0)
                rec_title = metadata.get('recommendation_title', '')
                specialty = metadata.get('specialty', '')
                org = metadata.get('organization', '')
                
                # Create unique key for this recommendation
                rec_key = (specialty, rec_num)
                
                # Count specialty occurrences
                if specialty:
                    specialty_counts[specialty] = specialty_counts.get(specialty, 0) + 1
                
                # Skip if we've already processed this recommendation
                if rec_key in seen_recommendations:
                    # But merge text if this chunk has more content
                    existing = seen_recommendations[rec_key]
                    current_text = result.get('text', '')
                    if len(current_text) > len(existing.get('text', '')):
                        seen_recommendations[rec_key]['text'] = current_text
                    continue
                
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
                
                # Create unique ID for this recommendation
                rec_id = f"{specialty.lower().replace(' ', '_')}_{rec_num}"

                # Get relevance score from search result
                relevance_score = result.get('relevance_score', 0.8)

                recommendation = ChoosingWiselyRecommendation(
                    id=rec_id,
                    text=description,  # Full explanation goes in text field
                    relevance_score=relevance_score,
                    source=specialty,  # Specialty is the source
                    metadata={
                        'recommendation_number': rec_num,
                        'title': title,
                        'organization': org,
                        'references': references
                    }
                )
                
                # Store in seen_recommendations and add to recommendations list
                seen_recommendations[rec_key] = {
                    'recommendation': recommendation,
                    'text': text
                }
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
        elif specialty_ids:
            # Use first specialty from classification
            primary_specialty = get_specialty_name(specialty_ids[0])

        # Sort recommendations by relevance score first, then by number
        recommendations.sort(key=lambda r: (-r.relevance_score, r.metadata['recommendation_number']))

        # Limit to requested k
        if len(recommendations) > k:
            recommendations = recommendations[:k]
            logger.info(f"Limited to {len(recommendations)} recommendations (from {len(recommendations)} total)")

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

        # Calculate confidence (enhanced with classification confidence)
        classification_confidence = classification.get('confidence', 0.5)
        confidence = classification_confidence if recommendations else classification_confidence * 0.5

        # Create query interpretation (enhanced with classification details)
        clinical_scenario = classification.get('clinical_scenario', 'general')
        query_interpretation = f"Intent: {classification['intent']} | Scenario: {clinical_scenario}"
        if primary_specialty:
            query_interpretation += f" | Specialty: {primary_specialty}"
        if len(specialty_ids) > 1:
            query_interpretation += f" | Searched {len(specialty_ids)} specialties"

        # DECISIONAL SYNTHESIS (NEW)
        if classification.get('is_decisional', False):
            logger.info("Decisional query detected - synthesizing binary recommendation")

            from .search.choosing_wisely_helpers import synthesize_binary_recommendation

            try:
                decisional_answer = await synthesize_binary_recommendation(
                    query=query,
                    classification=classification,
                    retrieved_chunks=search_results,
                    llm_client=openai_client
                )

                # Return decisional format with structured answer + supporting evidence
                return {
                    'decisional_answer': decisional_answer,
                    'supporting_evidence': recommendations,  # Full recommendation objects
                    'classification': {
                        'intent': classification['intent'],
                        'query_type': classification.get('query_type', 'binary_recommendation'),
                        'relevant_specialties': specialty_ids,
                        'clinical_scenario': classification.get('clinical_scenario'),
                        'is_decisional': True,
                        'confidence': classification.get('confidence', 0.8)
                    },
                    'response_type': 'decisional',
                    'query_interpretation': query_interpretation,
                    'specialties_searched': specialty_ids,
                    # Add top-level fields for test framework compatibility
                    'confidence': decisional_answer.get('confidence', 0.8),
                    'citations': citations,
                    'items': recommendations  # Include for backwards compatibility
                }

            except Exception as e:
                logger.error(f"Decisional synthesis failed: {e}", exc_info=True)
                # Fall through to standard informational response
                logger.info("Falling back to informational response due to synthesis error")

        # Create response (informational query path)
        response = ChoosingWiselyResponse(
            specialty_title=primary_specialty,
            items=recommendations,
            total_recommendations=len(recommendations),
            specialty_overview=specialty_overview,
            organization=organization,
            last_updated=last_updated,
            citations=citations,
            confidence=confidence,
            query_interpretation=query_interpretation
        )

        logger.info(f"Returning {len(recommendations)} Choosing Wisely recommendations")

        # Convert to dict and add classification details
        response_dict = response.model_dump()

        # Add two-tier classification metadata
        response_dict['classification'] = {
            'intent': classification.get('intent'),
            'scope': classification.get('scope'),
            'clinical_scenario': classification.get('clinical_scenario'),
            'confidence': classification.get('confidence'),
            'reasoning': classification.get('reasoning')
        }
        response_dict['specialties_searched'] = specialty_ids

        return standardize_mcp_response(response_dict, "opa_choosing_wisely")
        
    except Exception as e:
        logger.error(f"Choosing Wisely search failed: {e}")
        logger.error(traceback.format_exc())
        
        # Return error response
        return {
            'error': str(e),
            'specialty_title': None,
            'items': [],
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
    logger.info("  - opa.ipac_guidance: PHO IPAC guidance (indexed corpus + current web search)")
    logger.info("  - opa.freshness_probe: Check for guidance updates")
    logger.info("  - opa.clinical_tools: CEP clinical decision support tools")
    logger.info("  - opa.quality_standards: Ontario Health quality standards search")
    logger.info("  - opa.choosing_wisely: Choosing Wisely recommendations for avoiding unnecessary care")
    
    # Initialize vector client only (SQL database deprecated)
    try:
        logger.info("Initializing vector client...")
        get_vector_client()
        logger.info("Dr. OPA MCP server ready with vector search")
    except Exception as e:
        logger.warning(f"Vector client initialization failed: {e}")
        logger.warning("Server will start but vector search operations may fail")
        logger.warning("Please ensure ChromaDB is populated using ingestion scripts")
    
    logger.info(f"Server session log: {log_file}")
    
    # Run the server on stdio (what MCP CLI expects)
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Server crashed: {e}")
        logger.error(traceback.format_exc())
        raise