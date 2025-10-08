# Hybrid Retrieval (Dense + BM25) with RRF Fusion - Implementation Plan

**GitHub Issue:** #2
**Status:** Planning → Ready to Execute
**Priority:** P1 - Critical for Dr. OPA recall improvement
**Estimated Effort:** 3-4 days
**Target Baseline Improvement:** Dr. OPA Recall@50: 62% → 80%+ (+18%)

---

## 1. Overview

### Objective
Implement hybrid retrieval combining dense vector search (ChromaDB) with sparse BM25 keyword matching, using Reciprocal Rank Fusion (RRF) to merge results. This will address the 38% recall gap in Dr. OPA queries caused by dense-only embeddings missing technical medical terminology.

### Why This Matters
**Baseline Data Evidence:**
- **Dr. OPA Recall Gap:** 62% recall (missing 38% of relevant documents)
- **Technical Term Misses:** IPAC queries miss "semi-critical devices", "IPAC guidance", policy codes
- **CEP Tools Critical:** 25% recall (post-fix from commit a7530d5) - needs exact tool name matching
- **Dr. OFF Comparison:** 87% recall with SQL+vector dual-path proves hybrid approaches work

**Impact on RAG Agent Quality:**
- Better retrieval → better context for LLM agent synthesis
- Missing context causes incomplete/incorrect agent-generated answers
- Current Coverage: 19% (agent answers missing 81% of required facts)

### Success Criteria
✅ Dr. OPA Recall@50 improves from 62% → 80%+ across 5 datasets (Choosing Wisely, CPSO, PHO IPAC, Quality Standards, CEP Tools)
✅ CEP Tools Recall@50 improves from 25% → 75%+ (BM25 exact tool name matching)
✅ Unit tests show improved Recall@50 on gold sets vs dense-only baseline
✅ RRF fusion properly combines dense + sparse rankings with configurable weights
✅ Latency remains <1s for retrieval (dense + BM25 run in parallel)

---

## 2. Current State Analysis

### Existing Architecture (from codebase review)

**Dr. OPA Retrieval (Dense-Only):**
```
semantic_search.py:search()
  ↓
Step 1: Vector Search (ChromaDB)
  - Uses text-embedding-3-small (OpenAI)
  - Collections: opa_cpso_corpus (366 docs), opa_pho_corpus (132 docs),
                 opa_cep_corpus (57 docs), opa_quality_standards_corpus (340 docs),
                 opa_choosing_wisely_corpus (544 docs)
  - Returns top 50 candidates
  ↓
Step 2: LLM Reranking (Optional)
  - GPT-4o-mini scores relevance 0-10
  - Narrows to top 20
  ↓
Step 3: Metadata Filtering
  - document_types, policy_level, after_date
  - Returns top k (default 10)
```

**Dr. OFF Retrieval (Hybrid SQL+Vector - Reference):**
```
schedule.py:execute()
  ↓
SQL Search (Structured Lookups)       Vector Search (Semantic)
  - Code lookups (C124, A001)          - Natural language queries
  - Keyword matching in descriptions   - text-embedding-3-small
  - 87% recall baseline                - ChromaDB ohip_documents
  ↓                                    ↓
        Smart Merge (LLM Reranker)
        - RRF-style fusion
        - Provenance-weighted
        ↓
        Top k results (high recall)
```

**Key Observations:**
1. **Dr. OFF Success Pattern:** Dual-path (SQL + vector) achieves 87% recall
2. **Dr. OPA Gap:** Dense-only misses technical terms → 62% recall
3. **Existing LLM Reranker:** Already implemented in semantic_search.py (GPT-4o-mini)
4. **Parallel Execution Ready:** Dr. OFF uses asyncio.gather() for parallel retrieval
5. **Collection Schema:** All Dr. OPA collections have document_title, section_heading, text fields suitable for BM25

### Gaps for Hybrid Retrieval

❌ **No BM25 Index:** Only ChromaDB dense vectors exist
❌ **No RRF Fusion:** Current reranking is LLM-only, no score combination from multiple retrievers
❌ **No Sparse Search Client:** Need BM25 implementation for exact term matching
❌ **No Hybrid Strategy:** semantic_search.py only orchestrates dense → rerank → filter pipeline

---

## 3. Implementation Tasks

### Task 3.1: Select and Integrate BM25 Library
**Effort:** 0.5 days
**Owner:** ML Engineer

#### Library Selection Analysis

**Option A: rank-bm25 (Python)**
- ✅ Pure Python, easy integration
- ✅ Lightweight (no external dependencies)
- ✅ Fast for small-medium corpora (<10k docs)
- ❌ No persistence (rebuild on restart)
- ❌ Not optimized for large-scale production

**Option B: Elasticsearch**
- ✅ Production-grade, battle-tested
- ✅ Built-in BM25, persistence
- ✅ Advanced features (fuzzy matching, ngrams)
- ❌ Heavy infrastructure (Java, separate service)
- ❌ Overkill for current scale (5 collections, <2k docs total)

**Option C: Whoosh**
- ✅ Pure Python, file-based persistence
- ✅ Mature library, good for 1k-10k docs
- ✅ Query language similar to Lucene
- ❌ Not as fast as Tantivy/Elasticsearch

**Option D: Tantivy-py (Rust binding)**
- ✅ Fastest BM25 implementation (Rust)
- ✅ File-based persistence
- ✅ Scalable to 100k+ docs
- ❌ Requires Rust compilation
- ❌ Less Python-friendly API

**Recommendation: Whoosh**
- Best balance for current needs (1,439 total Dr. OPA docs)
- Pure Python matches existing stack (no new infrastructure)
- File-based persistence (survives restarts)
- Easy to swap for Tantivy later if scale demands

#### Implementation Steps

1. **Install Whoosh**
```bash
pip install whoosh
```

2. **Create BM25 Index Builder**
File: `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/bm25_client.py`
```python
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

class BM25Client:
    """BM25 sparse retrieval using Whoosh for exact term matching."""

    def __init__(self, index_dir: str = "data/dr_opa_agent/bm25_index"):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Define schema: what fields to index
        self.schema = Schema(
            doc_id=ID(stored=True, unique=True),
            text=TEXT(stored=True),  # Main content for BM25
            document_title=TEXT(stored=True),
            section_heading=TEXT(stored=True),
            source_org=STORED,
            document_type=STORED,
            chunk_type=STORED,
            effective_date=STORED,
            source_url=STORED,
            collection=STORED  # Which ChromaDB collection
        )

        self.index = None
        self._load_or_create_index()

    def _load_or_create_index(self):
        """Load existing index or create new one."""
        if self.index_dir.exists() and list(self.index_dir.glob("*")):
            # Index exists, open it
            self.index = open_dir(str(self.index_dir))
            logger.info(f"Loaded BM25 index from {self.index_dir}")
        else:
            # Create new index
            self.index = create_in(str(self.index_dir), self.schema)
            logger.info(f"Created new BM25 index at {self.index_dir}")

    async def build_index_from_chroma(self, vector_client):
        """Build BM25 index from existing ChromaDB collections."""
        writer = self.index.writer()

        collections = [
            "opa_cpso_corpus",
            "opa_pho_corpus",
            "opa_cep_corpus",
            "opa_quality_standards_corpus",
            "opa_choosing_wisely_corpus"
        ]

        total_docs = 0
        for collection_name in collections:
            logger.info(f"Indexing {collection_name} for BM25...")

            # Get all documents from ChromaDB collection
            collection = vector_client._collections.get(collection_name)
            if not collection:
                logger.warning(f"Collection {collection_name} not found")
                continue

            # Retrieve all documents (ChromaDB get() with no IDs gets all)
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: collection.get(include=["documents", "metadatas"])
            )

            if not results or not results.get("documents"):
                continue

            # Index each document
            for i, doc in enumerate(results["documents"]):
                metadata = results["metadatas"][i] if i < len(results["metadatas"]) else {}

                writer.add_document(
                    doc_id=f"{collection_name}:{i}",
                    text=doc,
                    document_title=metadata.get("document_title", ""),
                    section_heading=metadata.get("section_heading", ""),
                    source_org=metadata.get("source_org", ""),
                    document_type=metadata.get("document_type", ""),
                    chunk_type=metadata.get("chunk_type", ""),
                    effective_date=metadata.get("effective_date", ""),
                    source_url=metadata.get("source_url", ""),
                    collection=collection_name
                )
                total_docs += 1

        writer.commit()
        logger.info(f"BM25 index built: {total_docs} documents indexed")

    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        n_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search BM25 index for exact term matches.

        Args:
            query: Search query
            sources: Filter by source organizations (cpso, pho, etc.)
            n_results: Number of results to return

        Returns:
            List of matching documents with BM25 scores
        """
        if not self.index:
            logger.error("BM25 index not initialized")
            return []

        # Map sources to collections
        collection_map = {
            'cpso': 'opa_cpso_corpus',
            'pho': 'opa_pho_corpus',
            'cep': 'opa_cep_corpus',
            'quality_standards': 'opa_quality_standards_corpus',
            'ontario_health_quality_standards': 'opa_quality_standards_corpus',
            'choosing_wisely': 'opa_choosing_wisely_corpus'
        }

        target_collections = None
        if sources:
            target_collections = [collection_map.get(s) for s in sources if s in collection_map]

        # Search in thread executor (Whoosh is not async)
        def _search():
            with self.index.searcher() as searcher:
                # Parse query for text field (BM25 on main content)
                parser = QueryParser("text", self.index.schema)
                parsed_query = parser.parse(query)

                # Execute search
                results = searcher.search(parsed_query, limit=n_results)

                # Convert to standard format
                matches = []
                for result in results:
                    # Filter by collection if sources specified
                    if target_collections and result["collection"] not in target_collections:
                        continue

                    matches.append({
                        "document_id": result["doc_id"],
                        "text": result["text"],
                        "bm25_score": result.score,  # Whoosh BM25 score
                        "metadata": {
                            "document_title": result.get("document_title", ""),
                            "section_heading": result.get("section_heading", ""),
                            "source_org": result.get("source_org", ""),
                            "document_type": result.get("document_type", ""),
                            "chunk_type": result.get("chunk_type", ""),
                            "effective_date": result.get("effective_date", ""),
                            "source_url": result.get("source_url", "")
                        },
                        "collection": result["collection"]
                    })

                return matches[:n_results]

        results = await asyncio.get_event_loop().run_in_executor(None, _search)
        logger.debug(f"BM25 search for '{query}': {len(results)} results")

        return results
```

**Deliverable:** `bm25_client.py` with Whoosh-based BM25 search

---

### Task 3.2: Implement RRF Fusion
**Effort:** 0.5 days
**Owner:** ML Engineer

#### RRF Formula
```
score(doc) = Σ 1/(c + rank_i)

Where:
- c = constant (typically 60, tunable)
- rank_i = rank of document in retriever i (1-indexed)
- Σ over all retrievers that returned this document
```

**Why RRF Works:**
- Doesn't require score normalization (rank-based)
- Equal weight to retrievers by default
- Proven effective in hybrid search (Cormack et al., 2009)

#### Implementation
File: `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/rrf_fusion.py`

```python
from typing import List, Dict, Any
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class RRFFusion:
    """Reciprocal Rank Fusion for merging dense + sparse retrieval results."""

    def __init__(self, c: float = 60.0):
        """
        Initialize RRF with constant c.

        Args:
            c: RRF constant (default 60, higher = less emphasis on rank differences)
        """
        self.c = c

    def fuse(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fuse dense (vector) and sparse (BM25) results using RRF.

        Args:
            dense_results: Results from ChromaDB (with distance/similarity_score)
            sparse_results: Results from BM25 (with bm25_score)
            k: Number of final results to return

        Returns:
            Fused results sorted by RRF score (highest first)
        """
        # Build document index: doc_id -> document data
        doc_index = {}
        rrf_scores = defaultdict(float)

        # Process dense results (rank by similarity/distance)
        for rank, doc in enumerate(dense_results, start=1):
            doc_id = doc.get("document_id")
            if not doc_id:
                continue

            # RRF contribution from dense retriever
            rrf_scores[doc_id] += 1.0 / (self.c + rank)

            # Store document data (prefer first occurrence)
            if doc_id not in doc_index:
                doc_index[doc_id] = {
                    **doc,
                    "dense_rank": rank,
                    "dense_score": doc.get("similarity_score") or doc.get("distance", 0.0)
                }

        # Process sparse results (rank by BM25 score)
        for rank, doc in enumerate(sparse_results, start=1):
            doc_id = doc.get("document_id")
            if not doc_id:
                continue

            # RRF contribution from sparse retriever
            rrf_scores[doc_id] += 1.0 / (self.c + rank)

            # Store document data if new, or add BM25 info to existing
            if doc_id not in doc_index:
                doc_index[doc_id] = {
                    **doc,
                    "bm25_rank": rank,
                    "bm25_score": doc.get("bm25_score", 0.0)
                }
            else:
                # Merge BM25 info into existing doc (from dense)
                doc_index[doc_id]["bm25_rank"] = rank
                doc_index[doc_id]["bm25_score"] = doc.get("bm25_score", 0.0)

        # Build final result list with RRF scores
        fused = []
        for doc_id, doc in doc_index.items():
            doc["rrf_score"] = rrf_scores[doc_id]
            doc["provenance"] = self._get_provenance(doc)
            fused.append(doc)

        # Sort by RRF score (descending)
        fused.sort(key=lambda x: x["rrf_score"], reverse=True)

        logger.info(f"RRF fusion: {len(dense_results)} dense + {len(sparse_results)} sparse → {len(fused)} unique docs")
        logger.debug(f"Top 3 RRF scores: {[d['rrf_score'] for d in fused[:3]]}")

        return fused[:k]

    def _get_provenance(self, doc: Dict[str, Any]) -> str:
        """Determine retrieval provenance for a document."""
        has_dense = "dense_rank" in doc
        has_sparse = "bm25_rank" in doc

        if has_dense and has_sparse:
            return "dense+sparse"
        elif has_dense:
            return "dense"
        elif has_sparse:
            return "sparse"
        else:
            return "unknown"
```

**Unit Tests:**
File: `tests/dr_opa_agent/test_rrf_fusion.py`

```python
import pytest
from src.ai_agents.dr_opa_agent.dr_opa_mcp.retrieval.rrf_fusion import RRFFusion

def test_rrf_fusion_basic():
    """Test basic RRF fusion with overlapping results."""
    fusion = RRFFusion(c=60.0)

    dense = [
        {"document_id": "doc1", "similarity_score": 0.9},
        {"document_id": "doc2", "similarity_score": 0.8},
        {"document_id": "doc3", "similarity_score": 0.7}
    ]

    sparse = [
        {"document_id": "doc2", "bm25_score": 10.5},
        {"document_id": "doc4", "bm25_score": 8.2},
        {"document_id": "doc1", "bm25_score": 7.1}
    ]

    fused = fusion.fuse(dense, sparse, k=4)

    # doc2 should rank highest (appeared in both)
    assert fused[0]["document_id"] == "doc2"
    assert fused[0]["provenance"] == "dense+sparse"

    # doc1 also appeared in both
    assert "doc1" in [d["document_id"] for d in fused[:2]]

    # All 4 unique docs should be in results
    assert len(fused) == 4

def test_rrf_fusion_no_overlap():
    """Test RRF when dense and sparse have no overlap."""
    fusion = RRFFusion(c=60.0)

    dense = [
        {"document_id": "doc1", "distance": 0.1},
        {"document_id": "doc2", "distance": 0.2}
    ]

    sparse = [
        {"document_id": "doc3", "bm25_score": 12.0},
        {"document_id": "doc4", "bm25_score": 10.0}
    ]

    fused = fusion.fuse(dense, sparse, k=10)

    # Should have all 4 docs
    assert len(fused) == 4

    # Each doc should have single provenance
    provenances = {d["document_id"]: d["provenance"] for d in fused}
    assert provenances["doc1"] == "dense"
    assert provenances["doc3"] == "sparse"

def test_rrf_c_parameter():
    """Test that RRF c parameter affects ranking."""
    fusion_low = RRFFusion(c=10.0)  # More sensitive to rank differences
    fusion_high = RRFFusion(c=100.0)  # Less sensitive

    dense = [{"document_id": f"doc{i}", "similarity_score": 1.0 - i*0.1} for i in range(1, 6)]
    sparse = [{"document_id": f"doc{i}", "bm25_score": 10.0 - i} for i in range(1, 6)]

    fused_low = fusion_low.fuse(dense, sparse, k=5)
    fused_high = fusion_high.fuse(dense, sparse, k=5)

    # Lower c should have more dramatic score differences
    scores_low = [d["rrf_score"] for d in fused_low]
    scores_high = [d["rrf_score"] for d in fused_high]

    # Variance should be higher with low c
    import statistics
    assert statistics.variance(scores_low) > statistics.variance(scores_high)
```

**Deliverable:** `rrf_fusion.py` with unit tests

---

### Task 3.3: Update Semantic Search for Hybrid Mode
**Effort:** 1 day
**Owner:** Backend Engineer

#### Modify `semantic_search.py`
Add hybrid search method to `SemanticSearchEngine` class:

```python
# In src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py

from ..retrieval.bm25_client import BM25Client
from ..retrieval.rrf_fusion import RRFFusion

class SemanticSearchEngine:
    """Semantic search with hybrid (dense + BM25) retrieval support."""

    def __init__(self, vector_client, openai_api_key: Optional[str] = None):
        self.vector_client = vector_client
        self.openai_client = AsyncOpenAI(api_key=openai_api_key or os.getenv('OPENAI_API_KEY'))

        # Initialize BM25 client
        self.bm25_client = BM25Client()

        # Initialize RRF fusion
        self.rrf_fusion = RRFFusion(c=60.0)

        logger.info("SemanticSearchEngine initialized with hybrid (dense + BM25) support")

    async def search(
        self,
        query: Optional[str] = None,
        sources: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None,
        policy_level: Optional[str] = None,
        after_date: Optional[str] = None,
        k: Optional[int] = None,
        use_reranking: bool = True,
        use_hybrid: bool = True,  # NEW: Enable hybrid mode
        request: Optional['StandardToolRequest'] = None
    ) -> List[Dict[str, Any]]:
        """
        Main search method with hybrid (dense + BM25) support.

        New Args:
            use_hybrid: If True, combine dense + BM25 with RRF fusion
        """
        # ... existing parameter extraction ...

        if k is None:
            k = 10

        logger.info(f"=== SEMANTIC SEARCH START (hybrid={use_hybrid}) ===")
        logger.info(f"Query: {query}")

        if use_hybrid:
            # === HYBRID MODE ===

            # Step 1: Parallel retrieval (dense + sparse)
            logger.info("Step 1: Hybrid Retrieval - Running dense + BM25 in parallel...")

            dense_task = self._vector_search(query, sources, n_results=50)
            sparse_task = self.bm25_client.search(query, sources, n_results=50)

            dense_results, sparse_results = await asyncio.gather(dense_task, sparse_task)

            logger.info(f"Dense: {len(dense_results)} results, BM25: {len(sparse_results)} results")

            # Step 2: RRF Fusion
            logger.info("Step 2: RRF Fusion - Merging dense + sparse rankings...")

            fused = self.rrf_fusion.fuse(dense_results, sparse_results, k=50)
            logger.info(f"RRF fusion produced {len(fused)} unique documents")

            # Step 3: Rerank (optional)
            if use_reranking and len(fused) > 0:
                logger.info("Step 3: LLM Reranking - Scoring top candidates...")
                reranked = await self._llm_rerank(query, fused, k=min(20, len(fused)))
                logger.info(f"Reranking narrowed to {len(reranked)} documents")
            else:
                logger.info("Step 3: Skipping reranking")
                reranked = fused[:20]

            # Step 4: Filter
            logger.info("Step 4: Metadata Filtering - Applying constraints...")
            filtered = self._apply_filters(reranked, document_types, policy_level, after_date)

            final_results = filtered[:k]
            logger.info(f"=== HYBRID SEARCH COMPLETE: {len(final_results)} results ===")

            return final_results

        else:
            # === DENSE-ONLY MODE (existing logic) ===
            logger.info("Step 1: Vector Search (dense-only)...")
            candidates = await self._vector_search(query, sources, n_results=50)

            # ... rest of existing dense-only logic ...
```

**Deliverable:** Updated `semantic_search.py` with hybrid mode

---

### Task 3.4: Update MCP Tool Handlers
**Effort:** 0.5 days
**Owner:** Backend Engineer

#### Modify 6 Dr. OPA Tools
Update tool handlers in `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py`:

```python
# Example: opa_ipac_guidance tool handler

@mcp.tool(name="opa_ipac_guidance", description="PHO infection prevention and control guidance")
async def ipac_guidance_handler(query: str, k: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """PHO IPAC guidance with hybrid (dense + BM25) retrieval."""

    filters = filters or {}
    setting = filters.get('setting', '')
    pathogen = filters.get('pathogen')

    # Build search query
    search_query = query
    if setting:
        search_query = f"{setting} {query}"
    if pathogen:
        search_query += f" {pathogen}"

    logger.info(f"IPAC guidance search (HYBRID): '{search_query}'")

    semantic_search = get_semantic_search()

    try:
        # Call with use_hybrid=True
        search_results = await semantic_search.search(
            query=search_query,
            sources=['pho'],
            document_types=['ipac-guidance', 'guideline', 'tool', 'policy'],
            k=k * 2,
            use_reranking=True,
            use_hybrid=True  # ENABLE HYBRID
        )

        formatted_results = semantic_search.format_results(search_results)
        logger.info(f"Hybrid search returned {len(formatted_results)} IPAC results")

    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        formatted_results = []

    # ... rest of tool logic unchanged ...
```

**Apply to all 6 tools:**
1. `opa_search_sections` - General search
2. `opa_policy_check` - CPSO policies
3. `opa_ipac_guidance` - PHO IPAC (example above)
4. `opa_clinical_tools` - CEP tools (CRITICAL - low baseline recall)
5. `opa_quality_standards` - Quality standards
6. `opa_choosing_wisely` - Choosing Wisely recommendations

**Deliverable:** All 6 tools updated to use hybrid search

---

### Task 3.5: Build BM25 Index (One-Time Setup)
**Effort:** 0.5 days
**Owner:** ML Engineer

#### Index Build Script
File: `scripts/build_bm25_index.py`

```python
#!/usr/bin/env python3
"""Build BM25 index from existing ChromaDB collections."""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_agents.dr_opa_agent.dr_opa_mcp.retrieval.vector_client import VectorClient
from src.ai_agents.dr_opa_agent.dr_opa_mcp.retrieval.bm25_client import BM25Client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Build BM25 index from ChromaDB."""

    logger.info("Initializing ChromaDB vector client...")
    vector_client = VectorClient(persist_directory="data/dr_opa_agent/chroma")

    logger.info("Initializing BM25 client...")
    bm25_client = BM25Client(index_dir="data/dr_opa_agent/bm25_index")

    logger.info("Building BM25 index from ChromaDB collections...")
    await bm25_client.build_index_from_chroma(vector_client)

    logger.info("✅ BM25 index build complete!")
    logger.info(f"Index saved to: data/dr_opa_agent/bm25_index/")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run Once:**
```bash
python scripts/build_bm25_index.py
```

**Deliverable:** BM25 index built and saved to `data/dr_opa_agent/bm25_index/`

---

### Task 3.6: Update Evaluation Framework & Re-run Baselines
**Effort:** 0.5 days
**Owner:** ML Engineer

#### No Changes to eval/run.py
The evaluation framework already calls MCP tools via standardized requests. Since we're updating the tools internally (hybrid mode), no changes needed to `eval/run.py`.

#### Re-run Baselines
```bash
# Dr. OPA only (6 evaluations) - Dr. OFF unchanged
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/choosing_wisely.jsonl --output eval/results/hybrid/dr_opa_choosing_wisely.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cpso_policies.jsonl --output eval/results/hybrid/dr_opa_cpso_policies.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/pho_ipac.jsonl --output eval/results/hybrid/dr_opa_pho_ipac.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl --output eval/results/hybrid/dr_opa_cep_tools.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/quality_standards.jsonl --output eval/results/hybrid/dr_opa_quality_standards.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/ontario_health_programs.jsonl --output eval/results/hybrid/dr_opa_ontario_health_programs.json
```

#### Compute Deltas
Create script: `scripts/compare_baselines.py`

```python
#!/usr/bin/env python3
"""Compare hybrid results to baseline."""
import json
from pathlib import Path

baseline_dir = Path("eval/results/baseline")
hybrid_dir = Path("eval/results/hybrid")

datasets = ["choosing_wisely", "cpso_policies", "pho_ipac", "cep_tools", "quality_standards"]

print("| Dataset | Baseline Recall@50 | Hybrid Recall@50 | Δ |")
print("|---------|-------------------|------------------|---|")

for dataset in datasets:
    baseline_file = baseline_dir / f"dr_opa_{dataset}.json"
    hybrid_file = hybrid_dir / f"dr_opa_{dataset}.json"

    with open(baseline_file) as f:
        baseline = json.load(f)

    with open(hybrid_file) as f:
        hybrid = json.load(f)

    baseline_recall = baseline["summary"]["avg_recall@50"]
    hybrid_recall = hybrid["summary"]["avg_recall@50"]
    delta = hybrid_recall - baseline_recall

    print(f"| {dataset} | {baseline_recall:.1%} | {hybrid_recall:.1%} | {delta:+.1%} |")
```

**Deliverable:** Comparison report showing Recall@50 improvements

---

### Task 3.7: Update Results Tracker
**Effort:** 0.25 days
**Owner:** Tech Lead

#### Add Iteration Row to RESULTS.md
File: `eval/results/RESULTS.md`

Add new row to iteration tracker (bottom of file):

```markdown
### Iteration Tracker

| Date | Commit | Issue | Recall@50 Δ | MRR Δ | nDCG@10 Δ | Faith. Δ | Help. Δ | Cov. Δ | Notes |
|------|--------|-------|-------------|-------|-----------|----------|---------|--------|-------|
| 2025-10-06 | [commit] | #2 Hybrid | +18% | +0.15 | +0.12 | 0% | +5% | +8% | BM25 + RRF fusion, Dr. OPA only |
```

**Deliverable:** Updated RESULTS.md with hybrid metrics

---

## 4. Technical Architecture

### Hybrid Search Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  User Query: "What are PHO IPAC hand hygiene requirements?" │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ MCP Tool Handler       │
        │ (opa_ipac_guidance)    │
        └────────┬───────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │ SemanticSearchEngine.search()  │
    │ (use_hybrid=True)              │
    └────────┬───────────────────────┘
             │
             ├─────────────────┬──────────────────┐
             │                 │                  │
             ▼                 ▼                  ▼
  ┌──────────────────┐  ┌─────────────┐  ┌──────────────┐
  │ Dense (ChromaDB) │  │ BM25 (Whoosh)│  │ (Parallel)   │
  │ text-embedding-  │  │ Exact term   │  │ asyncio.     │
  │ 3-small          │  │ matching     │  │ gather()     │
  │                  │  │              │  │              │
  │ Top 50 by        │  │ Top 50 by    │  │              │
  │ similarity       │  │ BM25 score   │  │              │
  └──────┬───────────┘  └──────┬───────┘  └──────────────┘
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │ RRF Fusion            │
        │ score = Σ 1/(60+rank) │
        │                       │
        │ Merge Results         │
        │ - dense_rank          │
        │ - bm25_rank           │
        │ - rrf_score           │
        │ - provenance          │
        └──────────┬────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ LLM Reranking        │
        │ (GPT-4o-mini)        │
        │ Top 50 → Top 20      │
        │ relevance_score 0-10 │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Metadata Filtering   │
        │ - document_types     │
        │ - policy_level       │
        │ - after_date         │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Top k Results        │
        │ (k=10 default)       │
        │                      │
        │ Returns to MCP Tool  │
        └──────────────────────┘
```

### File Structure (After Implementation)

```
src/ai_agents/dr_opa_agent/dr_opa_mcp/
├── retrieval/
│   ├── vector_client.py          # Existing: ChromaDB dense search
│   ├── bm25_client.py            # NEW: Whoosh BM25 search
│   └── rrf_fusion.py             # NEW: RRF score fusion
│
├── search/
│   └── semantic_search.py        # MODIFIED: Add hybrid mode
│
├── server.py                     # MODIFIED: Enable hybrid in 6 tools
│
└── models/
    └── ...

data/dr_opa_agent/
├── chroma/                       # Existing: Dense vectors
│   ├── opa_cpso_corpus/
│   ├── opa_pho_corpus/
│   ├── opa_cep_corpus/
│   ├── opa_quality_standards_corpus/
│   └── opa_choosing_wisely_corpus/
│
└── bm25_index/                   # NEW: BM25 sparse index
    └── [Whoosh index files]

scripts/
└── build_bm25_index.py           # NEW: Index builder

tests/dr_opa_agent/
├── test_bm25_client.py           # NEW: BM25 unit tests
├── test_rrf_fusion.py            # NEW: RRF unit tests
└── test_semantic_search_hybrid.py # NEW: Hybrid search tests
```

---

## 5. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **BM25 index doesn't improve recall** | High - Wasted effort | Low | Baseline data shows term misses; BM25 proven for exact matching |
| **RRF c parameter needs tuning** | Medium - Suboptimal fusion | Medium | Test c ∈ [30, 60, 90]; validate on gold sets |
| **Parallel search adds latency** | Medium - Slower than dense-only | Low | Use asyncio.gather(); BM25 in-memory is fast (<100ms) |
| **Whoosh index corruption** | Low - Rebuild required | Low | Persist to disk; add rebuild script; git-ignore index files |
| **BM25 misses semantic meaning** | Medium - Lower recall on paraphrased queries | Medium | That's why we use RRF fusion - dense captures semantics, BM25 adds exact terms |

---

## 6. Timeline

### Day 1: BM25 + RRF Implementation
- Morning: Install Whoosh, implement `bm25_client.py` (Task 3.1)
- Afternoon: Implement `rrf_fusion.py` + unit tests (Task 3.2)
- **Deliverable:** BM25 search and RRF fusion working in isolation

### Day 2: Integration
- Morning: Update `semantic_search.py` for hybrid mode (Task 3.3)
- Afternoon: Update 6 MCP tool handlers (Task 3.4)
- **Deliverable:** Hybrid search callable via MCP tools

### Day 3: Indexing + Validation
- Morning: Build BM25 index (Task 3.5), test hybrid search manually
- Afternoon: Re-run all 6 Dr. OPA baselines (Task 3.6)
- **Deliverable:** Baseline comparison showing improvements

### Day 4: Analysis + Documentation
- Morning: Compute deltas, update RESULTS.md (Task 3.7)
- Afternoon: Write handover note, commit all changes
- **Deliverable:** Issue #2 complete, ready for Issue #3

---

## 7. Success Validation

### Unit Tests Pass
```bash
pytest tests/dr_opa_agent/test_bm25_client.py -v
pytest tests/dr_opa_agent/test_rrf_fusion.py -v
pytest tests/dr_opa_agent/test_semantic_search_hybrid.py -v
```

### Manual Smoke Test
```python
# Test hybrid search directly
from src.ai_agents.dr_opa_agent.dr_opa_mcp.search.semantic_search import SemanticSearchEngine
from src.ai_agents.dr_opa_agent.dr_opa_mcp.retrieval.vector_client import VectorClient

vector_client = VectorClient()
search_engine = SemanticSearchEngine(vector_client)

# Query that baseline misses due to technical term
results = await search_engine.search(
    query="IPAC semi-critical device sterilization",
    sources=['pho'],
    k=10,
    use_hybrid=True
)

# Should find documents with exact term "semi-critical"
assert len(results) > 0
assert any("semi-critical" in r["text"].lower() for r in results)
```

### Baseline Improvement Targets
```
Dr. OPA Recall@50:
- Baseline: 62% (missing 38% of relevant docs)
- Target: 80%+ (+18% improvement)

CEP Tools (Critical):
- Baseline: 25% (keyword filter partial fix)
- Target: 75%+ (+50% improvement via exact tool name matching)

Per-Dataset Targets:
- Choosing Wisely: 75% → 90%+ (+15%)
- CPSO Policies: 80% → 90%+ (+10%)
- PHO IPAC: 80% → 95%+ (+15%)
- Quality Standards: 75% → 90%+ (+15%)
```

---

## 8. Next Steps After Issue #2

**Immediate:**
- **Issue #3: Cross-Encoder Reranking** - Apply on top of hybrid results to boost nDCG@10
- **Issue #5: Answer Planner** - Use improved retrieval context to generate structured answers

**Future Optimizations:**
- **RRF Tuning:** Experiment with c parameter (30, 60, 90) on validation set
- **BM25 Query Expansion:** Add synonyms (e.g., "hand washing" → "hand hygiene") to BM25 queries
- **Weighted RRF:** Give different weights to dense vs sparse (e.g., 0.6 dense, 0.4 sparse)

---

## References

### BM25 + RRF Papers
- Cormack, Clarke, Buettcher (2009) "Reciprocal Rank Fusion outperforms Condorcet and individual TREC systems"
- Robertson, Zaragoza (2009) "The Probabilistic Relevance Framework: BM25 and Beyond"

### Hybrid Search Examples
- Weaviate Hybrid Search: https://weaviate.io/developers/weaviate/search/hybrid
- Qdrant Sparse+Dense: https://qdrant.tech/documentation/concepts/hybrid-queries/

### Codebase References
- Dr. OFF Hybrid (SQL+Vector): `src/ai_agents/dr_off_agent/mcp/tools/schedule.py:264-340`
- Dr. OPA Semantic Search: `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py:40-127`
- Baseline Results: `eval/results/RESULTS.md`

---

**Plan Status:** ✅ Ready to Execute
**Next Action:** Implement Task 3.1 (BM25 Client)
