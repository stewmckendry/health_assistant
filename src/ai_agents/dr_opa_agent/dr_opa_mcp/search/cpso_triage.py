"""
CPSO Policy Triage using LLM Classification.

Implements two-tier retrieval for CPSO policies:
1. LLM classifies query intent and identifies relevant policies
2. Retrieval is scoped to those policies only

Author: AI Assistant
Date: 2025-10-07
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache
import os

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_policy_catalog() -> List[Dict]:
    """
    Load CPSO policy catalog from JSON file.

    Returns:
        List of policy catalog entries with metadata
    """
    catalog_path = Path("data/dr_opa_agent/cpso_policy_catalog.json")

    if not catalog_path.exists():
        logger.error(f"Policy catalog not found at {catalog_path}")
        logger.error("Please run: python scripts/build_cpso_policy_catalog.py")
        raise FileNotFoundError(f"Policy catalog not found: {catalog_path}")

    with open(catalog_path) as f:
        catalog = json.load(f)

    logger.info(f"Loaded {len(catalog)} policies from catalog")
    return catalog


def get_policy_info(policy_id: str) -> Optional[Dict]:
    """
    Get full metadata for a specific policy.

    Args:
        policy_id: Policy ID (e.g., "virtual_care")

    Returns:
        Policy metadata dict or None if not found
    """
    catalog = load_policy_catalog()

    for entry in catalog:
        if entry['policy_id'] == policy_id:
            return entry

    return None


def get_policy_url(policy_id: str) -> Optional[str]:
    """
    Get source URL for a policy ID.

    Args:
        policy_id: Policy ID

    Returns:
        Source URL or None if not found
    """
    policy = get_policy_info(policy_id)
    return policy['source_url'] if policy else None


async def classify_cpso_query(query: str, openai_client) -> Dict:
    """
    Classify CPSO query and identify relevant policies using LLM.

    Args:
        query: User's clinical question or practice query
        openai_client: OpenAI client instance

    Returns:
        {
            "intent": "policy_discovery" | "specific_requirement",
            "relevant_policies": ["policy_id1", "policy_id2"],
            "scope": "single" | "multiple" | "all",
            "practice_domain": "service_delivery" | ...,
            "policy_level_focus": "expectation" | "advice" | "both",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }
    """
    catalog = load_policy_catalog()

    # Create a concise catalog summary for the LLM
    # (Full catalog is too large for prompt - just send key fields)
    catalog_summary = []
    for entry in catalog:
        catalog_summary.append({
            "policy_id": entry['policy_id'],
            "title": entry['policy_title'],
            "domain": entry['practice_domain'],
            "level": entry['policy_level'],
            "topics": entry['topics'][:5],  # Limit topics
            "aliases": entry['aliases'][:3]  # Limit aliases
        })

    prompt = f"""You are a CPSO policy classifier for Ontario physicians.

User query: "{query}"

Available CPSO Policies ({len(catalog_summary)} total):
{json.dumps(catalog_summary, indent=2)}

Classify this query:

1. **Intent**:
   - "policy_discovery": User wants to know WHAT policies exist (broad question)
   - "specific_requirement": User has a specific compliance question (deep question)

2. **Relevant Policies**: Which policy/policies (1-5 max) from the catalog are most relevant?
   - Use policy_id field
   - If the query matches multiple policies, include all relevant ones
   - If unclear, prefer returning more policies (better recall)

3. **Scope**:
   - "single": One specific policy clearly matches
   - "multiple": 2-5 related policies are relevant
   - "all": Query is too broad for specific policies (rare)

4. **Policy Level Focus**:
   - "expectation": Query focuses on mandatory requirements ("must" statements)
   - "advice": Query focuses on professional guidance ("advised" statements)
   - "both": Query doesn't specify, or needs both types

5. **Practice Domain**: Which domain best matches the query?
   - "service_delivery", "patient_interaction", "prescribing_treatment",
   - "professional_conduct", "administrative", "delegation_supervision", "general"

Respond with JSON ONLY (no explanation before or after):
{{
    "intent": "policy_discovery" | "specific_requirement",
    "scope": "single" | "multiple" | "all",
    "relevant_policies": ["policy_id1", "policy_id2"],
    "practice_domain": "domain_name",
    "policy_level_focus": "expectation" | "advice" | "both",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation in 1-2 sentences"
}}

Examples:

Query: "What CPSO policies exist for virtual care?"
Response: {{"intent": "policy_discovery", "scope": "multiple", "relevant_policies": ["virtual_care", "advice_to_the_profession_virtual_care", "consent_to_treatment"], "practice_domain": "service_delivery", "policy_level_focus": "both", "confidence": 0.95, "reasoning": "User wants to discover policies related to virtual care"}}

Query: "What are the consent requirements for virtual care?"
Response: {{"intent": "specific_requirement", "scope": "single", "relevant_policies": ["virtual_care"], "practice_domain": "service_delivery", "policy_level_focus": "expectation", "confidence": 0.9, "reasoning": "User asks about specific requirements within virtual care policy"}}

Query: "What policies apply to prescribing opioids?"
Response: {{"intent": "policy_discovery", "scope": "multiple", "relevant_policies": ["prescribing_drugs", "advice_to_the_profession_prescribing_drugs"], "practice_domain": "prescribing_treatment", "policy_level_focus": "expectation", "confidence": 0.92, "reasoning": "User wants to know which prescribing policies cover opioids"}}

Now classify the user's query:"""

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise CPSO policy classifier. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
            max_tokens=300
        )

        # Parse response
        content = response.choices[0].message.content.strip()

        # Remove markdown code blocks if present
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()

        classification = json.loads(content)

        # Validate required fields
        required_fields = ['intent', 'relevant_policies', 'scope', 'confidence']
        for field in required_fields:
            if field not in classification:
                logger.warning(f"Missing required field '{field}' in classification")
                classification[field] = None if field != 'relevant_policies' else []

        # Ensure confidence is a float
        if not isinstance(classification.get('confidence'), (int, float)):
            classification['confidence'] = 0.5

        # Ensure relevant_policies is a list
        if not isinstance(classification.get('relevant_policies'), list):
            classification['relevant_policies'] = []

        # Log classification
        logger.info(f"Query classified as: {classification['intent']}")
        logger.info(f"  Relevant policies: {classification['relevant_policies']}")
        logger.info(f"  Confidence: {classification['confidence']}")

        return classification

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response content: {content}")

        # Return fallback classification
        return {
            "intent": "specific_requirement",
            "scope": "all",
            "relevant_policies": [],
            "practice_domain": "general",
            "policy_level_focus": "both",
            "confidence": 0.3,
            "reasoning": "LLM classification failed, using fallback"
        }

    except Exception as e:
        logger.error(f"Classification failed: {e}")

        # Return fallback classification
        return {
            "intent": "specific_requirement",
            "scope": "all",
            "relevant_policies": [],
            "practice_domain": "general",
            "policy_level_focus": "both",
            "confidence": 0.3,
            "reasoning": f"Classification error: {str(e)}"
        }


# Query cache for testing (simple dict-based cache)
_query_cache = {}


async def classify_cpso_query_cached(query: str, openai_client) -> Dict:
    """
    Cached version of classify_cpso_query for testing.

    Args:
        query: User query
        openai_client: OpenAI client

    Returns:
        Classification dict
    """
    # Normalize query for caching
    query_key = query.lower().strip()

    if query_key in _query_cache:
        logger.info(f"Using cached classification for query: {query[:50]}...")
        return _query_cache[query_key]

    # Classify
    classification = await classify_cpso_query(query, openai_client)

    # Cache result
    _query_cache[query_key] = classification

    return classification
