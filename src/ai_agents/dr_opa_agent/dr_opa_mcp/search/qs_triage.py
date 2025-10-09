"""
Ontario Health Quality Standards Triage using LLM Classification.

Implements two-tier retrieval for Ontario Health Quality Standards:
1. LLM classifies query intent and identifies relevant standards
2. Retrieval is scoped to those standards only

Author: AI Assistant
Date: 2025-10-07
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_quality_standards_catalog() -> List[Dict]:
    """
    Load Ontario Health quality standards catalog from JSON file.

    Returns:
        List of quality standard catalog entries with metadata
    """
    # Use code-relative path (works on both local and Railway)
    catalog_path = Path(__file__).parent.parent / "qs_catalog.json"

    if not catalog_path.exists():
        logger.error(f"Quality standards catalog not found at {catalog_path}")
        logger.error("Please run: python scripts/build_qs_catalog.py")
        raise FileNotFoundError(f"Quality standards catalog not found: {catalog_path}")

    with open(catalog_path) as f:
        catalog = json.load(f)

    logger.info(f"Loaded {len(catalog)} quality standards from catalog")
    return catalog


def get_standard_info(standard_id: str) -> Optional[Dict]:
    """
    Get full metadata for a specific quality standard.

    Args:
        standard_id: Standard ID (e.g., "diabetes", "copd")

    Returns:
        Standard metadata dict or None if not found
    """
    catalog = load_quality_standards_catalog()

    for entry in catalog:
        if entry['standard_id'] == standard_id:
            return entry

    return None


def get_standard_title(standard_id: str) -> Optional[str]:
    """
    Get title for a standard ID.

    Args:
        standard_id: Standard ID

    Returns:
        Standard title or None if not found
    """
    standard = get_standard_info(standard_id)
    return standard['standard_title'] if standard else None


def detect_decisional_intent(query: str) -> bool:
    """
    Detect if query expects practice validation vs informational lookup.

    Decisional queries ask for practice validation:
    - "Is this aligned...?"
    - "Is this appropriate...?"
    - "Does this meet...?"
    - Treatment/practice descriptions

    Args:
        query: User query

    Returns:
        True if decisional, False if informational
    """
    # Decisional keyword patterns for Quality Standards
    decisional_patterns = [
        r'\bis\s+this\s+aligned\b',
        r'\bis\s+this\s+appropriate\b',
        r'\bdoes\s+this\s+meet\b',
        r'\bshould\s+i\b',
        r'\bis\s+this\s+recommended\b',
        r'\bdoes\s+this\s+follow\b',
        r'\bis\s+.*\s+appropriate\b'
    ]

    query_lower = query.lower()

    # Check for decisional keyword patterns
    for pattern in decisional_patterns:
        if re.search(pattern, query_lower):
            logger.debug(f"Decisional pattern matched: {pattern}")
            return True

    # Check for patient/treatment scenario descriptions
    practice_indicators = ['patient', 'treatment', 'considering', 'plan', 'management']
    if any(indicator in query_lower for indicator in practice_indicators):
        # Check if asking about appropriateness/alignment
        if any(word in query_lower for word in ['appropriate', 'aligned', 'meet', 'follow', 'standard']):
            logger.debug("Practice scenario with validation query detected")
            return True

    # Check for multi-line scenario descriptions
    if "\n" in query and len(query.split("\n")) > 2:
        logger.debug("Multi-line practice scenario detected")
        return True

    return False


async def classify_quality_standards_query(query: str, openai_client) -> Dict:
    """
    Classify Ontario Health quality standards query and identify relevant standards using LLM.

    Args:
        query: User's clinical question or topic
        openai_client: OpenAI client instance

    Returns:
        {
            "intent": "standard_discovery" | "specific_indicator",
            "relevant_standards": ["standard_id1", "standard_id2"],
            "scope": "single" | "multiple" | "all",
            "clinical_domain": "mental_health" | ...,
            "query_focus": "overview" | "statements" | "indicators" | "implementation",
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }
    """
    catalog = load_quality_standards_catalog()

    # Create a concise catalog summary for the LLM
    # (Full catalog is too large for prompt - just send key fields)
    catalog_summary = []
    for entry in catalog:
        catalog_summary.append({
            "standard_id": entry['standard_id'],
            "title": entry['standard_title'],
            "domain": entry['clinical_domain'],
            "conditions": entry['conditions'][:3],  # Limit conditions
            "care_focus": entry['care_focus'][:3],  # Limit care focus
            "aliases": entry['aliases'][:3],  # Limit aliases
            "statements": entry['statement_count']
        })

    prompt = f"""You are an Ontario Health quality standards classifier for healthcare providers.

User query: "{query}"

Available Ontario Health Quality Standards ({len(catalog_summary)} total):
{json.dumps(catalog_summary, indent=2)}

Classify this query:

1. **Intent**:
   - "standard_discovery": User wants to know WHAT quality standards exist (broad question)
   - "specific_indicator": User has a specific quality indicator/statement question (deep question)

2. **Relevant Standards**: Which standard(s) (1-5 max) from the catalog are most relevant?
   - Use standard_id field
   - If the query matches multiple standards, include all relevant ones
   - If unclear, prefer returning more standards (better recall)

3. **Scope**:
   - "single": One specific standard clearly matches
   - "multiple": 2-5 related standards are relevant
   - "all": User wants to browse ALL available standards (catalog query)

4. **Query Focus**: What aspect of quality standards?
   - "overview": General information about the standard
   - "statements": Specific quality statements
   - "indicators": Quality indicators/measures
   - "implementation": How to implement the standard

5. **Clinical Domain**: Which domain best matches the query?
   - "mental_health", "respiratory", "neurology_cognitive", "endocrine_metabolic",
   - "cardiovascular", "musculoskeletal", "womens_health", "dermatology",
   - "palliative_care", "transitions_care", "general"

Respond with JSON ONLY (no explanation before or after):
{{
    "intent": "standard_discovery" | "specific_indicator",
    "scope": "single" | "multiple" | "all",
    "relevant_standards": ["standard_id1", "standard_id2"],
    "clinical_domain": "domain_name",
    "query_focus": "overview" | "statements" | "indicators" | "implementation",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation in 1-2 sentences"
}}

Examples:

Query: "List all Ontario Health quality standards"
Response: {{"intent": "standard_discovery", "scope": "all", "relevant_standards": [], "clinical_domain": "general", "query_focus": "overview", "confidence": 0.98, "reasoning": "User wants to browse the complete catalog of all available quality standards"}}

Query: "What quality standards exist for mental health?"
Response: {{"intent": "standard_discovery", "scope": "multiple", "relevant_standards": ["alcohol_use_disorder", "anxiety_disorders", "depression", "schizophrenia", "opioid"], "clinical_domain": "mental_health", "query_focus": "overview", "confidence": 0.95, "reasoning": "User wants to discover mental health quality standards"}}

Query: "What are the quality indicators for diabetes care?"
Response: {{"intent": "specific_indicator", "scope": "single", "relevant_standards": ["diabetes"], "clinical_domain": "endocrine_metabolic", "query_focus": "indicators", "confidence": 0.9, "reasoning": "User asks about specific diabetes quality indicators"}}

Query: "How do I implement COPD quality standards in primary care?"
Response: {{"intent": "specific_indicator", "scope": "single", "relevant_standards": ["copd"], "clinical_domain": "respiratory", "query_focus": "implementation", "confidence": 0.92, "reasoning": "User asks about implementing COPD standards"}}

Query: "What standards apply to respiratory conditions?"
Response: {{"intent": "standard_discovery", "scope": "multiple", "relevant_standards": ["copd", "asthma_in_adults"], "clinical_domain": "respiratory", "query_focus": "overview", "confidence": 0.88, "reasoning": "User wants respiratory quality standards overview"}}

Now classify the user's query:"""

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise quality standards classifier. Return only valid JSON."
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
        required_fields = ['intent', 'relevant_standards', 'scope', 'query_focus', 'confidence']
        for field in required_fields:
            if field not in classification:
                logger.warning(f"Missing required field '{field}' in classification")
                if field == 'relevant_standards':
                    classification[field] = []
                elif field == 'query_focus':
                    classification[field] = 'statements'
                else:
                    classification[field] = None

        # Ensure confidence is a float
        if not isinstance(classification.get('confidence'), (int, float)):
            classification['confidence'] = 0.5

        # Ensure relevant_standards is a list
        if not isinstance(classification.get('relevant_standards'), list):
            classification['relevant_standards'] = []

        # Add decisional intent detection
        classification['is_decisional'] = detect_decisional_intent(query)

        # Set query_type based on decisional flag
        if classification['is_decisional']:
            classification['query_type'] = 'practice_validation'
        else:
            classification['query_type'] = 'standard_lookup'

        # Log classification
        logger.info(f"Query classified as: {classification['intent']}")
        logger.info(f"  Query type: {classification['query_type']} (decisional={classification['is_decisional']})")
        logger.info(f"  Relevant standards: {classification['relevant_standards']}")
        logger.info(f"  Query focus: {classification['query_focus']}")
        logger.info(f"  Confidence: {classification['confidence']}")

        return classification

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response content: {content}")

        # Return fallback classification
        return {
            "intent": "specific_indicator",
            "scope": "all",
            "relevant_standards": [],
            "clinical_domain": "general",
            "query_focus": "statements",
            "confidence": 0.3,
            "reasoning": "LLM classification failed, using fallback"
        }

    except Exception as e:
        logger.error(f"Classification failed: {e}")

        # Return fallback classification
        return {
            "intent": "specific_indicator",
            "scope": "all",
            "relevant_standards": [],
            "clinical_domain": "general",
            "query_focus": "statements",
            "confidence": 0.3,
            "reasoning": f"Classification error: {str(e)}"
        }


# Query cache for testing (simple dict-based cache)
_query_cache = {}


async def classify_quality_standards_query_cached(query: str, openai_client) -> Dict:
    """
    Cached version of classify_quality_standards_query for testing.

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
    classification = await classify_quality_standards_query(query, openai_client)

    # Cache result
    _query_cache[query_key] = classification

    return classification
