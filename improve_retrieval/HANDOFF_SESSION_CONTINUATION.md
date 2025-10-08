# Session Handoff: Dr. OPA/OFF Tool Evaluation & Improvement

**Date:** 2025-10-07
**Status:** Ready to run evaluations and iterate on improvements
**Context Limit Reached:** Yes - fresh session needed

---

## What We Just Completed

### 1. Fixed Dr. OPA Embedding Mismatch ✅
**Issue:** Dr. OPA tools returning 0% recall due to embedding dimension mismatch (1536 vs 384)

**Fix Applied:**
- File: `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/vector_client.py`
- Changed: Collections now loaded without embedding function, query embeddings generated manually
- Result: Embedding mismatch resolved

### 2. Improved CEP Content Extraction ✅
**Issue:** BeautifulSoup extractor missing content from Gravity Forms blocks

**Fix Applied:**
- File: `src/ai_agents/dr_opa_agent/ingestion/cep/ingester_v2.py`
- Added extraction from: `<span>`, `<div class="gfield_html">`, `<blockquote>`, `<aside>`, H4 headings
- Validation: 100% section coverage on 3 live web pages (Dementia, Heart Failure, ADHD tools)

### 3. Removed Boilerplate Sections ✅
**Issue:** 22% of chunks were References/Acknowledgments (not clinically useful)

**Fix Applied:**
- File: `src/ai_agents/dr_opa_agent/ingestion/cep/ingester_v2.py` (lines 38-43, 226-241)
- Added `BOILERPLATE_SECTIONS` filter that skips References, Acknowledgments, Legal sections during ingestion
- Collection reduced: 644 → 501 chunks (-22.2%)
- Boilerplate removed: 143 → 0 chunks (100% removed)

### 4. Fixed API Compatibility Bug ✅
**Issue:** Tools calling `semantic_search.search(document_types=...)` but that parameter doesn't exist

**Fix Applied:**
- File: `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py`
- Removed `document_types=` parameter from 5 tool handler calls (lines 867, 1198, 1334, 1401, 1661)
- Ready to test but **NOT YET RUN** due to context limit

---

## Current State

### Collections Status

**Dr. OPA Collections:**
- ✅ `opa_cep_corpus`: 501 chunks (re-ingested without boilerplate)
- ✅ `opa_choosing_wisely_corpus`: 295 chunks
- ✅ `opa_cpso_corpus`: 325 chunks
- ✅ `opa_pho_corpus`: Active
- ✅ `opa_quality_standards_corpus`: Active
- All use 1536-dim OpenAI embeddings (text-embedding-3-small)

**Dr. OFF Collections:**
- Status: Not yet evaluated in this session

---

## NEXT STEPS (Immediate Tasks)

### Task 1: Run CEP Tools Evaluation ⏭️

```bash
# Kill any running MCP servers
pkill -f "dr_opa_mcp"

# Run evaluation
source /Users/liammckendry/spacy_env/bin/activate
python eval/run.py \
  --agent dr_opa \
  --set eval/gold/dr_opa/cep_tools.jsonl \
  --output eval/results/04_chunking/dr_opa_cep_tools_FINAL.json
```

**Expected Results:**
- Before: 50% recall (2/4 queries)
- After boilerplate removal: Should improve MRR significantly
- Note: 2 queries (cep_002, cep_004) ask for non-existent content - those will still fail

**Check:**
```bash
cat eval/results/04_chunking/dr_opa_cep_tools_FINAL.json | jq '.summary'
```

### Task 2: Analyze Results & Compare

Compare to baseline:
```bash
# Baseline (before fixes)
cat eval/results/04_chunking/dr_opa_cep_tools.json | jq '.summary'

# After boilerplate removal
cat eval/results/04_chunking/dr_opa_cep_tools_FINAL.json | jq '.summary'
```

Look for:
- ✅ MRR improvement (was 0.051, expect 0.2-0.3+)
- ✅ No boilerplate in top-10 results
- ⚠️ Recall@50 likely still 50% (test data issue, not retrieval issue)

### Task 3: Run All Dr. OPA Evaluations

```bash
# Run all 6 datasets
for dataset in cep_tools choosing_wisely cpso_policies pho_ipac quality_standards ontario_health_programs; do
  echo "Evaluating $dataset..."
  python eval/run.py \
    --agent dr_opa \
    --set eval/gold/dr_opa/${dataset}.jsonl \
    --output eval/results/04_chunking/dr_opa_${dataset}.json
done
```

**Expected Results:**
- CEP Tools: 50% recall (test data issue)
- Choosing Wisely: 40-60% recall (should work now)
- CPSO Policies: 40-60% recall (should work now)
- PHO IPAC: 40-60% recall (or timeouts - large dataset)
- Quality Standards: 100% recall (worked before)
- Ontario Health Programs: Web-based (no retrieval metrics)

### Task 4: Troubleshoot Low-Performing Datasets

For any dataset with <40% recall:

1. **Check logs:**
```bash
find logs/dr_opa_agent -name "mcp_session_*.log" -type f | sort -r | head -1 | xargs tail -200 | grep ERROR
```

2. **Inspect failed queries:**
```bash
cat eval/results/04_chunking/dr_opa_DATASET.json | jq '.queries[] | select(.recall_at_50 < 0.5) | {id, query, recall_at_50, retrieved_count}'
```

3. **Check collection metadata:**
```python
import chromadb
client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")
collection = client.get_collection("opa_COLLECTION_NAME")
results = collection.get(limit=10, include=['metadatas', 'documents'])

# Check chunk types and metadata fields
for metadata in results['metadatas']:
    print(metadata.keys())
```

4. **Common Issues & Fixes:**
   - **Chunk type mismatch:** Tool expects `chunk_type='X'` but data has `chunk_type='parent/child'`
     - Fix: Update tool handler like we did for Choosing Wisely (server.py line 1713)
   - **Metadata field mismatch:** Tool filters on `document_type` but data uses `doc_type`
     - Fix: Update filter logic in tool handler
   - **Content missing:** Check extraction quality
     - Fix: Update ingester like we did for CEP

---

## Task 5: Run Dr. OFF Evaluations

```bash
# Run all Dr. OFF datasets
for dataset in adp schedule ohip odb; do
  echo "Evaluating Dr. OFF $dataset..."
  python eval/run.py \
    --agent dr_off \
    --set eval/gold/dr_off/${dataset}.jsonl \
    --output eval/results/04_chunking/dr_off_${dataset}.json
done
```

**Expected:** 40-60% recall (these worked before, should still work)

---

## Key Files Reference

### Code Files Modified This Session
1. `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/vector_client.py`
   - Lines 95-125: Load collections without embedding function
   - Lines 127-183: Generate query embeddings manually
   - Lines 240-273: Use cached collection references

2. `src/ai_agents/dr_opa_agent/ingestion/cep/ingester_v2.py`
   - Lines 38-43: BOILERPLATE_SECTIONS constant
   - Lines 226-241: `_should_skip_section()` method
   - Lines 272-284: Skip boilerplate in extraction loop
   - Lines 289-311: Extract from multiple HTML sources (gfield, span, etc.)

3. `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py`
   - Lines 867, 1198, 1334, 1401, 1661: Removed `document_types=` parameter

### Documentation Created
- `eval/results/04_chunking/CEP_EXTRACTION_VALIDATION.md` - Validation of 100% extraction completeness
- `eval/results/04_chunking/CEP_BEFORE_AFTER_COMPARISON.md` - Before/after ingestion comparison
- `eval/results/04_chunking/CEP_TOOLS_ANALYSIS.md` - Deep analysis of 50% recall issue
- `eval/results/04_chunking/ROOT_CAUSE_ANALYSIS.md` - Root cause of retrieval failures
- `BOILERPLATE_SOLUTION_COMPARISON.md` - 3 approaches compared (chose filtering at ingestion)
- `improve_retrieval/FIX_DR_OPA_EMBEDDING_MISMATCH.md` - Technical docs on embedding fix

### Scripts Available
- `reingest_cep_corpus.py` - Delete & re-ingest CEP with current extractor
- `validate_cep_extraction.py` - Compare extraction to live web pages
- `analyze_boilerplate.py` - Check boilerplate % in collection
- `test_cep_retrieval.py` - Test retrieval for specific queries

---

## Evaluation Commands Quick Reference

### Single Dataset
```bash
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/DATASET.jsonl --output eval/results/04_chunking/dr_opa_DATASET.json
```

### Check Results
```bash
cat eval/results/04_chunking/dr_opa_DATASET.json | jq '.summary'
```

### View Failed Queries
```bash
cat eval/results/04_chunking/dr_opa_DATASET.json | jq '.queries[] | select(.recall_at_50 == 0)'
```

### Create Summary Report
```python
import json
from pathlib import Path

results_dir = Path("eval/results/04_chunking")
summary = []

for result_file in results_dir.glob("dr_opa_*.json"):
    with open(result_file) as f:
        data = json.load(f)
        summary.append({
            'dataset': result_file.stem.replace('dr_opa_', ''),
            'recall': data['summary']['avg_recall@50'],
            'mrr': data['summary']['avg_mrr'],
            'queries': data['summary']['queries_evaluated']
        })

for s in sorted(summary, key=lambda x: x['recall']):
    print(f"{s['dataset']:40} | {s['recall']:5.1%} recall | MRR {s['mrr']:.3f} | {s['queries']} queries")
```

---

## Known Issues & Workarounds

### Issue 1: CEP Test Queries Ask for Non-Existent Content
**Problem:**
- `cep_002`: "Diabetes screening algorithm" - CEP only has diabetes MANAGEMENT
- `cep_004`: "CV risk assessment tool" - CEP only has heart failure MANAGEMENT

**Workaround:** Accept 50% recall, or update gold standard

### Issue 2: MCP Server Caching
**Problem:** MCP server caches collections at startup, doesn't reload after re-ingestion

**Workaround:** Kill server before running evals:
```bash
pkill -f "dr_opa_mcp"
```

### Issue 3: ChromaDB Client Conflicts
**Problem:** Multiple ChromaDB clients with different settings cause `ValueError`

**Workaround:** Use consistent settings, or restart Python process

---

## Success Criteria

After running all evaluations, we expect:

**Dr. OPA:**
- CEP Tools: 50% recall (limited by test data)
- Choosing Wisely: ≥40% recall
- CPSO Policies: ≥40% recall
- PHO IPAC: ≥40% recall (or acceptable timeout rate)
- Quality Standards: ≥90% recall
- Ontario Health Programs: Web-based (N/A)

**Dr. OFF:**
- All datasets: ≥40% recall

**Overall:**
- No embedding mismatch errors
- No `document_types` API errors
- Boilerplate not in top-10 results
- MRR improved from baseline

---

## If You Need to Debug

### Check Collection Health
```python
import chromadb
client = chromadb.PersistentClient(path="data/dr_opa_agent/chroma")

for collection_name in ['opa_cep_corpus', 'opa_choosing_wisely_corpus', 'opa_cpso_corpus']:
    collection = client.get_collection(collection_name)
    results = collection.get(limit=5, include=['metadatas', 'documents', 'embeddings'])

    print(f"\n{collection_name}:")
    print(f"  Total chunks: {collection.count()}")
    print(f"  Embedding dim: {len(results['embeddings'][0]) if results['embeddings'] else 'N/A'}")
    print(f"  Sample metadata keys: {list(results['metadatas'][0].keys()) if results['metadatas'] else 'N/A'}")
```

### Check MCP Server Status
```bash
# Find running servers
ps aux | grep mcp_server

# Check latest logs
find logs -name "mcp_session_*.log" -type f | sort -r | head -1 | xargs tail -50
```

### Re-ingest if Needed
```bash
# CEP only
python reingest_cep_corpus.py

# All Dr. OPA (use main ingestion script)
# Check: src/ai_agents/dr_opa_agent/ingestion/run_ingestion.py
```

---

## Timeline Estimate

- Task 1 (CEP eval): 3-5 minutes
- Task 2 (Analyze): 5-10 minutes
- Task 3 (All Dr. OPA): 15-30 minutes
- Task 4 (Troubleshoot): 30-60 minutes per failing dataset
- Task 5 (Dr. OFF): 10-15 minutes

**Total:** 1-3 hours depending on issues found

---

## Final Notes

1. **Always kill MCP servers before running evals** - they cache collections
2. **Check logs first** when something fails - errors are usually obvious
3. **Collection is good** - 501 CEP chunks, 0 boilerplate, 100% content extraction validated
4. **Code fixes applied** - embedding mismatch fixed, API compatibility fixed
5. **Ready to run** - just execute Task 1 and proceed from there

Good luck! 🚀
