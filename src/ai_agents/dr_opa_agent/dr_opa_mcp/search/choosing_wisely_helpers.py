"""
Choosing Wisely Specialty-Scoped Retrieval Helpers.

Helper functions for two-tier Choosing Wisely retrieval:
- Specialty overview retrieval (for discovery queries)
- Detailed recommendation retrieval (for specific queries)
- Complete specialty retrieval (for "all recommendations" mode)
- Parent-child context assembly
- Decisional synthesis (binary recommendations)

Author: AI Assistant
Date: 2025-10-07
"""

import json
import logging
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


async def retrieve_specialty_overviews(
    semantic_search,
    query: str,
    specialty_ids: List[str],
    k: int = 10
) -> List[Dict]:
    """
    Retrieve specialty overview chunks for discovery queries.

    Strategy:
    1. Get parent chunks from relevant specialties
    2. Deduplicate to 1 overview per specialty
    3. Sort by relevance

    Args:
        semantic_search: SemanticSearchEngine instance
        query: User query
        specialty_ids: List of specialty IDs to search
        k: Maximum results

    Returns:
        List of overview chunks with metadata
    """
    from .choosing_wisely_triage import get_specialty_name

    logger.info(f"Retrieving overviews for {len(specialty_ids)} specialties")

    # Get specialty names for filtering
    specialty_names = []
    for specialty_id in specialty_ids:
        name = get_specialty_name(specialty_id)
        if name:
            specialty_names.append(name)
        else:
            logger.warning(f"No name found for specialty_id: {specialty_id}")

    if not specialty_names:
        logger.warning("No valid specialty names found")
        return []

    # Build metadata filter for parent chunks only
    # We want overviews, which are parent chunks
    where_filter = {
        "$and": [
            {"chunk_type": "parent"},  # Only parent chunks (overviews)
            {
                "$or": [
                    {"specialty": name}
                    for name in specialty_names
                ]
            }
        ]
    }

    # Search with filter
    try:
        search_results = await semantic_search.search(
            query=query,
            sources=['choosing_wisely'],
            k=k * 2,  # Get more to ensure coverage
            use_reranking=True,
            use_hybrid=False,
            use_ce_reranking=False,
            where_filter=where_filter  # Custom filter
        )

        logger.info(f"Found {len(search_results)} overview chunks")

        # Format results
        formatted_results = semantic_search.format_results(search_results)

        # Deduplicate to 1 chunk per specialty
        by_specialty = defaultdict(list)
        for result in formatted_results:
            specialty = result.get('specialty', '')
            by_specialty[specialty].append(result)

        # Take top 1 from each specialty
        deduplicated = []
        for specialty, chunks in by_specialty.items():
            # Sort by relevance score
            chunks.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            deduplicated.append(chunks[0])

        # Sort all by relevance
        deduplicated.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        logger.info(f"Deduplicated to {len(deduplicated)} overview chunks (1 per specialty)")

        return deduplicated[:k]

    except Exception as e:
        logger.error(f"Overview retrieval failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


async def retrieve_detailed_recommendations(
    semantic_search,
    query: str,
    specialty_ids: List[str],
    k: int = 20
) -> List[Dict]:
    """
    Retrieve specific recommendation chunks for clinical scenario queries.

    Strategy:
    1. Search within scoped specialties
    2. Include both parent and child chunks
    3. Prioritize child chunks (individual recommendations)
    4. Assemble parent+child context

    Args:
        semantic_search: SemanticSearchEngine instance
        query: User query
        specialty_ids: List of specialty IDs to search
        k: Maximum results

    Returns:
        List of detailed recommendation chunks with parent context
    """
    from .choosing_wisely_triage import get_specialty_name

    logger.info(f"Retrieving detailed recommendations for {len(specialty_ids)} specialties")

    # Get specialty names for filtering
    specialty_names = []
    for specialty_id in specialty_ids:
        name = get_specialty_name(specialty_id)
        if name:
            specialty_names.append(name)
        else:
            logger.warning(f"No name found for specialty_id: {specialty_id}")

    if not specialty_names:
        logger.warning("No valid specialty names found")
        return []

    # Build metadata filter - search all chunks in these specialties
    where_filter = {
        "$or": [
            {"specialty": name}
            for name in specialty_names
        ]
    }

    # Search with filter
    try:
        search_results = await semantic_search.search(
            query=query,
            sources=['choosing_wisely'],
            k=k * 2,  # Get more for processing
            use_reranking=True,
            use_hybrid=False,
            use_ce_reranking=False,
            where_filter=where_filter
        )

        logger.info(f"Found {len(search_results)} recommendation chunks")

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
        logger.error(f"Detailed recommendation retrieval failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


async def retrieve_complete_specialty(
    semantic_search,
    specialty_name: str
) -> List[Dict]:
    """
    Retrieve ALL chunks for a specialty (no semantic filtering).

    Use case: "Show me all Cardiology recommendations"

    Returns parent + all children for 100% coverage.

    Args:
        semantic_search: SemanticSearchEngine instance
        specialty_name: Display name of specialty (e.g., "Cardiology")

    Returns:
        List of all chunks for specialty
    """
    logger.info(f"Retrieving complete specialty: {specialty_name}")

    try:
        # Use ChromaDB .get() for exact filter (not semantic search)
        vector_client = semantic_search.vector_client
        collection = vector_client.collection

        results = collection.get(
            where={"specialty": {"$eq": specialty_name}},
            include=['documents', 'metadatas']
        )

        logger.info(f"Found {len(results['ids'])} total chunks for {specialty_name}")

        # Format as standard chunks
        formatted = []
        for chunk_id, doc, metadata in zip(
            results['ids'],
            results['documents'],
            results['metadatas']
        ):
            formatted.append({
                'chunk_id': chunk_id,
                'text': doc,
                'chunk_type': metadata.get('chunk_type', 'unknown'),
                'specialty': metadata.get('specialty', ''),
                'organization': metadata.get('organization', ''),
                'source_url': metadata.get('source_url', ''),
                'doc_type': metadata.get('doc_type', ''),
                'parent_id': metadata.get('parent_id'),
                'recommendation_count': metadata.get('recommendation_count'),
                'has_methodology': metadata.get('has_methodology') == 'True',
                'relevance_score': 1.0  # No scoring for complete retrieval
            })

        # Sort: parent first, then children
        parent_chunks = [c for c in formatted if c['chunk_type'] == 'parent']
        child_chunks = [c for c in formatted if c['chunk_type'] == 'child']

        sorted_chunks = parent_chunks + child_chunks

        logger.info(f"Sorted: {len(parent_chunks)} parent, {len(child_chunks)} children")

        return sorted_chunks

    except Exception as e:
        logger.error(f"Complete specialty retrieval failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
                assembled_text = f"[PARENT CONTEXT - {chunk.get('specialty', 'Unknown')}]\n{parent_data['text']}\n\n[SPECIFIC RECOMMENDATION]\n{chunk['text']}"

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


def format_choosing_wisely_response(
    chunks: List[Dict],
    classification: Dict,
    query: str
) -> Dict:
    """
    Format response with specialty-level metadata.

    Args:
        chunks: Retrieved chunks
        classification: Triage classification results
        query: Original query

    Returns:
        Formatted response dict with specialty context
    """
    from .choosing_wisely_triage import get_specialty_info

    # Get specialty metadata for searched specialties
    specialty_context = []
    for specialty_id in classification.get('relevant_specialties', []):
        specialty_info = get_specialty_info(specialty_id)
        if specialty_info:
            specialty_context.append({
                'specialty_id': specialty_id,
                'name': specialty_info['specialty_name'],
                'organization': specialty_info['organization'],
                'recommendation_count': specialty_info['recommendation_count'],
                'url': specialty_info['source_url']
            })

    # Build summary based on intent
    intent = classification.get('intent', 'unknown')
    specialty_count = len(classification.get('relevant_specialties', []))
    clinical_scenario = classification.get('clinical_scenario', 'general')

    if intent == 'specialty_discovery':
        summary = f"Found {specialty_count} relevant specialties with Choosing Wisely recommendations for: {query}"
    else:
        summary = f"Choosing Wisely recommendations from {specialty_count} specialty/specialties for: {clinical_scenario}"

    # Create response
    response = {
        'classification': {
            'intent': classification.get('intent'),
            'scope': classification.get('scope'),
            'clinical_scenario': classification.get('clinical_scenario'),
            'confidence': classification.get('confidence'),
            'reasoning': classification.get('reasoning')
        },
        'specialty_context': specialty_context,
        'recommendations': chunks,
        'specialties_searched': classification.get('relevant_specialties', []),
        'summary': summary,
        'query_interpretation': f"Searching Choosing Wisely recommendations for: {query}"
    }

    return response


def deduplicate_by_specialty(chunks: List[Dict], max_per_specialty: int = 1) -> List[Dict]:
    """
    Deduplicate chunks to max N per specialty.

    Args:
        chunks: List of chunks
        max_per_specialty: Maximum chunks to keep per specialty

    Returns:
        Deduplicated list
    """
    by_specialty = defaultdict(list)

    for chunk in chunks:
        specialty = chunk.get('specialty', '')
        by_specialty[specialty].append(chunk)

    deduplicated = []
    for specialty, specialty_chunks in by_specialty.items():
        # Sort by relevance
        specialty_chunks.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        # Take top N
        deduplicated.extend(specialty_chunks[:max_per_specialty])

    # Sort all by relevance
    deduplicated.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

    return deduplicated


async def synthesize_binary_recommendation(
    query: str,
    classification: Dict,
    retrieved_chunks: List[Dict],
    llm_client
) -> Dict:
    """
    Provide binary recommendation (avoid/consider/recommended) based on Choosing Wisely guidelines.

    Args:
        query: User's clinical scenario or test/procedure question
        classification: Triage classification results
        retrieved_chunks: Retrieved Choosing Wisely recommendation chunks
        llm_client: OpenAI client for LLM synthesis

    Returns:
        {
            "recommendation": "avoid" | "consider" | "recommended" | "insufficient_info",
            "reasoning": "Explanation citing Choosing Wisely recommendations",
            "supporting_recommendations": ["CW recommendations that apply"],
            "red_flags": ["Scenarios where recommendation would change"],
            "alternative_approaches": ["What to do instead if avoiding test/treatment"],
            "relevant_specialties": [{"specialty": "...", "recommendation": "..."}],
            "confidence": 0.0-1.0
        }
    """
    logger.info("Synthesizing binary recommendation for decisional query")

    # Build context from Choosing Wisely recommendations (top 8 most relevant)
    cw_context = []
    for chunk in retrieved_chunks[:8]:
        metadata = chunk.get('metadata', {}) if 'metadata' in chunk else chunk
        cw_context.append({
            'specialty': metadata.get('specialty', chunk.get('specialty', 'Unknown')),
            'organization': metadata.get('organization', chunk.get('organization', '')),
            'recommendation': chunk.get('text', '')[:800]
        })

    prompt = f"""You are a Choosing Wisely advisor. Evaluate whether this test/treatment/procedure is appropriate.

Clinical Scenario:
{query}

Relevant Choosing Wisely Recommendations:
{json.dumps(cw_context, indent=2)}

Provide recommendation in JSON:
{{
    "recommendation": "avoid" | "consider" | "recommended" | "insufficient_info",
    "reasoning": "<1-3 sentence explanation citing Choosing Wisely recommendations>",
    "supporting_recommendations": ["<CW recommendations that apply to this scenario>"],
    "red_flags": ["<clinical scenarios where recommendation would change - be specific>"],
    "alternative_approaches": ["<what to do instead if avoiding the test/treatment>"],
    "relevant_specialties": [
        {{"specialty": "<specialty>", "recommendation_summary": "<brief summary>"}}
    ],
    "confidence": <0.0-1.0>
}}

Guidelines:
- "avoid" = Choosing Wisely explicitly recommends against in this scenario
- "consider" = May be appropriate depending on additional factors not specified
- "recommended" = Scenario falls outside Choosing Wisely "avoid" categories (appropriate to order)
- "insufficient_info" = Choosing Wisely doesn't address this specific scenario

Remember: Choosing Wisely identifies tests/treatments to AVOID. If scenario doesn't match avoidance criteria, it may be appropriate.
Be specific about red flags - name the actual clinical findings that would change the recommendation."""

    try:
        response = await llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        logger.info(f"Binary recommendation result: {result.get('recommendation', 'unknown')}")
        logger.info(f"  Confidence: {result.get('confidence', 0.0)}")

        return result

    except Exception as e:
        logger.error(f"Binary recommendation synthesis error: {e}")
        return {
            "recommendation": "insufficient_info",
            "reasoning": "Error during recommendation analysis",
            "supporting_recommendations": [],
            "red_flags": [],
            "alternative_approaches": ["Please consult Choosing Wisely recommendations directly"],
            "relevant_specialties": [],
            "confidence": 0.0
        }
