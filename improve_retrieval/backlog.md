# GitHub Issue Backlog

## Critical Review: What Actually Works (2025-10-06)

After testing Issues #2 (Hybrid Retrieval) and #3 (Cross-Encoder Reranking), **both approaches FAILED to improve performance**. Here's what we learned:

### ❌ **What DOESN'T Work:**

1. **Hybrid Retrieval (BM25 + Dense):**
   - **Why it failed:** Baseline Recall@50 already at 75-80% (not 40% as initially assumed)
   - Medical/policy queries are semantic ("hand hygiene protocols"), not keyword-based
   - Dense embeddings already capture semantic meaning well
   - RRF fusion **degraded ranking** (MRR dropped 32% for CPSO)
   - **Verdict:** Skip for specialized domains with good semantic chunking

2. **Cross-Encoder Reranking (General Models):**
   - **Why it failed:** bge-reranker-v2-m3 lacks medical domain understanding
   - Prioritizes keyword overlap over semantic intent
   - Example: Ranked "surgical procedures" higher than "general hand hygiene" for query about procedure rooms
   - MRR dropped 68%, nDCG@10 dropped 57%
   - **Verdict:** General cross-encoders degrade performance in specialized domains

### ✅ **What DOES Work:**

1. **Dense-only retrieval with domain-specific embeddings:**
   - text-embedding-3-small captures medical semantic relationships
   - MRR 0.533 (baseline) vs 0.169 (cross-encoder) - **3x better**
   - Works well for semantic queries common in medical/policy domains

2. **Current baseline is actually decent for Dr. OPA:**
   - Recall@50: 75-80% (finding most relevant docs)
   - MRR: 0.533 (best doc at rank ~2)
   - **Real bottleneck:** Answer synthesis quality, not retrieval

### 🎯 **What to Focus On Next:**

**The real problem is NOT retrieval - it's answer synthesis:**
- Coverage: 19% → Need 85%+ (agent misses 81% of required facts)
- Helpfulness: 25% → Need 70%+ (answers don't address user's specific question)
- Tools return raw chunks; agent needs structured schemas per intent

**Issue #5 (Answer Planner + Self-Check) is the highest ROI:**
- Retrieval quality is decent (71% recall, MRR 0.503)
- Problem: Agent gets raw chunks, doesn't know what info is important
- Solution: Intent-specific schemas guide agent to extract/synthesize complete answers
- Expected: 3-4x improvement in Coverage/Helpfulness

**Issue #6 (Parent/Child Chunking) fixes critical failures:**
- CEP Tools: 0% Recall → Need to fix chunking strategy
- CPSO Policies: 10% Faithfulness → Better chunks reduce hallucination
- Provides richer context for agent synthesis

---

## 1. Eval & Observability Baseline ✅ COMPLETED

**Title:** Add retrieval & answer evaluation harness + richer tracing
**Why:** Establish baseline to quantify improvements with each change.
**Status:** ✅ Complete (2025-10-06)

**What Was Implemented:**
- ✅ Created 9 gold datasets: 3 Dr. OFF (OHIP, ADP, ODB), 6 Dr. OPA (Choosing Wisely, CPSO, PHO IPAC, CEP, Quality Standards, OH Programs)
- ✅ Implemented eval framework: Recall@50, MRR, nDCG@10, Hit@10 (retrieval); Faithfulness, Helpfulness, Coverage (LLM-judge)
- ✅ Optimized evaluation: Keyword pre-filtering (70-90% reduction in LLM calls) + batch LLM eval (10 chunks/call)
- ✅ CLI working: `python eval/run.py --agent {dr_off|dr_opa} --set eval/gold/{path} --output results/{name}.json`
- ✅ All 9 baselines captured in `eval/results/baseline/` + summary in `eval/results/RESULTS.md`

**Baseline Results:**
- **Dr. OFF:** 87% Recall@50, 0.822 MRR, 0.963 nDCG@10, 97% Faithfulness, 33% Helpfulness, 24% Coverage
- **Dr. OPA:** 62% Recall@50, 0.335 MRR, 0.444 nDCG@10, 80% Faithfulness, 21% Helpfulness, 16% Coverage
- **Overall:** 71% Recall@50, 0.503 MRR, 0.635 nDCG@10, 86% Faithfulness, 25% Helpfulness, 19% Coverage

**Critical Issues Identified:**
1. **CPSO Policies:** 10% Faithfulness (agent hallucination despite 80% recall)
2. **CEP Tools:** 0% Recall (keyword filter mismatch)
3. **Low Coverage/Helpfulness:** Tools return raw chunks; agent needs structured schemas per intent

**Next Priority:** Issues #2 (Hybrid Retrieval) and #5 (Answer Planner) to address recall gaps and synthesis quality

---

## 2. Hybrid Retrieval (Dense + BM25) with RRF Fusion ⚠️ COMPLETED BUT NOT RECOMMENDED

**Title:** Implement hybrid retriever and RRF fusion endpoint
**Why:** Improve recall on codes/terms and semantics.
**Status:** ⚠️ Complete (2025-10-06) - **Did not improve performance, skip for now**

**What Was Implemented:**
- ✅ Added BM25 index using Whoosh (file-based, 1,439 documents indexed from 5 Dr. OPA collections)
- ✅ Implemented RRF fusion with c=60.0, provenance tracking (dense/sparse/both)
- ✅ Added `use_hybrid=True` parameter to all 6 Dr. OPA MCP tools
- ✅ Fixed critical bug: BM25 index was using sequential IDs instead of ChromaDB's actual document IDs (caused zero overlap)
- ✅ Added comprehensive logging for dense/sparse/RRF debugging

**Evaluation Results (vs Baseline):**
- **PHO IPAC:** 80% → 80% Recall@50 (0% improvement)
- **CPSO Policies:** 80% → 100% Recall@50 (+25%), but MRR: 0.800 → 0.545 (-32%) ⚠️ worse ranking
- **Quality Standards:** 75% → 75% Recall@50 (0% improvement)
- **Choosing Wisely:** 75% → 75% Recall@50 (0% improvement)
- **CEP Tools:** 0% → 25% Recall@50 (known keyword filter bug, unrelated to hybrid)

**Key Finding:**
Hybrid retrieval **did not help** because:
1. Baseline already had 75-80% Recall@50 (not 40% as handover suggested - baseline had empty ID bug)
2. Dr. OPA queries are semantic (e.g., "hand hygiene protocols") - dense embeddings handle these well
3. RRF fusion **degraded ranking quality** (MRR/nDCG) by diluting strong dense rankings
4. BM25 keyword matching doesn't add value for semantic medical queries with good chunking

**Recommendation:**
- **Skip hybrid search** - added complexity without benefit
- **Focus on Issue #3 (Cross-Encoder Reranking)** instead - improves ranking of already-retrieved docs
- The bottleneck is **ranking quality (MRR: 0.335, nDCG@10: 0.444)**, not recall

**Files:**
- Implementation: `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/bm25_client.py`, `rrf_fusion.py`
- Results: `eval/results/02_hybrid_search/`
- Documentation: `improve_retrieval/HYBRID_SEARCH_TECHNICAL_EXPLANATION.md`
- Unit tests: `tests/dr_opa_agent/test_rrf_fusion.py` (7 tests passing)

---

## 3. Cross-Encoder Reranker (Open-source) ❌ COMPLETED BUT FAILED

**Title:** Add local cross-encoder reranker (bge-reranker-v2-m3)
**Why:** Surface the exact clause; reduce "bookmark" answers. Expected to improve MRR/nDCG based on Issue #2 findings.
**Status:** ❌ Complete (2025-10-06) - **FAILED - Performance degraded significantly, DO NOT USE**

**What Was Implemented:**
- ✅ Implemented CrossEncoderReranker with bge-reranker-v2-m3
- ✅ Added lazy initialization to avoid model loading overhead
- ✅ Integrated into semantic_search.py pipeline (Step 3: CE reranking before filtering)
- ✅ Added unit tests with mocked model for CI/CD
- ✅ Pre-downloaded model (~1.2GB) to avoid timeout issues

**Evaluation Results (PHO IPAC, 5 queries):**
- **MRR:** 0.533 → 0.169 (**-68%**) ❌ Best doc moved from rank 2 to rank 6
- **nDCG@10:** 0.499 → 0.216 (**-57%**) ❌ Top-10 ranking quality degraded
- **Helpfulness:** 28% → 20% (-29%) ❌
- **Coverage:** 54.7% → 40.7% (-26%) ❌
- **Recall@50:** 80% → 80% (unchanged, as expected)

**Why It Failed - Root Cause Analysis:**

**Domain Mismatch:** bge-reranker-v2-m3 is a general-purpose cross-encoder trained on web/generic data. It lacks medical domain understanding:

**Example (Query: "What are hand hygiene requirements for procedure rooms?"):**
- **Baseline (Dense) Rank #1** ✅ CORRECT:
  - "4 Moments for Hand Hygiene", "When to clean hands", "Ontario's Just Clean Your Hands program"
  - Dense embeddings understood general procedure room hand hygiene guidance

- **Cross-Encoder Rank #1** ❌ WRONG:
  - "surgical hand rub", "surgical/invasive procedures", "operating rooms are cleaned"
  - Cross-encoder focused on keyword overlap ("procedure", "surgical", "hand") but missed semantic intent
  - **Key insight:** General model doesn't understand that "procedure rooms" ≠ "surgical/invasive procedures" in medical context

**Why Dense Embeddings Outperform:**
1. **Domain-specific training:** text-embedding-3-small captures medical semantic relationships through the corpus
2. **General cross-encoder:** Trained on web data, prioritizes keyword overlap over domain semantics
3. **Chunk size variability:** Chunks range 34-1,165 words; cross-encoder truncates at 512 tokens (~384 words), losing context

**Per-Query Impact:**
- Query 1 (hand hygiene): MRR 1.000 → 0.100 (perfect → rank 10)
- Query 2 (sterilization): MRR 1.000 → 0.333 (perfect → rank 3)
- Query 3 (mobile clinic): MRR 0.500 → 0.333 (rank 2 → rank 3)
- Query 4 (PPE): MRR 0.167 → 0.077 (rank 6 → rank 13)
- Query 5 (environmental cleaning): MRR 0.000 → 0.000 (both failed)

**Recommendation:**
- ❌ **DO NOT use cross-encoder reranking with general-purpose models** for specialized medical/policy domains
- ✅ **Stick with dense-only retrieval** (baseline) - domain-specific embeddings already perform well (MRR 0.533 vs CE 0.169)
- 🔮 **Future option:** Fine-tune a cross-encoder on medical domain data (requires labeled relevance judgments, out of current scope)

**Key Learning:**
General-purpose reranking models can **degrade performance** in specialized domains. Domain-specific dense embeddings trained on the corpus outperform generic cross-encoders for semantic matching.

**Files:**
- Implementation: `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/cross_encoder_reranker.py`
- Tests: `tests/dr_opa_agent/test_cross_encoder_reranker.py`
- Results: `eval/results/03_cross_encoder/dr_opa_pho_ipac.json`
- Pre-download script: `scripts/download_ce_model.py`

---

## 4. Intent Router (SQL-first for Billing/Drugs)

**Title:** Add intent classifier + routing policy for `retrieve()`  
**Why:** Ensure we hit SQL truth first when appropriate; constrain policy sources by intent.

**Scope:**
- Few-shot LLM or rules → intents: {Billing, Drugs, Devices, IPAC, Forms}.
- Router table:
    - Billing → SQL OHIP, then policy collections
    - Drugs → ODB SQL, then formulary policy
    - IPAC → PHO/CPSO/OH only (prefer PHO)
    - Forms → admin policies
- Expose as `retrieve_router(query)` that calls hybrid only on the chosen collections.

**Acceptance Criteria:**
- 90%+ of Billing/Drugs queries hit SQL before vector search (verified in logs).

---

## 5. Answer Planner + Self-Check Loop

**Title:** Add planner & self-check stages with schemas per intent  
**Why:** Convert snippets into decision-ready answers.

**Scope:**
- `plan(query, intent)` returns schema fields per intent:
    - Billing: primary_codes[], modifiers[], conditions[], common_misses[], citations[]
    - IPAC: requirements_mandatory, recommendations, setting_specifics, equipment_rooming, validation, citations[]
- `self_check(schema, context)` verifies slots filled & citations fresh; if not → generate focused sub-queries and call `retrieve()` again.

**Acceptance Criteria:**
- On gold set, Coverage increases (>85% fields filled).
- Answers include explicit citations supporting each slot.

---

## 6. Parent/Child Chunking + Metadata Enrichment + Synonyms

**Title:** Re-ingest with standardized chunking and enriched metadata  
**Why:** Higher-quality snippets and better sparse matching.

**Scope:**
- Chunk all collections to 300–800 tokens + 10% overlap; add parent_id, section_title, section_path.
- Add fields: effective_date, authority/source_org, aliases[], codes[] (OHIP, DIN, LU, ATC), setting[].
- Maintain small CSV synonym tables (OHIP alias, brand↔generic, device aliases) and inject into aliases[].

**Acceptance Criteria:**
- New indices built; retrieval returns child+parent context.
- Recall@50 improves on code/name variants.

---

## 7. Agentic Multi-Query Expansion

**Title:** Add automatic sub-query generation & fusion  
**Why:** Catch synonyms/codes/facets the user didn’t type.

**Scope:**
- `expand_queries(query, intent)` → 3–6 sub-queries: lexical (codes/brands), semantic paraphrases, and facet filters (setting/population/device).
- Call `search_hybrid` for each; RRF-fuse across sub-queries; then rerank.

**Acceptance Criteria:**
- Recall@50 + Hit@10 improve notably on IPAC and Billing golds.

---

## 8. Authority & Recency Weighting

**Title:** Add authority/recency scoring to final rank  
**Why:** Prefer PHO/MOH/CPSO and fresh guidance for IPAC/policy.

**Scope:**
- Final score = α*ce_score + β*authority + γ*recency_decay.
- Calibrate per intent (IPAC gets higher β, γ).

**Acceptance Criteria:**
- In IPAC golds, ≥80% of Top-10 items are PHO/MOH/CPSO and ≤24 months old (when applicable).

---

## 9. Observability Dashboards & “Why this chunk?” Trace

**Title:** Add `retrieval_evidence.json` and simple dashboard  
**Why:** Make misses diagnosable.

**Scope:**
- Log: intent, expanded queries, dense/sparse ranks, RRF scores, CE scores, chosen Top-k, rejected-but-close items, SQL hits.
- Optional Streamlit/Plotly page to visualize distributions per release.

**Acceptance Criteria:**
- For any query, devs can see exactly how items were selected.

---

## 10. (Later) Graph Summaries for Policy-Landscape Questions

**Title:** Prototype KG + local expansion for IPAC topics  
**Why:** Better “how is public health handling X?” answers.

**Scope:**
- Extract entity triples during ETL (procedure/device/setting/authority + requires/prohibits/updated_by).
- `graph_expand(topic)` returns a stitched summary + citations to include alongside Top-k.

**Acceptance Criteria:**
- SME rates Helpfulness higher than baseline on at least 3 IPAC “landscape” queries.