# GitHub Issue Backlog

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

## 2. Hybrid Retrieval (Dense + BM25) with RRF Fusion

**Title:** Implement hybrid retriever and RRF fusion endpoint  
**Why:** Improve recall on codes/terms and semantics.

**Scope:**
- Add BM25 index (e.g., whoosh, elasticsearch, lunr, or tantivy binding).
- New MCP endpoint: `search_hybrid(query, collections[], k_dense=40, k_sparse=100, k_fuse=50)`
- Run Chroma dense + BM25 sparse in parallel.
- Implement RRF: `score = Σ 1/(c + rank_i)` (c≈60).
- Return Top-50 with feature columns: dense_rank, bm25_rank, rrf_score.

**Acceptance Criteria:**
- Unit tests show improved Recall@50 on gold set vs. dense-only.

---

## 3. Cross-Encoder Reranker (Open-source)

**Title:** Add local cross-encoder reranker (bge-reranker-v2-m3)  
**Why:** Surface the exact clause; reduce “bookmark” answers.

**Scope:**
- Load bge-reranker-v2-m3 (HF).
- New function: `rerank(query, items[]) -> items_sorted_by_ce_score`.
- Pipeline: hybrid → Top-50 → rerank → Top-k (10–12).

**Acceptance Criteria:**
- nDCG@10 and MRR improve vs. #2 alone.
- Latency within target (e.g., <400ms rerank on Top-50 CPU).

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