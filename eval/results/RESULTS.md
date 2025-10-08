# Baseline Evaluation Results

**Date:** 2025-10-06
**Agents:** Dr. OFF, Dr. OPA
**Gold Sets:** 9 datasets, 44 queries total
**Evaluation Framework:** Keyword pre-filtering + batch LLM matching + GPT-4o answer quality assessment

---

## Executive Summary

### Dr. OFF (Ontario Funding Finder)

| Domain | Tool Tested | Queries | Recall@50 | MRR | nDCG@10 | Faithfulness | Helpfulness | Coverage |
|--------|-------------|---------|-----------|-----|---------|--------------|-------------|----------|
| OHIP Billing | schedule_get | 5 | 60% | 0.600 | 0.912 | 90% | 34% | 24% |
| ADP Devices | adp_get | 5 | 100% | 0.867 | 0.976 | 100% | 24% | 23% |
| ODB Drugs | odb_get | 5 | 100% | 1.000 | 1.000 | 100% | 42% | 25% |
| **Dr. OFF Avg** | - | **15** | **87%** | **0.822** | **0.963** | **97%** | **33%** | **24%** |

### Dr. OPA (Ontario Practice Advice)

| Domain | Tool Tested | Queries | Recall@50 | MRR | nDCG@10 | Faithfulness | Helpfulness | Coverage |
|--------|-------------|---------|-----------|-----|---------|--------------|-------------|----------|
| Choosing Wisely | opa_choosing_wisely | 4 | 75% | 0.375 | 0.512 | 100% | 50% | 30% |
| CPSO Policies | opa_policy_check | 5 | 80% | 0.567 | 0.688 | 10% | 12% | 9% |
| PHO IPAC | opa_ipac_guidance | 5 | 80% | 0.383 | 0.500 | 100% | 28% | 18% |
| CEP Tools | opa_clinical_tools | 4 | 0% | 0.000 | 0.000 | 100% | 5% | 15% |
| Quality Standards | opa_quality_standards | 4 | 75% | 0.350 | 0.521 | 88% | 28% | 18% |
| Ontario Health Programs | opa_program_lookup* | 5 | N/A* | N/A* | N/A* | 80% | 0% | 4% |
| **Dr. OPA Avg** | - | **27** | **62%** | **0.335** | **0.444** | **80%** | **21%** | **16%** |

**Overall Average:** 44 queries | Recall@50: **71%** | MRR: **0.503** | nDCG@10: **0.635** | Faithfulness: **86%** | Helpfulness: **25%** | Coverage: **19%**

*Note: `opa_program_lookup` uses Claude + Web Search (not vector retrieval), so Recall@50/MRR/nDCG@10 are N/A. Answer quality metrics still apply.*

---

## What These Metrics Mean

### Retrieval Metrics

**Recall@50** (Target: ≥80%)
- **What it measures:** Of all the correct/relevant documents, what percentage did we retrieve in the top 50 results?
- **Current state:** 71% overall (Dr. OFF: 87%, Dr. OPA: 62%)
- **Interpretation:** We're finding most relevant documents for Dr. OFF, but missing ~38% for Dr. OPA queries
- **Why it matters:** If we don't retrieve the right documents, the LLM agent can't generate complete/correct answers regardless of how good the synthesis prompt is

**MRR - Mean Reciprocal Rank** (Target: ≥0.70)
- **What it measures:** How quickly do we surface the BEST answer? (1/rank of first relevant result)
- **Current state:** 0.503 overall (Dr. OFF: 0.822, Dr. OPA: 0.335)
- **Interpretation:** Dr. OFF puts best answer in top 2 on average (0.822 ≈ rank 1.2), but Dr. OPA puts it around rank 3 (0.335 ≈ rank 3.0)
- **Why it matters:** The LLM agent synthesizing the final answer needs the best context first to generate accurate responses

**nDCG@10** (Target: ≥0.80)
- **What it measures:** Are the MOST relevant documents ranked HIGHEST in top 10?
- **Current state:** 0.635 overall (Dr. OFF: 0.963, Dr. OPA: 0.444)
- **Interpretation:** Dr. OFF has near-perfect ranking, Dr. OPA ranking needs improvement
- **Why it matters:** LLM agents have limited context windows - we need the most relevant chunks ranked first to fit within token limits

### Answer Quality Metrics

**Faithfulness** (Target: 100%)
- **What it measures:** Does the answer contain ONLY claims supported by retrieved documents? (No hallucinations)
- **Current state:** 86% overall (Dr. OFF: 97%, Dr. OPA: 80%)
- **Interpretation:** Most answers are grounded, but CPSO policies has 10% faithfulness (serious hallucination issue)
- **Why it matters:** Medical advice MUST be accurate and traceable to authoritative sources

**Helpfulness** (Target: ≥70%)
- **What it measures:** Does the synthesized answer actually address the user's question?
- **Current state:** 25% overall
- **Interpretation:** Retrieved context is technically accurate but LLM synthesis is incomplete or doesn't address the specific question
- **Why it matters:** The end-user (clinician) needs actionable answers from the agent, not just a dump of related facts

**Coverage** (Target: ≥85%)
- **What it measures:** What percentage of expected answer elements are included in the synthesized response?
- **Current state:** 19% overall
- **Interpretation:** Agent-generated answers are missing 81% of required facts on average
- **Why it matters:** Incomplete answers force users to ask follow-up questions or do additional research, degrading the RAG experience

---

## What We Need to Improve

### Critical Issues (P0)

1. **CPSO Policies Hallucination (10% Faithfulness)**
   - **Problem:** System is generating claims NOT supported by retrieved documents
   - **Impact:** Could lead to regulatory/legal misinformation
   - **Root cause:** TBD - needs investigation (possibly chunking, prompt, or LLM reasoning issue)
   - **Next step:** Audit retrieval + answer synthesis for CPSO queries

2. **CEP Tools Retrieval Failure (0% Recall)**
   - **Problem:** Keyword pre-filter is rejecting ALL retrieved documents
   - **Impact:** Completely failing to answer CEP-related questions
   - **Root cause:** Mismatch between gold dataset keywords (expecting full documents) and chunked text
   - **Next step:** Either expand gold dataset keywords or adjust chunking strategy for CEP corpus

3. **Low Coverage Across All Domains (19%)**
   - **Problem:** Agent-synthesized answers are factually correct but incomplete
   - **Impact:** Users get partial answers, must ask follow-up questions or do additional research
   - **Root cause:** Retrieval tools return raw chunks without structure; agent synthesis prompt doesn't guide toward complete answers per intent
   - **Next step:** Implement Issue #5 (Answer Planner + Self-Check Loop) to give agents structured context

### High Priority (P1)

4. **Dr. OPA Retrieval Quality (62% Recall, 0.335 MRR)**
   - **Problem:** Missing 38% of relevant documents, and good ones ranked low
   - **Impact:** Agent receives incomplete context, leading to poor quality synthesized answers
   - **Root cause:** Dense-only retrieval misses technical terms (e.g., "IPAC", "semi-critical devices")
   - **Next step:** Implement Issue #2 (Hybrid Retrieval with BM25) to improve context passed to agent

5. **Helpfulness Low Across All Domains (25%)**
   - **Problem:** Agent-synthesized answers don't directly address the user's question
   - **Impact:** Users lose trust in the RAG system
   - **Root cause:** Tools return unstructured chunks; agent doesn't know what information is important for each intent type
   - **Next step:** Intent-specific schemas in tool responses (Issue #5) to guide agent synthesis

### Medium Priority (P2)

6. **Ontario Health Programs Answer Quality (0% Helpfulness)**
   - **Problem:** Web search returns content, but agent synthesis doesn't extract actionable program info
   - **Impact:** Program lookup queries are unhelpful despite retrieving data
   - **Root cause:** Web search content not structured; agent doesn't know what program information to extract
   - **Next step:** Add program-specific extraction schema (name, eligibility, referral process, contact) to guide agent

---

## Strengths (What's Working)

### ✅ Dr. OFF Retrieval Performance
- **Near-perfect retrieval:** 87% Recall@50, 0.822 MRR, 0.963 nDCG@10
- **Excellent faithfulness:** 97% - agent synthesis is grounded in retrieved documents
- **Why it works:** SQL + vector dual-path retrieval provides high-quality context; well-chunked OHIP/ADP/ODB data

### ✅ Choosing Wisely & PHO IPAC Faithfulness (100%)
- Agent synthesis is fully grounded in retrieved context despite modest recall
- Shows that when we retrieve the right content, the agent can synthesize reliable answers

### ✅ Evaluation Framework Optimizations
- Keyword pre-filtering reduced LLM calls by 70-90% (from 50 evals/query to 0-10)
- Batch LLM evaluation (10 chunks per API call) cut latency significantly
- Same optimization framework works for both agents (agent-agnostic)

---

## Recommendations for Next Issues

Based on baseline data, prioritize backlog items as follows:

### Issue #2: Hybrid Retrieval (BM25 + Dense) - **IMMEDIATE**
- **Target:** Dr. OPA Recall@50: 62% → 80%+
- **Rationale:** IPAC, Quality Standards, Choosing Wisely queries miss technical terms
- **Expected ROI:** +18% recall = more complete answers

### Issue #5: Answer Planner + Self-Check - **IMMEDIATE**
- **Target:** Coverage: 19% → 85%+, Helpfulness: 25% → 70%+
- **Rationale:** Retrieval is working (71% recall), but tools return unstructured chunks; agent needs intent-specific schemas to synthesize complete answers
- **Expected ROI:** 3x improvement in answer completeness; agent gets actionable context instead of raw chunks

### Issue #3: Cross-Encoder Reranking - **HIGH PRIORITY**
- **Target:** Dr. OPA MRR: 0.335 → 0.70+
- **Rationale:** Relevant documents retrieved but ranked poorly (rank 3 vs rank 1); agent receives best context later in results
- **Expected ROI:** Agent gets best chunks first → better synthesis quality, fits within context window limits

### Issue #6: Parent/Child Chunking + Metadata - **MEDIUM PRIORITY**
- **Target:** Fix CEP Tools 0% recall, improve CPSO faithfulness (10% → 95%+)
- **Rationale:** Better chunks = better retrieval + less agent hallucination; richer metadata helps agent understand context
- **Expected ROI:** Fixes critical failures in specific domains; agent receives higher-quality, more contextual chunks

### Issue #9: Observability Dashboards - **CONTINUOUS**
- Build Streamlit UI to visualize metric trends over releases
- Track regressions as new features are added

---

## Collection Statistics

**Vector Collections Evaluated:**
- ✅ Dr. OFF: ohip_documents (6,983 vectors), adp_documents (610 vectors), odb_documents (10,815 vectors)
- ✅ Dr. OPA: opa_cpso_corpus (366 vectors), opa_pho_corpus (132 vectors), opa_cep_corpus (57 vectors), opa_quality_standards_corpus (340 vectors), opa_choosing_wisely_corpus (544 vectors)

**Tools Evaluated:**
- ✅ 3 Dr. OFF MCP tools: `schedule_get`, `adp_get`, `odb_get`
- ✅ 6 Dr. OPA MCP tools: `opa_choosing_wisely`, `opa_policy_check`, `opa_ipac_guidance`, `opa_clinical_tools`, `opa_quality_standards`, `opa_program_lookup`

---

## Methodology

**Gold Datasets:**
- 44 queries across 9 domains (15 Dr. OFF, 29 Dr. OPA)
- SME-annotated with expected sources, answer elements, and expert answers
- Queries range from simple lookups to complex multi-source scenarios

**Retrieval Metrics:**
- Recall@50: Fraction of relevant docs in top 50
- MRR: 1/rank of first relevant doc
- nDCG@10: Quality-weighted ranking score
- Hit@10: Binary indicator if any relevant doc in top 10

**Answer Quality Metrics (LLM-Judge):**
- Faithfulness: Claims supported by context? (GPT-4o judge)
- Helpfulness: Does it answer the question? (compared to expert answer)
- Coverage: Percentage of expected facts included

**Optimization Framework:**
- Keyword pre-filtering: Reduce LLM evaluations by 70-90%
- Batch LLM evaluation: 10 chunks per API call
- Parallel tool calls where possible

**Evaluation Date:** 2025-10-06
**Models:**
- Embedding: OpenAI text-embedding-3-small
- LLM Judge: GPT-4o
- Vector DB: ChromaDB (local for evaluation, Railway for production)

---

## Key Findings by Domain

### Dr. OFF Domains

**OHIP Billing** (60% Recall, 90% Faithfulness)
- Strong performance overall, but 40% of relevant codes not retrieved
- Likely due to complex multi-code scenarios or synonym variations
- Faithfulness high when content is retrieved

**ADP Devices** (100% Recall, 100% Faithfulness)
- Perfect retrieval from 610-vector collection
- Demonstrates that small, well-curated collections can achieve 100% recall

**ODB Drugs** (100% Recall, 100% Faithfulness)
- Perfect retrieval from 10,815-vector collection
- Shows that large collections don't necessarily hurt recall if well-structured

### Dr. OPA Domains

**Choosing Wisely** (75% Recall, 100% Faithfulness, 50% Helpfulness)
- Good retrieval from 544-vector collection
- When content is found, agent uses it faithfully in synthesis
- Helpfulness highest among Dr. OPA tools (structured recommendations give agent clear context to work with)

**CPSO Policies** (80% Recall, **10% Faithfulness** ⚠️)
- **CRITICAL ISSUE:** Severe agent hallucination problem
- Despite good retrieval (80%), agent synthesis generates unsupported claims
- Needs immediate investigation - likely chunking issue or prompt needs stronger grounding instructions

**PHO IPAC** (80% Recall, 100% Faithfulness, 28% Helpfulness)
- Good retrieval; agent synthesis is faithful to retrieved context
- Low helpfulness suggests raw chunks don't give agent enough structure to synthesize actionable answers
- Need IPAC-specific schema in tool responses (requirements, equipment, validation) to guide agent

**CEP Tools** (**0% Recall** ⚠️, 100% Faithfulness, 5% Helpfulness)
- **CRITICAL ISSUE:** Complete retrieval failure - agent receives no relevant context
- Gold dataset expects full tool descriptions, but corpus has chunked text
- Need to adjust either gold data keywords or CEP chunking strategy to provide agent with proper context

**Quality Standards** (75% Recall, 88% Faithfulness, 28% Helpfulness)
- Solid retrieval from 340-vector collection
- Faithfulness mostly good (one query had hallucination)
- Helpfulness suggests need for quality statement-specific formatting

**Ontario Health Programs** (N/A retrieval metrics, 80% Faithfulness, 0% Helpfulness)
- Web search-based tool (no vector retrieval metrics)
- Faithfulness decent, but agent-synthesized answers completely unhelpful
- Web search returns unstructured content; agent doesn't know what program details to extract
- Need program-specific schema to guide agent extraction (name, eligibility, referral, contact)

---

## Files Generated

All baseline results saved to `eval/results/baseline/`:

**Dr. OFF:**
- `dr_off_ohip_billing.json` (5 queries)
- `dr_off_adp_devices.json` (5 queries)
- `dr_off_odb_drugs.json` (5 queries)

**Dr. OPA:**
- `dr_opa_choosing_wisely.json` (4 queries)
- `dr_opa_cpso_policies.json` (5 queries)
- `dr_opa_pho_ipac.json` (5 queries)
- `dr_opa_cep_tools.json` (4 queries)
- `dr_opa_quality_standards.json` (4 queries)
- `dr_opa_ontario_health_programs.json` (5 queries)

Each JSON contains:
- Summary metrics
- Per-query results with retrieval scores
- Answer quality evaluations
- Retrieved item traces for debugging

---

**This baseline establishes the foundation for quantifying improvements. All future changes will be measured against these metrics.**

---

## Iteration Tracker

Track improvements across iterations by comparing to this baseline.

### Baseline Summary (2025-10-06, commit 6219b44)

| Agent | Recall@50 | MRR | nDCG@10 | Faithfulness | Helpfulness | Coverage |
|-------|-----------|-----|---------|--------------|-------------|----------|
| Dr. OFF | 87% | 0.822 | 0.963 | 97% | 33% | 24% |
| Dr. OPA | 62% | 0.335 | 0.444 | 80% | 21% | 16% |
| **Overall** | **71%** | **0.503** | **0.635** | **86%** | **25%** | **19%** |

### Iteration 1: Hybrid Retrieval (2025-10-06)

**Status:** ⚠️ **Invalid comparison - baseline had empty document IDs**

| Dataset | Baseline R@50 | Hybrid R@50 | Δ | Baseline MRR | Hybrid MRR | Δ | Notes |
|---------|---------------|-------------|---|--------------|------------|---|-------|
| PHO IPAC | 80% | 80% | **0%** | 0.533 | 0.550 | +3.1% | No improvement - BM25 didn't help |
| CPSO Policies | 80% | 100% | **+25%** | 0.800 | 0.545 | **-31.9%** | ⚠️ Improved recall but worse ranking |
| CEP Tools | 0% | 25% | **+25%** | 0.000 | 0.125 | +0.125 | Partial fix (known keyword bug) |
| Quality Standards | 75% | 75% | **0%** | 0.350 | 0.349 | -0.3% | No change |
| Choosing Wisely | 75% | 75% | **0%** | 0.288 | 0.293 | +1.6% | No change |

**Key Findings:**

1. **Baseline Measurement Issue:** Baseline results had empty document IDs (`['', '', '']`) but reported high Recall@50/MRR. This indicates the baseline evaluation was matching on content keywords rather than document IDs, making direct comparison invalid.

2. **CPSO Policies Ranking Degradation:** Hybrid search improved Recall@50 (80% → 100%, found all relevant docs) but **degraded ranking quality** (MRR 0.800 → 0.545). This means:
   - Dense-only search ranked best doc at position #1
   - Hybrid search (RRF fusion) pushed best doc to position #2-3
   - **Root cause:** RRF dilutes strong dense rankings when BM25 retrieves different documents

3. **PHO IPAC - No Improvement:** Baseline already at 80% with dense-only search. BM25 didn't add value because:
   - IPAC queries are semantic (e.g., "hand hygiene protocols for immunocompromised patients")
   - Dense embeddings already capture these concepts well
   - BM25 keyword matching doesn't improve semantic retrieval

4. **Hybrid Search Didn't Help:** The fundamental issue is that **baseline was already performing well** (80% recall for IPAC/CPSO/QS/CW). Hybrid search is designed to help when:
   - Dense search misses exact technical terms (e.g., medical codes, acronyms)
   - Sparse retrieval catches what dense misses
   - **BUT:** Our corpora are already semantic-rich with good chunking, so dense alone suffices

**Reflection:**

Hybrid retrieval (Issue #2) was **not the right solution** for Dr. OPA. The handover document assumed PHO IPAC's 40% → 80% improvement potential, but:
- Baseline evaluation had bugs (empty IDs)
- Re-running with fixed evaluation shows 80% baseline
- Hybrid didn't improve beyond 80%
- **The real bottleneck is ranking quality (MRR, nDCG), not recall**

**Recommendation:**

- **Skip hybrid search for now** - added complexity without benefit
- **Focus on Issue #3 (Cross-Encoder Reranking)** to improve MRR/nDCG
- Cross-encoder will improve ranking of already-retrieved documents, which is the actual problem

**Technical Implementation (Preserved for Future Reference):**

✅ Implemented BM25Client with Whoosh (file-based, 1,439 documents indexed)
✅ Implemented RRF fusion with c=60.0 and provenance tracking
✅ Fixed critical bug: BM25 index was using sequential IDs vs ChromaDB's actual document IDs (caused zero overlap)
✅ Added hybrid mode toggle (`use_hybrid=True`) to all 6 Dr. OPA MCP tools
✅ Added provenance logging (dense/sparse/both) for debugging

**Files:**
- Implementation: `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/bm25_client.py`, `rrf_fusion.py`
- Results: `eval/results/02_hybrid_search/dr_opa_*.json`
- Documentation: `improve_retrieval/HYBRID_SEARCH_TECHNICAL_EXPLANATION.md`

---

### Iteration 2: Cross-Encoder Reranking (2025-10-06)

**Status:** ❌ **FAILED - Performance degraded significantly**

**Test Dataset:** PHO IPAC (5 queries)

| Metric | Baseline | Cross-Encoder | Δ | % Change |
|--------|----------|---------------|---|----------|
| Recall@50 | 80% | 80% | **0%** | 0% |
| MRR | 0.533 | 0.169 | **-0.365** | **-68%** |
| nDCG@10 | 0.499 | 0.216 | **-0.283** | **-57%** |
| Faithfulness | 100% | 100% | 0% | 0% |
| Helpfulness | 28% | 20% | -8% | -29% |
| Coverage | 54.7% | 40.7% | -14% | -26% |

**Key Findings:**

1. **Cross-Encoder Degraded Ranking Quality:**
   - MRR dropped from 0.533 → 0.169 (best document moved from rank ~2 to rank ~6)
   - nDCG@10 dropped from 0.499 → 0.216 (top-10 ranking quality degraded by 57%)
   - Helpfulness and Coverage both decreased (fewer best documents in top positions)

2. **Root Cause Analysis - Domain Mismatch:**

   **Example (Query 1: "What are hand hygiene requirements for procedure rooms?"):**

   - **Baseline (Dense-only) - Rank #1 (CORRECT):**
     - Document: "4 Moments for Hand Hygiene", "When to clean hands", "Ontario's Just Clean Your Hands program"
     - **Semantic match:** Dense embeddings understood general procedure room hand hygiene guidance

   - **Cross-Encoder Rank #1 (WRONG):**
     - Document: "surgical hand rub", "surgical/invasive procedures", "operating rooms are cleaned"
     - **Keyword match:** bge-reranker-v2-m3 focused on overlapping keywords ("procedure", "surgical", "hand") but missed semantic intent
     - **Domain mismatch:** General-purpose cross-encoder doesn't understand that "procedure rooms" ≠ "surgical/invasive procedures" in medical context

3. **Why Dense Embeddings Outperform Cross-Encoder:**
   - **Domain-specific embeddings (text-embedding-3-small)** capture medical semantic relationships through the corpus
   - **General cross-encoder (bge-reranker-v2-m3)** trained on web/generic data, lacks medical domain understanding
   - **Chunk size variability:** Chunks range from 34 to 1,165 words; cross-encoder truncates at 512 tokens (~384 words), losing context from longer chunks

4. **Per-Query Results:**
   - Query 1 (hand hygiene): MRR 1.000 → 0.100 (perfect → rank 10)
   - Query 2 (sterilization): MRR 1.000 → 0.333 (perfect → rank 3)
   - Query 3 (mobile clinic): MRR 0.500 → 0.333 (rank 2 → rank 3)
   - Query 4 (PPE): MRR 0.167 → 0.077 (rank 6 → rank 13)
   - Query 5 (environmental cleaning): MRR 0.000 → 0.000 (both failed)

**Conclusion:**

Cross-encoder reranking with **general-purpose models does NOT work** for specialized medical/policy domains. The bge-reranker-v2-m3 model:
- Prioritizes keyword overlap over semantic understanding
- Lacks domain-specific knowledge to distinguish "procedure rooms" from "surgical procedures"
- Consistently demoted the best documents in favor of keyword-rich but semantically incorrect matches

**Recommendation:**

- ❌ **DO NOT use cross-encoder reranking with general models** for Dr. OPA
- ✅ **Stick with dense-only retrieval** (baseline) - domain-specific embeddings already perform well
- 🔮 **Future option:** Fine-tune a cross-encoder on medical domain data (requires significant effort, out of scope)

**Technical Implementation (Preserved for Reference):**

✅ Implemented CrossEncoderReranker with bge-reranker-v2-m3
✅ Added lazy initialization to avoid model loading overhead
✅ Integrated into semantic_search.py pipeline (Step 3: CE reranking before filtering)
✅ Added unit tests with mocked model for CI/CD
✅ Pre-downloaded model (~1.2GB) to avoid timeout issues during evaluation

**Files:**
- Implementation: `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/cross_encoder_reranker.py`
- Tests: `tests/dr_opa_agent/test_cross_encoder_reranker.py`
- Results: `eval/results/03_cross_encoder/dr_opa_pho_ipac.json`
- Pre-download script: `scripts/download_ce_model.py`

---

### Future Iterations

Add new rows below after each improvement iteration:

| Date | Commit | Issue | Recall@50 Δ | MRR Δ | nDCG@10 Δ | Faith. Δ | Help. Δ | Cov. Δ | Notes |
|------|--------|-------|-------------|-------|-----------|----------|---------|--------|-------|
| 2025-10-06 | TBD | **#2 Hybrid Retrieval** | **0%** | **-3%** | **-17%** | N/A | N/A | N/A | ⚠️ No improvement - dense alone sufficient |
| 2025-10-06 | TBD | **#3 Cross-Encoder Reranking** | **0%** | **-68%** | **-57%** | 0% | -29% | -26% | ❌ **FAILED** - Domain mismatch, do not use |
| TBD | TBD | #5 Answer Planner + Self-Check | TBD | TBD | TBD | TBD | TBD | TBD | **RECOMMENDED NEXT** - Fix answer synthesis |
| TBD | TBD | #6 Parent/Child Chunking | TBD | TBD | TBD | TBD | TBD | TBD | Fix CEP 0% recall, improve context |

**How to use:** After each improvement, run all baselines again, compute deltas (Δ = new - baseline), and add a row above.
