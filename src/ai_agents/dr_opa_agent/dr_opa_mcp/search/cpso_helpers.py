"""
CPSO Policy-Scoped Retrieval Helpers.

Helper functions for two-tier CPSO policy retrieval:
- Policy overview retrieval (for discovery queries)
- Detailed chunk retrieval (for specific queries)
- Parent-child context assembly
- Decisional synthesis (compliance checking)

Author: AI Assistant
Date: 2025-10-07
"""

import json
import logging
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


async def retrieve_policy_overviews(
    semantic_search,
    query: str,
    policy_ids: List[str],
    k: int = 10
) -> List[Dict]:
    """
    Retrieve policy overview chunks for discovery queries.

    Strategy:
    1. Get parent chunks from relevant policies
    2. Deduplicate to 1-2 overviews per policy
    3. Sort by relevance

    Args:
        semantic_search: SemanticSearchEngine instance
        query: User query
        policy_ids: List of policy IDs to search
        k: Maximum results

    Returns:
        List of overview chunks with metadata
    """
    from .cpso_triage import get_policy_url

    logger.info(f"Retrieving overviews for {len(policy_ids)} policies")

    # Get URLs for policy IDs
    policy_urls = []
    for policy_id in policy_ids:
        url = get_policy_url(policy_id)
        if url:
            policy_urls.append(url)
        else:
            logger.warning(f"No URL found for policy_id: {policy_id}")

    if not policy_urls:
        logger.warning("No valid policy URLs found")
        return []

    # Build metadata filter for parent chunks only
    # We want overviews, which are parent chunks
    where_filter = {
        "$and": [
            {"chunk_type": "parent"},  # Only parent chunks (overviews)
            {
                "$or": [
                    {"source_url": url}
                    for url in policy_urls
                ]
            }
        ]
    }

    # Search with filter
    try:
        search_results = await semantic_search.search(
            query=query,
            sources=['cpso'],
            k=k * 3,  # Get more to ensure coverage
            use_reranking=True,
            use_hybrid=False,
            use_ce_reranking=False,
            where_filter=where_filter  # Custom filter
        )

        logger.info(f"Found {len(search_results)} overview chunks")

        # Format results
        formatted_results = semantic_search.format_results(search_results)

        # Deduplicate to max 2 chunks per policy
        by_policy = defaultdict(list)
        for result in formatted_results:
            url = result.get('source_url', '')
            by_policy[url].append(result)

        # Take top 2 from each policy
        deduplicated = []
        for url, chunks in by_policy.items():
            # Sort by relevance score
            chunks.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            deduplicated.extend(chunks[:2])

        # Sort all by relevance
        deduplicated.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        logger.info(f"Deduplicated to {len(deduplicated)} overview chunks")

        return deduplicated[:k]

    except Exception as e:
        logger.error(f"Overview retrieval failed: {e}")
        return []


async def retrieve_detailed_chunks(
    semantic_search,
    query: str,
    policy_ids: List[str],
    policy_level: Optional[str] = None,
    k: int = 20
) -> List[Dict]:
    """
    Retrieve detailed requirement chunks for specific queries.

    Strategy:
    1. Search within scoped policies
    2. Filter by policy_level if specified (expectation vs advice)
    3. Include both parent and child chunks
    4. Assemble parent+child context

    Args:
        semantic_search: SemanticSearchEngine instance
        query: User query
        policy_ids: List of policy IDs to search
        policy_level: Optional filter ("expectation" or "advice")
        k: Maximum results

    Returns:
        List of detailed chunks with parent context
    """
    from .cpso_triage import get_policy_url

    logger.info(f"Retrieving detailed chunks for {len(policy_ids)} policies")
    logger.info(f"  Policy level filter: {policy_level}")

    # Get URLs for policy IDs
    policy_urls = []
    for policy_id in policy_ids:
        url = get_policy_url(policy_id)
        if url:
            policy_urls.append(url)
        else:
            logger.warning(f"No URL found for policy_id: {policy_id}")

    if not policy_urls:
        logger.warning("No valid policy URLs found")
        return []

    # Build metadata filter
    filters = []

    # Filter by policy URLs
    url_filter = {
        "$or": [
            {"source_url": url}
            for url in policy_urls
        ]
    }
    filters.append(url_filter)

    # Filter by policy level if specified
    if policy_level and policy_level in ['expectation', 'advice']:
        filters.append({"policy_level": policy_level})

    # Combine filters
    if len(filters) > 1:
        where_filter = {"$and": filters}
    else:
        where_filter = filters[0]

    # Search with filter
    try:
        search_results = await semantic_search.search(
            query=query,
            sources=['cpso'],
            k=k * 2,  # Get more for processing
            use_reranking=True,
            use_hybrid=False,
            use_ce_reranking=False,
            where_filter=where_filter
        )

        logger.info(f"Found {len(search_results)} detailed chunks")

        # Format results
        formatted_results = semantic_search.format_results(search_results)

        # Assemble parent+child context
        assembled = await assemble_parent_child_context(
            semantic_search,
            formatted_results
        )

        logger.info(f"Assembled {len(assembled)} chunks with context")

        return assembled[:k]

    except Exception as e:
        logger.error(f"Detailed retrieval failed: {e}")
        return []


async def assemble_parent_child_context(
    semantic_search,
    chunks: List[Dict]
) -> List[Dict]:
    """
    For child chunks, fetch parent and prepend context.

    Args:
        semantic_search: SemanticSearchEngine instance
        chunks: List of retrieved chunks

    Returns:
        List of chunks with parent context assembled
    """
    assembled = []
    parent_cache = {}  # Cache parent chunks

    for chunk in chunks:
        chunk_type = chunk.get('chunk_type', 'unknown')

        if chunk_type == 'parent':
            # Parent chunk - include as-is
            assembled.append(chunk)

        elif chunk_type == 'child':
            # Child chunk - need to fetch parent
            parent_id = chunk.get('parent_id')

            if not parent_id:
                # No parent ID - include child as-is
                logger.warning(f"Child chunk has no parent_id: {chunk.get('chunk_id')}")
                assembled.append(chunk)
                continue

            # Get parent from cache or fetch
            if parent_id not in parent_cache:
                try:
                    # Fetch parent chunk from ChromaDB
                    vector_client = semantic_search.vector_client
                    parent_result = vector_client.collection.get(
                        ids=[parent_id],
                        include=['documents', 'metadatas']
                    )

                    if parent_result['documents']:
                        parent_cache[parent_id] = {
                            'text': parent_result['documents'][0],
                            'metadata': parent_result['metadatas'][0]
                        }
                    else:
                        logger.warning(f"Parent not found: {parent_id}")
                        parent_cache[parent_id] = None

                except Exception as e:
                    logger.error(f"Failed to fetch parent {parent_id}: {e}")
                    parent_cache[parent_id] = None

            # Assemble parent + child
            parent_data = parent_cache.get(parent_id)

            if parent_data:
                # Prepend parent context to child text
                assembled_text = f"[PARENT CONTEXT]\n{parent_data['text']}\n\n[SPECIFIC DETAIL]\n{chunk['text']}"

                assembled_chunk = {
                    **chunk,
                    'text': assembled_text,
                    'parent_text': parent_data['text'],
                    'parent_metadata': parent_data['metadata'],
                    'has_parent_context': True
                }
                assembled.append(assembled_chunk)
            else:
                # No parent found - include child as-is
                assembled.append(chunk)

        else:
            # Unknown chunk type - include as-is
            assembled.append(chunk)

    return assembled


def format_policy_response(
    chunks: List[Dict],
    classification: Dict,
    query: str
) -> Dict:
    """
    Format response with policy-level metadata.

    Args:
        chunks: Retrieved chunks
        classification: Triage classification results
        query: Original query

    Returns:
        Formatted response dict with policy context
    """
    from .cpso_triage import get_policy_info

    # Get policy metadata for searched policies
    policy_context = []
    for policy_id in classification.get('relevant_policies', []):
        policy_info = get_policy_info(policy_id)
        if policy_info:
            policy_context.append({
                'policy_id': policy_id,
                'title': policy_info['policy_title'],
                'level': policy_info['policy_level'],
                'url': policy_info['source_url']
            })

    # Build summary based on intent
    intent = classification.get('intent', 'unknown')
    policy_count = len(classification.get('relevant_policies', []))

    if intent == 'policy_discovery':
        summary = f"Found {policy_count} relevant CPSO policies for: {query}"
    else:
        summary = f"Requirements from {policy_count} CPSO policy/policies for: {query}"

    # Create response
    response = {
        'classification': {
            'intent': classification.get('intent'),
            'scope': classification.get('scope'),
            'practice_domain': classification.get('practice_domain'),
            'policy_level_focus': classification.get('policy_level_focus'),
            'confidence': classification.get('confidence'),
            'reasoning': classification.get('reasoning')
        },
        'policy_context': policy_context,
        'items': chunks,
        'tools_searched': classification.get('relevant_policies', []),
        'summary': summary,
        'query_interpretation': f"Searching CPSO policies for: {query}"
    }

    return response


def deduplicate_by_policy(chunks: List[Dict], max_per_policy: int = 2) -> List[Dict]:
    """
    Deduplicate chunks to max N per policy.

    Args:
        chunks: List of chunks
        max_per_policy: Maximum chunks to keep per policy

    Returns:
        Deduplicated list
    """
    by_policy = defaultdict(list)

    for chunk in chunks:
        url = chunk.get('source_url', '')
        by_policy[url].append(chunk)

    deduplicated = []
    for url, policy_chunks in by_policy.items():
        # Sort by relevance
        policy_chunks.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        # Take top N
        deduplicated.extend(policy_chunks[:max_per_policy])

    # Sort all by relevance
    deduplicated.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

    return deduplicated


async def synthesize_compliance_answer(
    query: str,
    classification: Dict,
    retrieved_chunks: List[Dict],
    llm_client
) -> Dict:
    """
    Synthesize compliance answer from multiple policy chunks.

    Analyzes clinical practice scenario against CPSO policies to determine compliance.

    Args:
        query: User's compliance question or scenario
        classification: Triage classification results
        retrieved_chunks: Retrieved policy chunks
        llm_client: OpenAI client for LLM synthesis

    Returns:
        {
            "compliant": "yes" | "no" | "partial" | "unclear",
            "reasoning": "Brief explanation referencing specific policies",
            "requirements": ["List of requirements that must be met"],
            "non_compliance_risks": ["List of areas where practice may not comply"],
            "recommendations": ["Suggested actions to ensure compliance"],
            "relevant_policies": [{"policy": "Virtual Care", "section": "3.2", ...}],
            "confidence": 0.0-1.0
        }
    """
    logger.info("Synthesizing compliance answer for decisional query")

    # Build context from retrieved chunks (top 10 most relevant)
    policy_context = []
    for chunk in retrieved_chunks[:10]:
        metadata = chunk.get('metadata', {}) if 'metadata' in chunk else chunk
        policy_context.append({
            'policy': metadata.get('document_title', chunk.get('document_title', 'Unknown')),
            'policy_level': metadata.get('policy_level', chunk.get('policy_level', 'unknown')),
            'section': metadata.get('section_heading', chunk.get('section_heading', '')),
            'text': chunk.get('text', '')[:1000]  # Limit context per chunk
        })

    prompt = f"""You are a CPSO policy compliance advisor. Analyze this clinical practice scenario for CPSO compliance.

Scenario/Question:
{query}

Relevant CPSO Policy Excerpts:
{json.dumps(policy_context, indent=2)}

Analyze compliance and respond with JSON:
{{
    "compliant": "yes" | "no" | "partial" | "unclear",
    "reasoning": "<1-3 sentence explanation citing specific policy requirements>",
    "requirements": ["<list ALL requirements from policies that apply to this scenario>"],
    "non_compliance_risks": ["<areas where scenario may not comply>"],
    "recommendations": ["<specific actions to ensure compliance>"],
    "relevant_policies": [
        {{"policy": "<policy name>", "section": "<section ref>", "requirement_level": "expectation|advice"}}
    ],
    "confidence": <0.0-1.0>
}}

Guidelines:
- "yes" = practice clearly complies with all applicable policies
- "no" = practice clearly violates at least one expectation-level policy
- "partial" = complies with some requirements but not others
- "unclear" = insufficient information in policies or scenario to determine

Be conservative - if unclear, say so. Cite specific policy requirements in reasoning.
Focus on expectation-level policies (mandatory) over advice-level (guidance).
If scenario lacks critical details, note this in non_compliance_risks."""

    try:
        response = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        logger.info(f"Compliance synthesis result: {result.get('compliant', 'unknown')}")
        logger.info(f"  Confidence: {result.get('confidence', 0.0)}")

        return result

    except Exception as e:
        logger.error(f"Compliance synthesis error: {e}")
        return {
            "compliant": "unclear",
            "reasoning": "Error during compliance analysis",
            "requirements": [],
            "non_compliance_risks": ["Unable to complete analysis due to technical error"],
            "recommendations": ["Please consult CPSO policies directly", "Consider seeking legal or regulatory advice"],
            "relevant_policies": [],
            "confidence": 0.0
        }
