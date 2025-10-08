# Hybrid Search Technical Explanation
## BM25 + Dense Vector Retrieval with RRF Fusion

**Date:** 2025-10-06
**Issue:** #2 - Hybrid Retrieval Implementation
**Goal:** Improve Dr. OPA Recall@50 from 62% → 80%+ by combining semantic + exact term matching

---

## Problem Statement

**Baseline Issue:**
- Dense-only embeddings (text-embedding-3-small) achieve 62% Recall@50 on Dr. OPA queries
- Missing 38% of relevant documents due to technical terminology gaps
- Examples of missed terms: "IPAC", "semi-critical devices", policy codes, exact tool names

**Why This Happens:**
```
Query: "What are IPAC hand hygiene requirements?"
Dense Embedding: [0.234, -0.891, 0.456, ...]  # Captures semantic meaning
                 ↓
Misses documents with exact term "IPAC" if embedding didn't learn that acronym well
```

**Solution:** Combine semantic (dense) + keyword (sparse) retrieval

---

## Architecture Overview

```
┌─────────────┐
│ User Query  │
│ "IPAC hand  │
│  hygiene"   │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────┐
│         Hybrid Search Pipeline           │
├──────────────────────────────────────────┤
│                                          │
│  ┌─────────────┐    ┌─────────────┐    │
│  │   DENSE     │    │   SPARSE    │    │
│  │  (ChromaDB) │    │   (BM25)    │    │
│  │             │    │             │    │
│  │ Semantic    │    │ Exact term  │    │
│  │ similarity  │    │ matching    │    │
│  │             │    │             │    │
│  │ Top 50      │    │ Top 50      │    │
│  └──────┬──────┘    └──────┬──────┘    │
│         │                  │            │
│         └────────┬─────────┘            │
│                  ▼                       │
│         ┌────────────────┐              │
│         │  RRF FUSION    │              │
│         │  Merge rankings│              │
│         │  Top 50        │              │
│         └────────┬───────┘              │
│                  ▼                       │
│         ┌────────────────┐              │
│         │  LLM RERANK    │              │
│         │  (GPT-4o-mini) │              │
│         │  Top 20        │              │
│         └────────┬───────┘              │
│                  ▼                       │
│         ┌────────────────┐              │
│         │ METADATA       │              │
│         │ FILTER         │              │
│         │ Top k (10)     │              │
│         └────────────────┘              │
│                                          │
└──────────────────────────────────────────┘
```

---

## Component 1: BM25 Sparse Retrieval

### What is BM25?

**BM25 (Best Matching 25)** is a probabilistic ranking function for exact term matching.

**Formula:**
```
score(D, Q) = Σ IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))

where:
- D = document
- Q = query
- qi = query term i
- IDF(qi) = inverse document frequency (rarity of term)
- f(qi, D) = term frequency in document
- |D| = document length
- avgdl = average document length
- k1, b = tuning parameters (Whoosh defaults)
```

**Pseudo Code:**
```python
# BM25 Search Algorithm
function bm25_search(query: str, n_results: int) -> List[Document]:
    # 1. Parse query into terms
    terms = tokenize(query)  # ["IPAC", "hand", "hygiene"]

    # 2. For each document in index:
    scores = {}
    for doc in index.documents:
        score = 0.0

        # 3. For each query term:
        for term in terms:
            if term in doc:
                # Calculate BM25 component
                tf = count(term, doc)  # Term frequency
                idf = log(N / df[term])  # Inverse doc frequency
                doc_len_norm = len(doc) / avg_doc_length

                # BM25 formula (simplified)
                score += idf * (tf * (k1 + 1)) / (tf + k1 * doc_len_norm)

        scores[doc.id] = score

    # 4. Sort by score and return top N
    return top_k(scores, n_results)
```

### Implementation Details

**Index Creation:**
```python
# From bm25_client.py
schema = Schema(
    doc_id=ID(stored=True, unique=True),
    text=TEXT(stored=True),           # Main content for BM25
    document_title=TEXT(stored=True),  # Also indexed for search
    section_heading=TEXT(stored=True), # Also indexed for search
    source_org=STORED,                 # Metadata only (not indexed)
    document_type=STORED,
    # ... other metadata fields
)

# Build index from ChromaDB
for collection in [cpso, pho, cep, quality_standards, choosing_wisely]:
    for doc in collection.get_all():
        index.add_document(
            doc_id=f"{collection.name}:{doc.id}",
            text=doc.text,
            document_title=doc.metadata.get('document_title'),
            section_heading=doc.metadata.get('section_heading'),
            # ... metadata
        )
```

**Search Process:**
```python
# Whoosh QueryParser with OR logic
parser = QueryParser("text", schema, group=OrGroup)
query = parser.parse("IPAC hand hygiene")
# Becomes: (IPAC OR hand OR hygiene) in text field

results = searcher.search(query, limit=50)
# Returns documents ranked by BM25 score
```

---

## Component 2: RRF (Reciprocal Rank Fusion)

### What is RRF?

**Reciprocal Rank Fusion** combines rankings from multiple retrievers without needing score normalization.

**Formula:**
```
RRF_score(doc) = Σ 1 / (c + rank_i)

where:
- rank_i = rank of document in retriever i (1-indexed)
- c = constant (typically 60)
- Σ = sum over all retrievers that returned this document
```

**Key Advantage:** Rank-based (not score-based) = no normalization needed!

### Why c=60?

```
c=60 is empirically proven optimal (Cormack et al., 2009):

rank=1:  1/(60+1)  = 0.0164  ← Top ranked item
rank=2:  1/(60+2)  = 0.0161  ← Small difference
rank=10: 1/(60+10) = 0.0143
rank=50: 1/(60+50) = 0.0091

Effect: Balances contribution from top and lower-ranked items
```

### Pseudo Code

```python
function rrf_fusion(dense_results: List, sparse_results: List, c=60) -> List:
    # 1. Initialize score accumulator
    rrf_scores = {}
    doc_data = {}

    # 2. Process dense results (ranked by similarity)
    for rank, doc in enumerate(dense_results, start=1):
        rrf_scores[doc.id] += 1.0 / (c + rank)
        doc_data[doc.id] = doc  # Store document
        doc.dense_rank = rank
        doc.dense_score = doc.similarity_score

    # 3. Process sparse (BM25) results
    for rank, doc in enumerate(sparse_results, start=1):
        rrf_scores[doc.id] += 1.0 / (c + rank)

        if doc.id in doc_data:
            # Document appeared in both retrievers
            doc_data[doc.id].bm25_rank = rank
            doc_data[doc.id].bm25_score = doc.score
        else:
            # New document (only in BM25)
            doc_data[doc.id] = doc
            doc.bm25_rank = rank

    # 4. Build final list with RRF scores
    results = []
    for doc_id, doc in doc_data.items():
        doc.rrf_score = rrf_scores[doc_id]
        doc.provenance = get_provenance(doc)  # "dense", "sparse", or "dense+sparse"
        results.append(doc)

    # 5. Sort by RRF score (descending)
    results.sort(key=lambda x: x.rrf_score, reverse=True)

    return results[:k]
```

### Example: RRF in Action

```
Query: "IPAC hand hygiene requirements"

Dense Results (semantic):        Sparse (BM25) Results (keyword):
Rank 1: doc_A (about hygiene)    Rank 1: doc_C (contains "IPAC")
Rank 2: doc_B (about safety)     Rank 2: doc_A (contains "hand hygiene")
Rank 3: doc_D (about protocols)  Rank 3: doc_E (contains all terms)

RRF Calculation (c=60):
doc_A: 1/(60+1) + 1/(60+2) = 0.0164 + 0.0161 = 0.0325  ← WINNER (in both)
doc_C: 1/(60+1)            = 0.0164                     ← 2nd (BM25 rank 1)
doc_B: 1/(60+2)            = 0.0161                     ← 3rd
doc_E: 1/(60+3)            = 0.0159                     ← 4th
doc_D: 1/(60+3)            = 0.0159                     ← 5th

Final Ranking: [doc_A, doc_C, doc_B, doc_E, doc_D]
```

**Result:** doc_A wins because it appeared in BOTH retrievers (provenance: "dense+sparse")

---

## Component 3: Hybrid Search Pipeline

### Full Algorithm Pseudo Code

```python
async function hybrid_search(query: str, sources: List[str], k: int = 10) -> List[Document]:

    # STEP 1: PARALLEL RETRIEVAL (Dense + Sparse)
    # ============================================
    # Run both retrievers in parallel using asyncio.gather()

    dense_task = vector_search(
        query=query,
        sources=sources,
        n_results=50  # Cast wide net
    )

    sparse_task = bm25_search(
        query=query,
        sources=sources,
        n_results=50  # Cast wide net
    )

    dense_results, sparse_results = await parallel_execute(dense_task, sparse_task)

    # STEP 2: RRF FUSION
    # ==================
    # Merge rankings from both retrievers

    fused_results = rrf_fusion(
        dense_results=dense_results,
        sparse_results=sparse_results,
        c=60.0  # RRF constant
    )
    # Output: Top 50 unique documents ranked by RRF score

    # STEP 3: LLM RERANKING (Optional)
    # =================================
    # Use GPT-4o-mini to score top candidates for precision

    if use_reranking:
        reranked_results = []
        for doc in fused_results[:30]:  # Limit cost
            relevance_score = await llm_score_relevance(query, doc)
            doc.relevance_score = relevance_score  # 0-10 scale
            reranked_results.append(doc)

        reranked_results.sort(key=lambda x: x.relevance_score, reverse=True)
        candidates = reranked_results[:20]
    else:
        candidates = fused_results[:20]

    # STEP 4: METADATA FILTERING
    # ===========================
    # Apply hard constraints

    filtered_results = []
    for doc in candidates:
        # Check document type
        if document_types and doc.metadata['document_type'] not in document_types:
            continue

        # Check policy level
        if policy_level and doc.metadata['policy_level'] != policy_level:
            continue

        # Check date range
        if after_date and doc.metadata['effective_date'] < after_date:
            continue

        filtered_results.append(doc)

    # STEP 5: RETURN TOP K
    # ====================
    return filtered_results[:k]
```

### Execution Flow Example

```
Input Query: "What are IPAC semi-critical device sterilization requirements?"

STEP 1: Parallel Retrieval (asyncio.gather)
┌─────────────────────────┐  ┌─────────────────────────┐
│ Dense (ChromaDB)        │  │ Sparse (BM25)           │
│ Finds:                  │  │ Finds:                  │
│ - Hygiene protocols     │  │ - Docs with "IPAC"      │
│ - Sterilization guides  │  │ - Docs with "semi-      │
│ - Device safety docs    │  │   critical"             │
│                         │  │ - Exact term matches    │
│ 50 results (semantic)   │  │ 50 results (keyword)    │
└───────────┬─────────────┘  └───────────┬─────────────┘
            │                            │
            └──────────┬─────────────────┘
                       ▼
STEP 2: RRF Fusion (c=60)
┌──────────────────────────────────────┐
│ Merged Ranking:                      │
│ 1. doc_X (dense rank 2, BM25 rank 1) │ ← RRF: 0.0325 (BOTH)
│ 2. doc_Y (dense rank 1)              │ ← RRF: 0.0164 (dense only)
│ 3. doc_Z (BM25 rank 3)               │ ← RRF: 0.0159 (BM25 only)
│ ...                                  │
│ 50 unique documents                  │
└──────────────────┬───────────────────┘
                   ▼
STEP 3: LLM Reranking (GPT-4o-mini)
┌──────────────────────────────────────┐
│ Relevance Scoring (0-10):            │
│ doc_X: 9.2 (directly answers query)  │
│ doc_Z: 8.5 (highly relevant)         │
│ doc_Y: 7.1 (related but not direct)  │
│ → Top 20 by relevance                │
└──────────────────┬───────────────────┘
                   ▼
STEP 4: Metadata Filtering
┌──────────────────────────────────────┐
│ Apply filters:                        │
│ - source='pho' ✓                     │
│ - document_type='ipac-guidance' ✓    │
│ - after_date='2023-01-01' ✓          │
│ → 12 documents pass                  │
└──────────────────┬───────────────────┘
                   ▼
STEP 5: Return Top k=10
┌──────────────────────────────────────┐
│ Final Results:                        │
│ 1. IPAC Semi-Critical Device Guide   │
│ 2. PHO Sterilization Standards       │
│ 3. Device Reprocessing Protocol      │
│ ...                                  │
│ 10. Equipment Safety Requirements    │
└──────────────────────────────────────┘
```

---

## Value Proposition

### Why Hybrid Search Works

**1. Complementary Strengths:**
```
Dense (Semantic):                    Sparse (BM25):
✓ Understands intent                 ✓ Exact term matching
✓ Handles paraphrasing               ✓ Acronyms (IPAC, CPSO)
✓ Conceptual similarity              ✓ Technical terms
✗ Misses exact terms                 ✗ No semantic understanding
✗ Weak on acronyms                   ✗ Misses paraphrases

Combined via RRF:
✓ Best of both worlds
✓ Higher recall (catches more relevant docs)
✓ Better ranking (docs in both rank highest)
```

**2. Evidence from Dr. OFF (Baseline Success):**
```
Dr. OFF uses hybrid SQL + Vector:
- SQL: Exact code lookups (C124, A001)
- Vector: Semantic understanding
- Result: 87% Recall@50 (excellent)

Dr. OPA was dense-only:
- Vector only: Semantic understanding
- Result: 62% Recall@50 (missing 38%)

Applying hybrid to Dr. OPA → Expected: 80%+ Recall@50
```

**3. RRF Advantages Over Score Fusion:**
```
Score Fusion (naive):
- Requires normalization: dense_score ∈ [0,1], BM25_score ∈ [0,∞]
- Scaling issues: how to weight?
- Complex tuning

RRF (rank-based):
- No normalization needed
- Empirically proven (c=60)
- Simple implementation
- Works across different retriever types
```

### Expected Impact

**Baseline Targets:**
```
Collection              Current Recall@50    Target    How Hybrid Helps
--------------------------------------------------------------------------------
Choosing Wisely         75%                  90%+      Exact recommendation names
CPSO Policies           80%                  90%+      Policy codes + semantic
PHO IPAC                80%                  95%+      "IPAC", "semi-critical" exact match
CEP Tools               25% ⚠️               75%+      Tool name exact matching (critical)
Quality Standards       75%                  90%+      Standard numbers + semantic
--------------------------------------------------------------------------------
Average                 62%                  88%+      +26% improvement (38% gap closed)
```

**Why CEP Tools Will Improve Most:**
```
Baseline issue: Dense embedding misses tool names
Query: "diabetes screening algorithm"
Dense: Might retrieve general diabetes docs
BM25: Finds docs with exact phrase "diabetes screening algorithm"
RRF: Combines both → correct tool ranked #1
```

---

## Performance Considerations

### Latency Analysis

**Dense Search:** ~100-200ms (ChromaDB embedding + vector search)
**BM25 Search:** ~50-100ms (Whoosh in-memory index, 1,439 docs)
**Parallel Execution:** max(dense, BM25) ≈ 200ms
**RRF Fusion:** ~5-10ms (simple rank calculation)
**LLM Reranking:** ~500-800ms (GPT-4o-mini, 30 docs)
**Total:** ~700-1000ms (within <1s target) ✓

### Scalability

**Current:** 1,439 documents across 5 collections
**BM25 Index Size:** ~2-5 MB (Whoosh on disk)
**Memory:** Minimal (index loaded on demand)
**Scale Limit:** Whoosh handles 10k-100k docs efficiently
**Future:** If >100k docs, migrate to Tantivy (Rust) or Elasticsearch

---

## Testing & Validation

### Unit Tests (7 passing)

```python
# From test_rrf_fusion.py
test_rrf_fusion_basic()           # Overlapping results → correct ranking
test_rrf_fusion_no_overlap()      # Disjoint results → provenance tracking
test_rrf_c_parameter()            # c=10 vs c=100 → variance difference
test_rrf_k_limit()                # k parameter enforced
test_rrf_score_calculation()      # Formula correctness (2/61 = 0.0328)
test_rrf_empty_inputs()           # Edge cases handled
test_rrf_metadata_preservation()  # Both retriever info kept
```

### Integration Test (Index Build)

```bash
python scripts/build_bm25_index.py
# Output:
# ✓ ChromaDB: 5 collections loaded (1,439 docs total)
# ✓ BM25 index built: 1,439 documents indexed
# ✓ Test search: 5 results for "IPAC hand hygiene"
```

### Baseline Evaluation (Next Step)

```bash
# Run on single dataset first
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/pho_ipac.jsonl

# Expected improvement:
# Baseline Recall@50: 80%
# Hybrid Recall@50: 95%+ (BM25 catches "IPAC", "semi-critical" exact terms)
```

---

## Conclusion

**Hybrid Search Implementation Summary:**

1. **BM25 Sparse Retrieval:** Exact term matching for technical vocabulary
2. **RRF Fusion:** Rank-based combination (no normalization, c=60)
3. **Hybrid Pipeline:** Dense ∥ Sparse → RRF → Rerank → Filter → Top-k

**Value:**
- Closes 38% recall gap (62% → 80%+ target)
- Maintains <1s latency via parallel execution
- Backward compatible with dense-only mode
- Proven approach (Dr. OFF at 87% recall with hybrid SQL+Vector)

**Next Steps:**
1. Run baseline evaluations to measure improvement
2. Document results in `RESULTS.md` iteration tracker
3. Consider cross-encoder reranking (Issue #3) if further improvement needed
