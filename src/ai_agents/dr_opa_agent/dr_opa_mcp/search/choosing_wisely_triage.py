"""
Choosing Wisely Specialty Triage using LLM Classification.

Implements two-tier retrieval for Choosing Wisely recommendations:
1. LLM classifies query intent and identifies relevant specialties
2. Retrieval is scoped to those specialties only

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
def load_specialty_catalog() -> List[Dict]:
    """
    Load Choosing Wisely specialty catalog from JSON file.

    Returns:
        List of specialty catalog entries with metadata
    """
    catalog_path = Path("data/dr_opa_agent/choosing_wisely_specialty_catalog.json")

    if not catalog_path.exists():
        logger.error(f"Specialty catalog not found at {catalog_path}")
        logger.error("Please run: python scripts/build_choosing_wisely_catalog.py")
        raise FileNotFoundError(f"Specialty catalog not found: {catalog_path}")

    with open(catalog_path) as f:
        catalog = json.load(f)

    logger.info(f"Loaded {len(catalog)} specialties from catalog")
    return catalog


def get_specialty_info(specialty_id: str) -> Optional[Dict]:
    """
    Get full metadata for a specific specialty.

    Args:
        specialty_id: Specialty ID (e.g., "cardiology")

    Returns:
        Specialty metadata dict or None if not found
    """
    catalog = load_specialty_catalog()

    for entry in catalog:
        if entry['specialty_id'] == specialty_id:
            return entry

    return None


def get_specialty_name(specialty_id: str) -> Optional[str]:
    """
    Get display name for a specialty ID.

    Args:
        specialty_id: Specialty ID (e.g., "cardiology")

    Returns:
        Display name (e.g., "Cardiology") or None if not found
    """
    specialty = get_specialty_info(specialty_id)
    return specialty['specialty_name'] if specialty else None


async def classify_choosing_wisely_query(query: str, openai_client) -> Dict:
    """
    Classify Choosing Wisely query and identify relevant specialties using LLM.

    Args:
        query: User's clinical question or test/procedure query
        openai_client: OpenAI client instance

    Returns:
        {
            "intent": "specialty_discovery" | "specific_recommendation",
            "relevant_specialties": ["specialty_id1", "specialty_id2"],
            "scope": "single" | "multiple" | "all",
            "clinical_scenario": "extracted scenario or test name",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }
    """
    catalog = load_specialty_catalog()

    # Create a concise catalog summary for the LLM
    # (Full catalog is too large - send key fields only)
    catalog_summary = []
    for entry in catalog:
        catalog_summary.append({
            "specialty_id": entry['specialty_id'],
            "specialty_name": entry['specialty_name'],
            "aliases": entry['aliases'][:3],  # Limit aliases
            "clinical_domain": entry['clinical_domain'],
            "organization": entry['organization'],
            "common_scenarios": entry['common_scenarios'][:3],  # Top 3 scenarios
            "recommendation_count": entry['recommendation_count']
        })

    prompt = f"""You are a Choosing Wisely Canada specialty classifier.

User query: "{query}"

Available Medical Specialties ({len(catalog_summary)} total):
{json.dumps(catalog_summary, indent=2)}

Classify this query:

1. **Intent**:
   - "specialty_discovery": User wants to know WHAT specialties have recommendations (broad question)
   - "specific_recommendation": User has a specific clinical scenario question (deep question)

2. **Relevant Specialties**: Which specialty/specialties (1-5 max) from the catalog are most relevant?
   - Use specialty_id field
   - If the query matches multiple specialties, include all relevant ones
   - If unclear, prefer returning more specialties (better recall)
   - Consider: primary specialty + related specialties

3. **Scope**:
   - "single": One specific specialty clearly matches
   - "multiple": 2-5 related specialties are relevant
   - "all": Query is too broad for specific specialties (rare)

4. **Clinical Scenario**: Extract the clinical scenario, test, or procedure being questioned
   - Examples: "low_back_pain_imaging", "asymptomatic_ecg_screening", "antibiotic_sinusitis"
   - Be specific if possible, or use general category

Respond with JSON ONLY (no explanation before or after):
{{
    "intent": "specialty_discovery" | "specific_recommendation",
    "scope": "single" | "multiple" | "all",
    "relevant_specialties": ["specialty_id1", "specialty_id2"],
    "clinical_scenario": "extracted scenario or test name",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation in 1-2 sentences"
}}

Examples:

Query: "What Choosing Wisely recommendations exist for cardiology?"
Response: {{"intent": "specialty_discovery", "scope": "single", "relevant_specialties": ["cardiology"], "clinical_scenario": "cardiology_overview", "confidence": 0.95, "reasoning": "User wants to discover all cardiology recommendations"}}

Query: "What unnecessary tests should I avoid for low back pain?"
Response: {{"intent": "specific_recommendation", "scope": "multiple", "relevant_specialties": ["family_medicine", "emergency_medicine"], "clinical_scenario": "low_back_pain_imaging", "confidence": 0.9, "reasoning": "Low back pain imaging recommendations are in family medicine and emergency medicine"}}

Query: "Should I order routine ECGs for asymptomatic patients?"
Response: {{"intent": "specific_recommendation", "scope": "multiple", "relevant_specialties": ["cardiology", "family_medicine"], "clinical_scenario": "asymptomatic_ecg_screening", "confidence": 0.92, "reasoning": "ECG screening recommendations appear in both cardiology and primary care"}}

Query: "What imaging tests are unnecessary?"
Response: {{"intent": "specialty_discovery", "scope": "multiple", "relevant_specialties": ["radiology", "family_medicine", "emergency_medicine"], "clinical_scenario": "imaging_overuse", "confidence": 0.85, "reasoning": "Imaging overuse is addressed across multiple specialties"}}

Now classify the user's query:"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise Choosing Wisely specialty classifier. Return only valid JSON."
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
        required_fields = ['intent', 'relevant_specialties', 'scope', 'confidence']
        for field in required_fields:
            if field not in classification:
                logger.warning(f"Missing required field '{field}' in classification")
                classification[field] = None if field != 'relevant_specialties' else []

        # Ensure confidence is a float
        if not isinstance(classification.get('confidence'), (int, float)):
            classification['confidence'] = 0.5

        # Ensure relevant_specialties is a list
        if not isinstance(classification.get('relevant_specialties'), list):
            classification['relevant_specialties'] = []

        # Default clinical_scenario if missing
        if 'clinical_scenario' not in classification:
            classification['clinical_scenario'] = 'general'

        # Log classification
        logger.info(f"Query classified as: {classification['intent']}")
        logger.info(f"  Relevant specialties: {classification['relevant_specialties']}")
        logger.info(f"  Clinical scenario: {classification.get('clinical_scenario', 'N/A')}")
        logger.info(f"  Confidence: {classification['confidence']}")

        return classification

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response content: {content}")

        # Return fallback classification
        return {
            "intent": "specific_recommendation",
            "scope": "all",
            "relevant_specialties": [],
            "clinical_scenario": "unknown",
            "confidence": 0.3,
            "reasoning": "LLM classification failed, using fallback"
        }

    except Exception as e:
        logger.error(f"Classification failed: {e}")

        # Return fallback classification
        return {
            "intent": "specific_recommendation",
            "scope": "all",
            "relevant_specialties": [],
            "clinical_scenario": "unknown",
            "confidence": 0.3,
            "reasoning": f"Classification error: {str(e)}"
        }


# Query cache for testing (simple dict-based cache)
_query_cache = {}


async def classify_choosing_wisely_query_cached(query: str, openai_client) -> Dict:
    """
    Cached version of classify_choosing_wisely_query for testing.

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
    classification = await classify_choosing_wisely_query(query, openai_client)

    # Cache result
    _query_cache[query_key] = classification

    return classification
