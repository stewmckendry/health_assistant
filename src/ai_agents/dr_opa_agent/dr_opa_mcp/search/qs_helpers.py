"""
Quality Standards Retrieval Helper Functions.

Provides intent-specific retrieval strategies for Ontario Health Quality Standards:
- Standard overview retrieval for discovery queries
- Detailed statement retrieval for specific queries
- Parent context assembly and deduplication
- Decisional synthesis (practice validation)

Author: AI Assistant
Date: 2025-10-07
"""

import json
import logging
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


async def retrieve_standard_overviews(
    semantic_search,
    query: str,
    standard_ids: List[str],
    k: int = 10
) -> List[Dict]:
    """
    Retrieve quality standard overview chunks (document chunks) for discovery queries.

    Strategy:
    1. Get document chunks from relevant standards
    2. Deduplicate to 1 overview per standard
    3. Sort by relevance

    Args:
        semantic_search: SemanticSearchEngine instance
        query: User query
        standard_ids: List of standard IDs to search
        k: Number of results

    Returns:
        List of search results (deduplicated overviews)
    """
    from .qs_triage import get_standard_title

    logger.info(f"Retrieving overviews for {len(standard_ids)} standards")

    # Convert standard_ids to titles for metadata filtering
    standard_titles = []
    for sid in standard_ids:
        title = get_standard_title(sid)
        if title:
            standard_titles.append(title)
        else:
            logger.warning(f"Could not find title for standard_id: {sid}")

    if not standard_titles:
        logger.warning("No valid standard titles found, returning empty results")
        return []

    # Search for document chunks only
    try:
        # Build metadata filter for ChromaDB
        where_filter = {
            "$and": [
                {
                    "$or": [
                        {"title": {"$eq": title}}
                        for title in standard_titles
                    ]
                },
                {"chunk_type": "document"}  # Only document chunks (overviews)
            ]
        }

        logger.info(f"Searching for document chunks from standards: {standard_titles[:3]}...")

        # Perform search with filter
        search_results = await semantic_search.search(
            query=query,
            sources=['ontario_health_quality_standards'],
            k=k * 2,  # Get more to ensure coverage
            use_reranking=True,
            use_hybrid=False,
            use_ce_reranking=False,
            where_filter=where_filter
        )

        logger.info(f"Found {len(search_results)} document chunks")

        # Deduplicate by standard title (one overview per standard)
        deduplicated = deduplicate_by_standard(search_results)

        logger.info(f"After deduplication: {len(deduplicated)} unique standards")

        return deduplicated[:k]

    except Exception as e:
        logger.error(f"Overview retrieval failed: {e}")
        return []


async def retrieve_detailed_statements(
    semantic_search,
    query: str,
    standard_ids: List[str],
    query_focus: str,
    k: int = 20
) -> List[Dict]:
    """
    Retrieve detailed statement chunks for specific queries.

    Strategy:
    1. Search within scoped standards
    2. Filter by query_focus if specified
    3. Return statement chunks with context

    Args:
        semantic_search: SemanticSearchEngine instance
        query: User query
        standard_ids: List of standard IDs to search
        query_focus: "statements" | "indicators" | "implementation" | "overview"
        k: Number of results

    Returns:
        List of search results
    """
    from .qs_triage import get_standard_title

    logger.info(f"Retrieving detailed statements for {len(standard_ids)} standards")
    logger.info(f"Query focus: {query_focus}")

    # Convert standard_ids to titles for metadata filtering
    standard_titles = []
    for sid in standard_ids:
        title = get_standard_title(sid)
        if title:
            standard_titles.append(title)
        else:
            logger.warning(f"Could not find title for standard_id: {sid}")

    if not standard_titles:
        logger.warning("No valid standard titles found, returning empty results")
        return []

    try:
        # Build metadata filter based on query focus
        if query_focus == "indicators":
            # Focus on statement chunks with indicators
            # Build title filter (handle single vs multiple titles)
            if len(standard_titles) == 1:
                title_filter = {"title": {"$eq": standard_titles[0]}}
            else:
                title_filter = {
                    "$or": [
                        {"title": {"$eq": title}}
                        for title in standard_titles
                    ]
                }

            where_filter = {
                "$and": [
                    title_filter,
                    {"chunk_type": "statement"},
                    {"has_indicators": "True"}
                ]
            }
        elif query_focus == "overview":
            # Get document chunks
            # Build title filter (handle single vs multiple titles)
            if len(standard_titles) == 1:
                title_filter = {"title": {"$eq": standard_titles[0]}}
            else:
                title_filter = {
                    "$or": [
                        {"title": {"$eq": title}}
                        for title in standard_titles
                    ]
                }

            where_filter = {
                "$and": [
                    title_filter,
                    {"chunk_type": "document"}
                ]
            }
        else:
            # General search - all chunk types from relevant standards
            # Handle single vs multiple titles
            if len(standard_titles) == 1:
                where_filter = {"title": {"$eq": standard_titles[0]}}
            else:
                where_filter = {
                    "$or": [
                        {"title": {"$eq": title}}
                        for title in standard_titles
                    ]
                }

        logger.info(f"Searching standards: {standard_titles[:3]}...")

        # Perform search with filter
        search_results = await semantic_search.search(
            query=query,
            sources=['ontario_health_quality_standards'],
            k=k,
            use_reranking=True,
            use_hybrid=False,
            use_ce_reranking=False,
            where_filter=where_filter
        )

        logger.info(f"Found {len(search_results)} results")

        return search_results

    except Exception as e:
        logger.error(f"Detailed statement retrieval failed: {e}")
        return []


def deduplicate_by_standard(chunks: List[Dict]) -> List[Dict]:
    """
    Deduplicate to one overview chunk per standard.

    Keeps the highest relevance score chunk for each standard.

    Args:
        chunks: List of search result chunks

    Returns:
        Deduplicated list (one chunk per standard)
    """
    # Group by standard title
    by_standard = defaultdict(list)

    for chunk in chunks:
        title = chunk.get('metadata', {}).get('title', 'Unknown')
        by_standard[title].append(chunk)

    # Keep best chunk per standard (highest similarity score)
    deduplicated = []
    for title, standard_chunks in by_standard.items():
        # Sort by similarity score (descending)
        standard_chunks.sort(
            key=lambda x: x.get('similarity_score', 0),
            reverse=True
        )
        # Keep the top chunk
        deduplicated.append(standard_chunks[0])

    # Sort deduplicated results by relevance
    deduplicated.sort(
        key=lambda x: x.get('similarity_score', 0),
        reverse=True
    )

    return deduplicated


def format_qs_response(
    chunks: List[Dict],
    classification: Dict,
    query: str
) -> Dict:
    """
    Format quality standards response with standard-level metadata.

    Args:
        chunks: Retrieved chunks
        classification: Triage classification result
        query: Original query

    Returns:
        Formatted response dict with standard context
    """
    from .qs_triage import get_standard_info

    # Get standard metadata for context
    standard_context = []
    for standard_id in classification.get('relevant_standards', []):
        info = get_standard_info(standard_id)
        if info:
            standard_context.append({
                'standard_id': info['standard_id'],
                'title': info['standard_title'],
                'domain': info['clinical_domain'],
                'statement_count': info['statement_count']
            })

    # Build response
    response = {
        'classification': {
            'intent': classification.get('intent'),
            'scope': classification.get('scope'),
            'relevant_standards': classification.get('relevant_standards', []),
            'query_focus': classification.get('query_focus'),
            'confidence': classification.get('confidence', 0.5),
            'reasoning': classification.get('reasoning', '')
        },
        'standard_context': standard_context,
        'items': chunks,
        'query_interpretation': _build_query_interpretation(query, classification),
        'standards_searched': len(classification.get('relevant_standards', []))
    }

    return response


def _build_query_interpretation(query: str, classification: Dict) -> str:
    """
    Build human-readable query interpretation string.

    Args:
        query: Original query
        classification: Classification result

    Returns:
        Interpretation string
    """
    intent = classification.get('intent', 'unknown')
    standards = classification.get('relevant_standards', [])
    focus = classification.get('query_focus', 'statements')

    if intent == 'standard_discovery':
        if len(standards) == 1:
            return f"Searching for overview of 1 quality standard: {query}"
        else:
            return f"Searching for overview of {len(standards)} quality standards related to: {query}"
    else:
        if focus == 'indicators':
            return f"Searching for quality indicators related to: {query}"
        elif focus == 'implementation':
            return f"Searching for implementation guidance for: {query}"
        else:
            return f"Searching quality standards for: {query}"


async def synthesize_validation_answer(
    query: str,
    classification: Dict,
    retrieved_chunks: List[Dict],
    llm_client
) -> Dict:
    """
    Validate clinical practice against quality standards.

    Args:
        query: User's practice validation question
        classification: Triage classification results
        retrieved_chunks: Retrieved quality standard chunks
        llm_client: OpenAI client for LLM synthesis

    Returns:
        {
            "aligned": "yes" | "no" | "partial" | "insufficient_info",
            "reasoning": "Explanation citing quality statements",
            "supporting_statements": ["Quality statements that support"],
            "gaps": ["Areas where practice deviates"],
            "recommendations": ["Actions to improve alignment"],
            "relevant_standards": [{"standard": "...", "statement": "..."}],
            "confidence": 0.0-1.0
        }
    """
    logger.info("Synthesizing validation answer for decisional query")

    # Build context from quality standard statements (top 10 most relevant)
    standard_context = []
    for chunk in retrieved_chunks[:10]:
        metadata = chunk.get('metadata', {}) if 'metadata' in chunk else chunk
        standard_context.append({
            'standard': metadata.get('document_title', chunk.get('document_title', 'Unknown')),
            'statement_number': metadata.get('statement_number', ''),
            'statement_type': metadata.get('statement_type', ''),
            'text': chunk.get('text', '')[:1000]
        })

    prompt = f"""You are a quality standards advisor. Evaluate this clinical practice against Ontario Health quality standards.

Clinical Practice Scenario:
{query}

Relevant Quality Standard Statements:
{json.dumps(standard_context, indent=2)}

Analyze alignment and respond with JSON:
{{
    "aligned": "yes" | "no" | "partial" | "insufficient_info",
    "reasoning": "<1-3 sentence explanation citing specific quality statements>",
    "supporting_statements": ["<quality statements that support this practice>"],
    "gaps": ["<areas where practice deviates from or doesn't address standards>"],
    "recommendations": ["<specific actions to improve alignment>"],
    "relevant_standards": [
        {{"standard": "<standard name>", "statement": "<statement number>", "statement_type": "<type>"}}
    ],
    "confidence": <0.0-1.0>
}}

Guidelines:
- "yes" = practice clearly aligns with quality statements
- "no" = practice contradicts quality statements
- "partial" = practice aligns with some aspects but misses others
- "insufficient_info" = quality standards don't address this specific scenario

Focus on evidence-based recommendations, not absolute requirements.
Be specific about which quality statements support or contradict the practice."""

    try:
        response = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        logger.info(f"Validation result: {result.get('aligned', 'unknown')}")
        logger.info(f"  Confidence: {result.get('confidence', 0.0)}")

        return result

    except Exception as e:
        logger.error(f"Validation synthesis error: {e}")
        return {
            "aligned": "insufficient_info",
            "reasoning": "Error during practice validation",
            "supporting_statements": [],
            "gaps": [],
            "recommendations": ["Please consult quality standards directly"],
            "relevant_standards": [],
            "confidence": 0.0
        }
