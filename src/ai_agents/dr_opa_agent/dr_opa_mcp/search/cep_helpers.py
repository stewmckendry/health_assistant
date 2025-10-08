"""
CEP Tool-Scoped Retrieval Helpers.

Helper functions for two-tier CEP clinical tool retrieval:
- Tool overview retrieval (for discovery queries)
- Detailed chunk retrieval (for specific queries)
- Parent-child context assembly

Adapted from CPSO helpers.

Author: AI Assistant
Date: 2025-10-07
"""

import logging
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


async def retrieve_tool_overviews(
    semantic_search,
    query: str,
    tool_ids: List[str],
    k: int = 10
) -> List[Dict]:
    """
    Retrieve clinical tool overview chunks for discovery queries.

    Strategy:
    1. Get parent chunks (especially is_overview=True) from relevant tools
    2. Deduplicate to 1-2 overviews per tool
    3. Sort by relevance

    Args:
        semantic_search: SemanticSearchEngine instance
        query: User query
        tool_ids: List of tool IDs to search
        k: Maximum results

    Returns:
        List of overview chunks with metadata
    """
    from .cep_triage import get_tool_url

    logger.info(f"Retrieving overviews for {len(tool_ids)} clinical tools")

    # Get URLs for tool IDs
    tool_urls = []
    for tool_id in tool_ids:
        url = get_tool_url(tool_id)
        if url:
            tool_urls.append(url)
        else:
            logger.warning(f"No URL found for tool_id: {tool_id}")

    if not tool_urls:
        logger.warning("No valid tool URLs found")
        return []

    # Build metadata filter for overview chunks
    # Prioritize is_overview=True, but also include parent chunks
    where_filter = {
        "$and": [
            {"chunk_type": "parent"},  # Only parent chunks
            {
                "$or": [
                    {"source_url": url}
                    for url in tool_urls
                ]
            }
        ]
    }

    # Search with filter
    try:
        search_results = await semantic_search.search(
            query=query,
            sources=['cep'],
            k=k * 3,  # Get more to ensure coverage across tools
            use_reranking=False,
            use_hybrid=False,
            use_ce_reranking=True,
            where_filter=where_filter
        )

        logger.info(f"Found {len(search_results)} overview chunks")

        # Format results
        formatted_results = semantic_search.format_results(search_results)

        # Deduplicate to max 2 chunks per tool
        by_tool = defaultdict(list)
        for result in formatted_results:
            url = result.get('source_url', '')
            by_tool[url].append(result)

        # Take top 2 from each tool, prioritizing is_overview=True
        deduplicated = []
        for url, chunks in by_tool.items():
            # Sort: is_overview first, then by relevance score
            chunks.sort(
                key=lambda x: (
                    x.get('metadata', {}).get('is_overview', False) != True,  # False sorts before True
                    -x.get('relevance_score', 0)
                )
            )
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
    tool_ids: List[str],
    k: int = 20
) -> List[Dict]:
    """
    Retrieve detailed clinical guidance chunks for specific questions.

    Strategy:
    1. Search within scoped clinical tools
    2. Include both parent and child chunks
    3. Assemble parent+child context for child chunks

    Args:
        semantic_search: SemanticSearchEngine instance
        query: User query
        tool_ids: List of tool IDs to search
        k: Maximum results

    Returns:
        List of detailed chunks with parent context
    """
    from .cep_triage import get_tool_url

    logger.info(f"Retrieving detailed chunks for {len(tool_ids)} clinical tools")

    # Get URLs for tool IDs
    tool_urls = []
    for tool_id in tool_ids:
        url = get_tool_url(tool_id)
        if url:
            tool_urls.append(url)
        else:
            logger.warning(f"No URL found for tool_id: {tool_id}")

    if not tool_urls:
        logger.warning("No valid tool URLs found")
        return []

    # Build metadata filter for tool scope
    # Include both parent and child chunks
    where_filter = {
        "$or": [
            {"source_url": url}
            for url in tool_urls
        ]
    }

    # Search with filter
    try:
        search_results = await semantic_search.search(
            query=query,
            sources=['cep'],
            k=k * 2,  # Get more for processing
            use_reranking=False,
            use_hybrid=False,
            use_ce_reranking=True,
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


def format_tool_response(
    tools_data: List[Dict],
    classification: Dict,
    query: str
) -> Dict:
    """
    Format tool retrieval results into standard response.

    Args:
        tools_data: Retrieved chunks
        classification: Triage classification
        query: Original query

    Returns:
        Formatted response dict
    """
    # Group chunks by tool
    by_tool = defaultdict(list)
    for chunk in tools_data:
        url = chunk.get('source_url', '')
        by_tool[url].append(chunk)

    logger.info(f"Formatting {len(tools_data)} chunks from {len(by_tool)} tools")

    # Build response
    response = {
        'items': tools_data,
        'total_tools': len(by_tool),
        'tools_searched': classification.get('relevant_tools', []),
        'query_interpretation': f"Searching CEP clinical tools for: {query}",
        'intent': classification.get('intent'),
        'confidence': classification.get('confidence', 0.8)
    }

    return response
