"""
Catalog fallback and semantic similarity utilities.

When LLM triage returns no relevant tools/policies/standards,
provide semantic similarity-based suggestions to improve UX.

Author: AI Assistant
Date: 2025-10-08
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


async def compute_catalog_similarity(
    query: str,
    catalog: List[Dict],
    openai_client,
    catalog_type: str,
    top_k: int = 3,
    min_similarity: float = 0.40
) -> List[Dict]:
    """
    Compute semantic similarity between query and catalog entries.

    Args:
        query: User's query
        catalog: List of catalog entries (tools/policies/standards)
        openai_client: OpenAI client for embeddings
        catalog_type: "cep_tools" | "cpso_policies" | "quality_standards" | "choosing_wisely"
        top_k: Number of suggestions to return
        min_similarity: Minimum cosine similarity threshold

    Returns:
        List of top-k similar catalog entries with scores
    """
    logger.info(f"Computing semantic similarity for catalog_type={catalog_type}, query='{query}'")

    try:
        # Get query embedding
        query_response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        query_embedding = np.array(query_response.data[0].embedding)

        # Compute similarities
        similarities = []
        for entry in catalog:
            # Build searchable text from catalog entry
            searchable_text = build_catalog_searchable_text(entry, catalog_type)

            if not searchable_text:
                continue

            # Get catalog entry embedding
            entry_response = await openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=searchable_text
            )
            entry_embedding = np.array(entry_response.data[0].embedding)

            # Compute cosine similarity
            similarity = np.dot(query_embedding, entry_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(entry_embedding)
            )

            if similarity >= min_similarity:
                similarities.append({
                    'entry': entry,
                    'similarity': float(similarity),
                    'searchable_text': searchable_text
                })

        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        top_results = similarities[:top_k]

        logger.info(f"Found {len(similarities)} items above threshold, returning top {len(top_results)}")

        return top_results

    except Exception as e:
        logger.error(f"Error computing catalog similarity: {e}", exc_info=True)
        return []


def build_catalog_searchable_text(entry: Dict, catalog_type: str) -> str:
    """
    Build searchable text from catalog entry fields.

    Args:
        entry: Catalog entry dict
        catalog_type: Type of catalog

    Returns:
        Searchable text string
    """
    # CEP clinical tools
    if catalog_type == "cep_tools":
        parts = [
            entry.get('tool_name', ''),
            entry.get('clinical_domain', ''),
            ', '.join(entry.get('conditions', [])),
            ', '.join(entry.get('capabilities', [])),
            ', '.join(entry.get('topics', []))
        ]
        return ' '.join(filter(None, parts))

    # CPSO policies
    elif catalog_type == "cpso_policies":
        parts = [
            entry.get('policy_title', ''),
            entry.get('practice_domain', ''),
            ', '.join(entry.get('topics', [])),
            ', '.join(entry.get('key_requirements', []))
        ]
        return ' '.join(filter(None, parts))

    # Ontario Health Quality Standards
    elif catalog_type == "quality_standards":
        parts = [
            entry.get('standard_title', ''),
            entry.get('clinical_domain', ''),
            ', '.join(entry.get('conditions', [])),
            ', '.join(entry.get('care_focus', [])),
            ', '.join(entry.get('key_statements', []))
        ]
        return ' '.join(filter(None, parts))

    # Choosing Wisely recommendations
    elif catalog_type == "choosing_wisely":
        parts = [
            entry.get('specialty_name', ''),
            entry.get('organization', ''),
            entry.get('clinical_domain', ''),
            ', '.join(entry.get('sample_recommendations', []))
        ]
        return ' '.join(filter(None, parts))

    return ''


def format_suggestions_response(
    query: str,
    suggestions: List[Dict],
    catalog_type: str
) -> str:
    """
    Format helpful response text with suggestions.

    Args:
        query: Original query
        suggestions: List of similar catalog entries with similarity scores
        catalog_type: "cep_tools" | "cpso_policies" | "quality_standards" | "choosing_wisely"

    Returns:
        Formatted response text
    """
    # Map catalog type to human-readable name
    catalog_names = {
        "cep_tools": "CEP clinical tools",
        "cpso_policies": "CPSO policies",
        "quality_standards": "Ontario Health quality standards",
        "choosing_wisely": "Choosing Wisely recommendations"
    }
    catalog_name = catalog_names.get(catalog_type, "items")

    if not suggestions:
        return f"No {catalog_name} found for: {query}"

    # Build response
    response_parts = [
        f"I couldn't find any {catalog_name} specifically for '{query}'.",
        "",
        "However, here are the closest matches:",
        ""
    ]

    for i, suggestion in enumerate(suggestions, 1):
        entry = suggestion['entry']
        similarity = suggestion['similarity']

        # Format based on catalog type
        if catalog_type == "cep_tools":
            name = entry.get('tool_name', 'Unknown Tool')
            domain = entry.get('clinical_domain', 'general')
            conditions = entry.get('conditions', [])
            condition_text = ', '.join(conditions[:2]) if conditions else ''

            response_parts.append(
                f"{i}. {name} ({domain})" +
                (f" - {condition_text}" if condition_text else "") +
                f" [similarity: {similarity:.2f}]"
            )

        elif catalog_type == "cpso_policies":
            name = entry.get('policy_title', 'Unknown Policy')
            domain = entry.get('practice_domain', 'general')
            level = entry.get('policy_level', '')

            response_parts.append(
                f"{i}. {name} ({domain})" +
                (f" - {level}" if level else "") +
                f" [similarity: {similarity:.2f}]"
            )

        elif catalog_type == "quality_standards":
            name = entry.get('standard_title', 'Unknown Standard')
            domain = entry.get('clinical_domain', 'general')
            conditions = entry.get('conditions', [])
            condition_text = ', '.join(conditions[:2]) if conditions else ''

            response_parts.append(
                f"{i}. {name} ({domain})" +
                (f" - {condition_text}" if condition_text else "") +
                f" [similarity: {similarity:.2f}]"
            )

        elif catalog_type == "choosing_wisely":
            specialty = entry.get('specialty_name', 'Unknown Specialty')
            org = entry.get('organization', '')
            recommendation_count = entry.get('recommendation_count', 0)

            response_parts.append(
                f"{i}. {specialty}" +
                (f" ({org})" if org else "") +
                f" - {recommendation_count} recommendations [similarity: {similarity:.2f}]"
            )

    response_parts.append("")
    response_parts.append("Would you like information on any of these?")

    return '\n'.join(response_parts)


def extract_catalog_entry_name(entry: Dict, catalog_type: str) -> str:
    """
    Extract the primary name/title from a catalog entry.

    Args:
        entry: Catalog entry dict
        catalog_type: Type of catalog

    Returns:
        Entry name/title
    """
    if catalog_type == "cep_tools":
        return entry.get('tool_name', 'Unknown Tool')
    elif catalog_type == "cpso_policies":
        return entry.get('policy_title', 'Unknown Policy')
    elif catalog_type == "quality_standards":
        return entry.get('standard_title', 'Unknown Standard')
    elif catalog_type == "choosing_wisely":
        return entry.get('specialty_name', 'Unknown Specialty')
    return 'Unknown'


def extract_catalog_entry_id(entry: Dict, catalog_type: str) -> str:
    """
    Extract the unique identifier from a catalog entry.

    Args:
        entry: Catalog entry dict
        catalog_type: Type of catalog

    Returns:
        Entry ID
    """
    if catalog_type == "cep_tools":
        return entry.get('tool_id', '')
    elif catalog_type == "cpso_policies":
        return entry.get('policy_id', '')
    elif catalog_type == "quality_standards":
        return entry.get('standard_id', '')
    elif catalog_type == "choosing_wisely":
        return entry.get('specialty_id', '')
    return ''
