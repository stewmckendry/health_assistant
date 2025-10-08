"""
CEP Clinical Tool Triage using LLM Classification.

Implements two-tier retrieval for CEP clinical tools:
1. LLM classifies query intent and identifies relevant tools
2. Retrieval is scoped to those tools only

Adapted from CPSO triage implementation.

Author: AI Assistant
Date: 2025-10-07
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_tool_catalog() -> List[Dict]:
    """
    Load CEP tool catalog from JSON file.

    Returns:
        List of tool catalog entries with metadata
    """
    catalog_path = Path(__file__).parent.parent / "cep_tool_catalog.json"

    if not catalog_path.exists():
        logger.error(f"Tool catalog not found at {catalog_path}")
        logger.error("Please run: python scripts/build_cep_tool_catalog.py")
        raise FileNotFoundError(f"Tool catalog not found: {catalog_path}")

    with open(catalog_path) as f:
        catalog = json.load(f)

    logger.info(f"Loaded {len(catalog)} clinical tools from catalog")
    return catalog


def get_tool_info(tool_id: str) -> Optional[Dict]:
    """
    Get full metadata for a specific tool.

    Args:
        tool_id: Tool ID (e.g., "management_of_chronic_non_cancer_pain")

    Returns:
        Tool metadata dict or None if not found
    """
    catalog = load_tool_catalog()

    for entry in catalog:
        if entry['tool_id'] == tool_id:
            return entry

    return None


def get_tool_url(tool_id: str) -> Optional[str]:
    """
    Get source URL for a tool ID.

    Args:
        tool_id: Tool ID

    Returns:
        Source URL or None if not found
    """
    tool = get_tool_info(tool_id)
    return tool['source_url'] if tool else None


async def classify_cep_query(query: str, openai_client) -> Dict:
    """
    Classify CEP query and identify relevant clinical tools using LLM.

    Args:
        query: User's clinical question
        openai_client: OpenAI client instance

    Returns:
        {
            "intent": "tool_discovery" | "specific_question",
            "relevant_tools": ["tool_id1", "tool_id2"],
            "scope": "single" | "multiple" | "all",
            "clinical_domain": "pain_management" | ...,
            "confidence": 0.0-1.0,
            "reasoning": "brief explanation"
        }
    """
    catalog = load_tool_catalog()

    # Create a concise catalog summary for the LLM
    # (Full catalog is too large for prompt - just send key fields)
    catalog_summary = []
    for entry in catalog:
        catalog_summary.append({
            "tool_id": entry['tool_id'],
            "tool_name": entry['tool_name'],
            "domain": entry['clinical_domain'],
            "conditions": entry['conditions'][:3],  # Limit conditions
            "capabilities": entry['capabilities'][:3],  # Limit capabilities
            "topics": entry['topics'][:3]  # Limit topics
        })

    prompt = f"""You are a CEP clinical tool classifier for Ontario primary care providers.

User query: "{query}"

Available CEP Clinical Tools ({len(catalog_summary)} total):
{json.dumps(catalog_summary, indent=2)}

Classify this query:

1. **Intent**:
   - "tool_discovery": User asks WHAT tools exist or wants to browse/discover tools
     Examples: "What CEP tools are available?", "Tools for diabetes?", "Does CEP have tools for X?"
   - "specific_question": User has a specific clinical question needing detailed guidance
     Examples: "What are diagnostic criteria?", "How do I screen for diabetes?", "What is the treatment pathway?"

   **Intent Detection Rules**:
   - If query ONLY asks "what tools", "does CEP have", "tools available" (without specific clinical terms) → tool_discovery
   - If query asks "how to", "what are criteria", "screening algorithm", "treatment pathway", "screening and treatment" → specific_question (even if mentions "tools")
   - If query mentions specific patient details (age, BMI, symptoms) → specific_question
   - If query contains both "tools" AND specific clinical terms ("screening", "treatment pathway", "diagnostic criteria") → specific_question (user wants detailed guidance, not just tool discovery)

2. **Relevant Tools**: Which tool(s) (1-3 max, strictly limit) from the catalog are most relevant?
   - Use tool_id field EXACTLY as shown in catalog
   - Match by: tool_name first, then conditions, then capabilities
   - ONLY include tools directly related to the query topic
   - Prefer fewer, more relevant tools over many loosely-related ones
   - For cardiovascular queries, ONLY include heart failure or obesity tools (CEP has no CV risk calculator)

3. **Scope**:
   - "single": One specific tool clearly matches
   - "multiple": 2-3 closely related tools
   - "all": Query is too broad for specific tools (rare)

4. **Clinical Domain**: Which domain best matches the query?
   - "pain_management", "mental_health", "cardiovascular", "respiratory",
   - "infectious_disease", "substance_use", "general"

Respond with JSON ONLY (no explanation before or after):
{{
    "intent": "tool_discovery" | "specific_question",
    "scope": "single" | "multiple" | "all",
    "relevant_tools": ["tool_id1", "tool_id2"],
    "clinical_domain": "domain_name",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation in 1-2 sentences"
}}

Examples:

Query: "What CEP tools are available for chronic pain management?"
Response: {{"intent": "tool_discovery", "scope": "multiple", "relevant_tools": ["management_of_chronic_non_cancer_pain", "opioid_tapering"], "clinical_domain": "pain_management", "confidence": 0.95, "reasoning": "User asks what tools are available - CNCP tool is primary, opioid tapering is related"}}

Query: "What are the diagnostic criteria for dementia?"
Response: {{"intent": "specific_question", "scope": "single", "relevant_tools": ["dementia_diagnosis"], "clinical_domain": "mental_health", "confidence": 0.95, "reasoning": "User asks specific diagnostic criteria question, dementia diagnosis tool provides this"}}

Query: "What is the diabetes screening algorithm for a 45-year-old with BMI 32?"
Response: {{"intent": "specific_question", "scope": "single", "relevant_tools": ["type_2_diabetes_non_insulin_pharmacotherapy_2"], "clinical_domain": "general", "confidence": 0.85, "reasoning": "Specific patient scenario asking for screening algorithm - diabetes pharmacotherapy tool is most relevant for management guidance"}}

Query: "What depression screening and treatment pathway tools does CEP provide for elderly patients?"
Response: {{"intent": "specific_question", "scope": "multiple", "relevant_tools": ["anxiety_and_depression", "managing_benzodiazepine_use_in_older_adults"], "clinical_domain": "mental_health", "confidence": 0.9, "reasoning": "User asks for specific screening and treatment pathways - anxiety/depression tool covers this, benzodiazepine tool relevant for elderly"}}

Query: "Does CEP have a tool for cardiovascular risk assessment?"
Response: {{"intent": "tool_discovery", "scope": "single", "relevant_tools": ["managing_patients_with_heart_failure_in_primary_care"], "clinical_domain": "cardiovascular", "confidence": 0.7, "reasoning": "User asks if tool exists - CEP has no CV risk calculator, but heart failure management tool is closest match"}}

Query: "How do I manage insomnia in elderly patients?"
Response: {{"intent": "specific_question", "scope": "multiple", "relevant_tools": ["management_of_chronic_insomnia", "managing_benzodiazepine_use_in_older_adults"], "clinical_domain": "mental_health", "confidence": 0.9, "reasoning": "Specific management question - insomnia tool is primary, benzodiazepine tool relevant for elderly"}}

Now classify the user's query:"""

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise CEP clinical tool classifier. Return only valid JSON."
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
        required_fields = ['intent', 'relevant_tools', 'scope', 'confidence']
        for field in required_fields:
            if field not in classification:
                logger.warning(f"Missing required field '{field}' in classification")
                classification[field] = None if field != 'relevant_tools' else []

        # Ensure confidence is a float
        if not isinstance(classification.get('confidence'), (int, float)):
            classification['confidence'] = 0.5

        # Ensure relevant_tools is a list
        if not isinstance(classification.get('relevant_tools'), list):
            classification['relevant_tools'] = []

        # Log classification
        logger.info(f"Query classified as: {classification['intent']}")
        logger.info(f"  Relevant tools: {classification['relevant_tools']}")
        logger.info(f"  Confidence: {classification['confidence']}")

        return classification

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response content: {content}")

        # Return fallback classification (no filtering - search all)
        return {
            "intent": "specific_question",
            "scope": "all",
            "relevant_tools": [],
            "clinical_domain": "general",
            "confidence": 0.3,
            "reasoning": "LLM classification failed, using fallback (no tool filtering)"
        }

    except Exception as e:
        logger.error(f"Classification failed: {e}")

        # Return fallback classification (no filtering - search all)
        return {
            "intent": "specific_question",
            "scope": "all",
            "relevant_tools": [],
            "clinical_domain": "general",
            "confidence": 0.3,
            "reasoning": f"Classification error: {str(e)}"
        }


# Query cache for testing and performance (simple dict-based cache)
# CLEARED after prompt update on 2025-10-07
_query_cache = {}


async def classify_cep_query_cached(query: str, openai_client) -> Dict:
    """
    Cached version of classify_cep_query for testing and performance.

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
    classification = await classify_cep_query(query, openai_client)

    # Cache result
    _query_cache[query_key] = classification

    return classification
