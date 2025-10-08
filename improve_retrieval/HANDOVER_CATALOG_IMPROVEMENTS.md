# Handover: Improve Catalog Tool Responses

**Date:** October 8, 2025
**Priority:** Medium
**Estimated Effort:** 2-3 hours

---

## Problem Statement

When users query for topics that don't exist in tool catalogs, the system returns **empty results** with no helpful guidance. This creates a poor user experience.

**Example:**
```
Query: "hypertension tools"
Response: [] (empty)
```

**Expected behavior:**
```
Query: "hypertension tools"
Response: "I couldn't find any tools specifically for hypertension. However, here are the closest matches:
- Managing Heart Failure in Primary Care (cardiovascular)
- Diabetes management tools (related condition)
Would you like information on any of these?"
```

---

## Scope

This issue affects **4 catalog-based tools**:

1. **opa_clinical_tools** - CEP Clinical Tools (41 tools)
   File: `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py:1298-1520`

2. **opa_policy_check** - CPSO Policies
   File: `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py:461-720`

3. **opa_quality_standards** - Ontario Health Quality Standards
   File: `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py:1522-1700`

4. **opa_choosing_wisely** - Choosing Wisely recommendations
   File: `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py:1702-1900`

---

## Current Architecture

Each tool uses a **two-tier retrieval architecture**:

### Tier 1: LLM Triage/Classification
```python
classification = await classify_query_cached(query, openai_client)
# Returns:
# {
#   "intent": "tool_discovery" | "specific_question",
#   "relevant_tools": ["tool_id1", "tool_id2"],  # ← Can be EMPTY
#   "confidence": 0.0-1.0,
#   "reasoning": "..."
# }
```

### Tier 2: Scoped Retrieval
```python
if classification["relevant_tools"]:
    # Retrieve from scoped tools
    results = await retrieve_detailed_chunks(...)
else:
    # Currently returns EMPTY []
    # ❌ No fallback or suggestions
```

---

## Required Changes

### Phase 1: Add Fallback Logic (All 4 Tools)

When `classification["relevant_tools"]` is empty, implement **semantic similarity fallback**:

1. **Compute query embedding** using OpenAI embeddings
2. **Compare against catalog** using cosine similarity
3. **Return top 3 closest matches** with similarity scores
4. **Format helpful response** explaining no exact match found

**Implementation location:**
Add to each handler after classification step (around lines 1356-1410 for CEP, similar for others)

```python
# NEW CODE TO ADD
if not classification["relevant_tools"] or len(classification["relevant_tools"]) == 0:
    logger.info("No exact matches found, computing semantic fallback suggestions")

    # Get catalog
    catalog = load_tool_catalog()  # or load_policy_catalog(), etc.

    # Compute semantic similarity
    suggestions = await compute_catalog_similarity(
        query=query,
        catalog=catalog,
        openai_client=openai_client,
        top_k=3,
        min_similarity=0.65  # Threshold for relevance
    )

    # Format helpful response
    if suggestions:
        suggestion_text = format_suggestions_response(
            query=query,
            suggestions=suggestions,
            catalog_type="CEP tools"  # or "CPSO policies", etc.
        )

        return {
            'items': [],
            'suggestions': suggestions,
            'total_tools': 0,
            'confidence': 0.5,
            'query_interpretation': suggestion_text,
            'no_exact_match': True
        }
    else:
        return {
            'items': [],
            'total_tools': 0,
            'confidence': 0.3,
            'query_interpretation': f"No {catalog_type} found for: {query}",
            'no_exact_match': True
        }
```

### Phase 2: Create Utility Functions

Create **new file**: `src/ai_agents/dr_opa_agent/dr_opa_mcp/utils/catalog_fallback.py`

```python
"""
Catalog fallback and semantic similarity utilities.
"""
import numpy as np
from typing import List, Dict
from openai import AsyncOpenAI


async def compute_catalog_similarity(
    query: str,
    catalog: List[Dict],
    openai_client: AsyncOpenAI,
    top_k: int = 3,
    min_similarity: float = 0.65
) -> List[Dict]:
    """
    Compute semantic similarity between query and catalog entries.

    Args:
        query: User's query
        catalog: List of catalog entries (tools/policies/standards)
        openai_client: OpenAI client for embeddings
        top_k: Number of suggestions to return
        min_similarity: Minimum cosine similarity threshold

    Returns:
        List of top-k similar catalog entries with scores
    """
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
        searchable_text = build_catalog_searchable_text(entry)

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
    return similarities[:top_k]


def build_catalog_searchable_text(entry: Dict) -> str:
    """Build searchable text from catalog entry fields."""
    # For CEP tools
    if 'tool_name' in entry:
        parts = [
            entry.get('tool_name', ''),
            entry.get('clinical_domain', ''),
            ', '.join(entry.get('conditions', [])),
            ', '.join(entry.get('capabilities', [])),
            ', '.join(entry.get('topics', []))
        ]
        return ' '.join(filter(None, parts))

    # For CPSO policies
    elif 'policy_title' in entry:
        parts = [
            entry.get('policy_title', ''),
            entry.get('practice_domain', ''),
            ', '.join(entry.get('topics', [])),
            ', '.join(entry.get('key_requirements', []))
        ]
        return ' '.join(filter(None, parts))

    # For Quality Standards
    elif 'standard_title' in entry:
        parts = [
            entry.get('standard_title', ''),
            entry.get('clinical_domain', ''),
            ', '.join(entry.get('conditions', [])),
            ', '.join(entry.get('care_focus', []))
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
        suggestions: List of similar catalog entries
        catalog_type: "CEP tools", "CPSO policies", etc.

    Returns:
        Formatted response text
    """
    if not suggestions:
        return f"No {catalog_type} found for: {query}"

    # Build response
    response_parts = [
        f"I couldn't find any {catalog_type} specifically for '{query}'.",
        "",
        "However, here are the closest matches:",
        ""
    ]

    for i, suggestion in enumerate(suggestions, 1):
        entry = suggestion['entry']
        similarity = suggestion['similarity']

        # Format based on catalog type
        if 'tool_name' in entry:
            name = entry['tool_name']
            domain = entry.get('clinical_domain', 'general')
            conditions = ', '.join(entry.get('conditions', [])[:2])
        elif 'policy_title' in entry:
            name = entry['policy_title']
            domain = entry.get('practice_domain', 'general')
            conditions = entry.get('policy_level', '')
        elif 'standard_title' in entry:
            name = entry['standard_title']
            domain = entry.get('clinical_domain', 'general')
            conditions = ', '.join(entry.get('conditions', [])[:2])
        else:
            name = entry.get('title', 'Unknown')
            domain = 'general'
            conditions = ''

        response_parts.append(
            f"{i}. {name} ({domain})" +
            (f" - {conditions}" if conditions else "") +
            f" [similarity: {similarity:.2f}]"
        )

    response_parts.append("")
    response_parts.append("Would you like information on any of these?")

    return '\n'.join(response_parts)
```

### Phase 3: Update Response Models

Update response models to include `suggestions` field:

**File:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/models/response.py`

Add to existing response classes:
```python
suggestions: Optional[List[Dict[str, Any]]] = Field(
    None,
    description="Suggested alternatives when no exact match found"
)
no_exact_match: bool = Field(
    default=False,
    description="True if no exact matches found, suggestions provided instead"
)
```

---

## Testing

Create test cases in `tests/test_catalog_fallback.py`:

```python
@pytest.mark.asyncio
async def test_cep_tools_no_match_returns_suggestions():
    """Test that non-existent tool returns helpful suggestions."""
    result = await clinical_tools_handler.fn(
        query="hypertension management",
        k=5
    )

    assert result['no_exact_match'] is True
    assert 'suggestions' in result
    assert len(result['suggestions']) > 0
    assert 'heart failure' in result['query_interpretation'].lower()


@pytest.mark.asyncio
async def test_cpso_policy_no_match_returns_suggestions():
    """Test CPSO policy suggestions for non-existent policy."""
    result = await policy_check_handler.fn(
        query="cryptocurrency mining in clinics",
        k=10
    )

    assert result['no_exact_match'] is True
    assert 'suggestions' in result
    # Should suggest closest policies even if topic doesn't exist


@pytest.mark.asyncio
async def test_quality_standards_no_match():
    """Test quality standards suggestions."""
    result = await quality_standards_handler.fn(
        query="homeopathy quality standards",
        k=10
    )

    assert result['no_exact_match'] is True
    assert 'suggestions' in result
```

---

## Performance Considerations

1. **Caching**: Cache catalog embeddings to avoid recomputing (catalog changes rarely)
2. **Batch processing**: Compute all catalog embeddings in batch for efficiency
3. **Timeout**: Add 5-second timeout for fallback computation
4. **Graceful degradation**: If fallback fails, return simple "not found" message

---

## Related Files

### Catalogs to Load
- CEP: `src/ai_agents/dr_opa_agent/dr_opa_mcp/cep_tool_catalog.json`
- CPSO: `src/ai_agents/dr_opa_agent/dr_opa_mcp/cpso_policy_catalog.json`
- QS: `src/ai_agents/dr_opa_agent/dr_opa_mcp/quality_standards_catalog.json`
- CW: `src/ai_agents/dr_opa_agent/dr_opa_mcp/choosing_wisely_catalog.json`

### Triage Functions to Modify
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/cep_triage.py:78` - classify_cep_query
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/cpso_triage.py` - classify_cpso_query
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/qs_triage.py` - classify_qs_query
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/choosing_wisely_triage.py` - classify_cw_query

---

## Bonus: ADP Device Category Issue

**Separate bug found**: ADP `device_category` field is **empty ('None')** in all 214 ChromaDB documents.

**Location:** `data/dr_off_agent/processed/dr_off/chroma` collection `adp_documents`

**Root cause:** Ingestion script not extracting category from filename.

**Filenames contain category:**
```
moh-adp-policy-and-administration-manual-mobility-devices-2023-07-01.pdf
moh-adp-policy-and-administration-manual-hearing-devices-2023-07-01.pdf
moh-adp-policy-and-administration-manual-insulin-pump-2023-07-01.pdf
moh-adp-policy-and-administration-manual-communication-aids-2023-07-01.pdf
...
```

**Device categories to extract:**
- mobility-devices → "Mobility Devices"
- hearing-devices → "Hearing Devices"
- insulin-pump → "Insulin Pump"
- communication-aids → "Communication Aids"
- home-oxygen → "Home Oxygen"
- limb-prosthesis → "Limb Prosthesis"
- etc.

**Fix needed:**
1. Find ADP ingestion script (likely `scripts/ingest_*adp*.py` or in `src/ai_agents/dr_off_agent/ingestion/`)
2. Add filename parsing to extract device category
3. Set `device_category` metadata field during ingestion
4. Re-run ingestion for ADP corpus

**Search for ingestion script:**
```bash
find . -name "*ingest*adp*.py" -o -name "*adp*ingest*.py"
grep -r "adp_documents" src/ scripts/
```

---

## Success Criteria

✅ When user queries for non-existent topic, system returns:
  - 3 closest matching alternatives
  - Similarity scores
  - Helpful explanation text
  - User can follow up on suggestions

✅ All 4 catalog tools have fallback logic
✅ Tests pass for no-match scenarios
✅ Response time <3 seconds even with fallback
✅ ADP device_category populated in ChromaDB

---

## Questions for Implementation

1. Should similarity threshold be configurable per catalog type?
2. Should we cache catalog embeddings on server startup?
3. Should suggestions be automatically expanded (retrieve chunks) or require user confirmation?
4. What to do if query is completely nonsensical (e.g., "asdfasdf")?

---

**Status:** Ready for implementation
**Assigned to:** Fresh Claude Code session
**Estimated completion:** 2-3 hours
