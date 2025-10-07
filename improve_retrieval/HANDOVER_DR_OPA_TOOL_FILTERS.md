# HANDOVER: Fix Dr. OPA Tool Filters (0% Recall Issue)

## Problem Summary

**CRITICAL**: After completing Issue #6 (Parent/Child Chunking), Dr. OPA tools are returning 0% recall on 3 datasets:
- CEP Tools: 0% recall (expected: ~40-60%)
- Choosing Wisely: 0% recall (expected: ~40-60%)
- CPSO Policies: 0% recall (expected: ~40-60%)

Dr. OFF tools work fine (40-60% recall). The issue is specific to Dr. OPA's filtering logic.

## Root Cause Investigation

### What We Know:
1. **Collections exist and have data**:
   - opa_cep_corpus: 840 chunks
   - opa_choosing_wisely_corpus: 295 chunks
   - opa_cpso_corpus: 325 chunks

2. **Embeddings are correct**: All verified with 1536-dim (text-embedding-3-small)

3. **Tools return 0 items** (from eval logs):
   ```
   Retrieved items count: 0
   Keyword pre-filter: 0/0 chunks passed (filtered 0)
   LLM-based matching found 0 relevant chunks out of 0
   ```

4. **Metadata filtering confirmed as the issue**:
   - The tools use `document_types` parameter to filter results
   - Semantic search filters on `document_type` OR `doc_type` metadata field (line 421 in semantic_search.py)
   - **But the tools may be passing wrong values or the filter is too restrictive**

### Key Code Locations:

**File**: `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py`

**Choosing Wisely Tool** (line 1603-1682):
```python
@mcp.tool(name="opa_choosing_wisely", ...)
async def choosing_wisely_handler(query: str, k: int = 10, filters: Dict[str, Any] = None):
    # Line 1646-1651: Document type filter construction
    document_types = None
    if recommendation_type == 'overview':
        document_types = ['choosing_wisely_overview']
    elif recommendation_type == 'recommendation':
        document_types = ['choosing_wisely_recommendation']

    # Line 1675-1682: Search with document_types filter
    search_results = await semantic_search.search(
        query=search_query,
        sources=sources,
        document_types=document_types,  # <-- Filter is applied here
        k=initial_search_size,
        ...
    )
```

**File**: `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py`

**Filter Logic** (line 394-443):
```python
def _apply_filters(
    self,
    documents: List[Dict[str, Any]],
    document_types: Optional[List[str]] = None,
    ...
):
    for doc in documents:
        metadata = doc.get('metadata', {})

        # Line 419-424: Document type filter
        if document_types:
            doc_type = metadata.get('doc_type') or metadata.get('document_type', '')
            if doc_type not in document_types:
                logger.debug(f"Filtered out: wrong type ({doc_type} not in {document_types})")
                continue
```

## What Needs to Be Done

### Step 1: Verify Actual Metadata Values
Run this script to check what `document_type` values are actually in the collections:

```python
import chromadb

client = chromadb.PersistentClient(path="data/processed/dr_opa/chroma")

for collection_name in ['opa_cep_corpus', 'opa_choosing_wisely_corpus', 'opa_cpso_corpus']:
    collection = client.get_collection(collection_name)
    results = collection.get(limit=10, include=['metadatas'])

    print(f"\n{collection_name}:")
    doc_types = set()
    for metadata in results['metadatas']:
        dt = metadata.get('document_type') or metadata.get('doc_type', 'MISSING')
        doc_types.add(dt)
    print(f"  document_type values: {doc_types}")
```

### Step 2: Check Tool Filter Values
Look at what `document_types` values the tools are passing to semantic_search.search():

**CEP Tool** (line ~1300 in server.py):
```python
@mcp.tool(name="opa_cep_tools", ...)
```

**CPSO Tool** (line ~1480 in server.py):
```python
@mcp.tool(name="opa_cpso_policy", ...)
```

**Choosing Wisely Tool** (line 1603 in server.py):
```python
@mcp.tool(name="opa_choosing_wisely", ...)
```

### Step 3: Fix the Mismatch
The issue is likely one of these:

**Option A**: Tools pass specific `document_types` values that don't match the actual metadata
- **Fix**: Update tool handlers to pass correct values OR remove document_types filter entirely

**Option B**: Metadata has wrong field names (e.g., `doc_type` instead of `document_type`)
- **Fix**: Re-run ingestion scripts to fix metadata

**Option C**: Filter is being applied when it shouldn't be
- **Fix**: Make document_types filter optional or default to None

## Evaluation Commands

After fixing, re-run evaluations to verify:

```bash
# CEP Tools
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl --output eval/results/04_chunking/dr_opa_cep_tools.json

# Choosing Wisely
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/choosing_wisely.jsonl --output eval/results/04_chunking/dr_opa_choosing_wisely.json

# CPSO Policies
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cpso_policies.jsonl --output eval/results/04_chunking/dr_opa_cpso_policies.json
```

Expected results: 40-60% recall (same as Dr. OFF)

## Files to Review

1. `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py` - Lines 1300-1700 (all tool handlers)
2. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py` - Lines 394-443 (filter logic)
3. Evaluation logs: `/tmp/eval_cep.log`, `/tmp/eval_choosing_wisely.log`, `/tmp/eval_cpso.log`
4. Eval results: `eval/results/04_chunking/dr_opa_*.json`

## Context

- **Issue #6** (Parent/Child Chunking) is complete
- All collections restructured with 1536-dim embeddings
- Dr. OFF works fine (40-60% recall)
- Dr. OPA has filtering bug causing 0% recall on 3/6 datasets
- PHO and Quality Standards work (100% recall on queries that completed before timeout)
- Ontario Health Programs is web-based (no retrieval metrics)

## Success Criteria

- CEP Tools: ≥40% recall
- Choosing Wisely: ≥40% recall
- CPSO Policies: ≥40% recall
- All tools return >0 items for relevant queries
