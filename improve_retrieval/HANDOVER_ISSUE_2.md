# Handover: Issue #2 - Hybrid Retrieval (Dense + BM25) with RRF Fusion

**Date:** 2025-10-06
**From:** Claude Code Session (Issue #1 completion)
**To:** Next Claude Code Session
**Branch:** `feat/agent-retrieval-depth-improvements`
**Status:** Ready to start Issue #2

---

## Context: What Was Just Completed (Issue #1)

### Issue #1: Evaluation & Observability Baseline ✅ COMPLETED
**Git Commit:** 6219b44 (feat/agent-retrieval-depth-improvements branch)

**What was built:**
- ✅ Evaluation framework: `eval/run.py` + metrics (Recall@50, MRR, nDCG@10, Faithfulness, Helpfulness, Coverage)
- ✅ 9 gold datasets (44 queries): 3 Dr. OFF, 6 Dr. OPA
- ✅ Baseline results captured in `eval/results/baseline/` (9 JSON files)
- ✅ Comprehensive analysis in `eval/results/RESULTS.md`

**Baseline Metrics:**
- **Overall:** 71% Recall@50, 0.503 MRR, 0.635 nDCG@10, 86% Faithfulness, 25% Helpfulness, 19% Coverage
- **Dr. OFF:** 87% Recall@50 (excellent) - SQL+vector dual-path works well
- **Dr. OPA:** 62% Recall@50 (needs improvement) - dense-only misses technical terms

**Critical Issues Discovered:**
1. **Dr. OPA Retrieval Gap:** Missing 38% of relevant documents (62% recall) due to dense-only embedding approach
2. **Technical Term Misses:** IPAC, PHO, Quality Standards queries miss domain-specific terminology (e.g., "semi-critical devices", "IPAC guidance", policy codes)
3. **CPSO Hallucination:** 10% faithfulness (P0 blocker - separate from Issue #2)
4. **CEP Tools Partial Fix (commit a7530d5):** Improved from 0% → 25% recall via relaxed keyword filters; 1/4 queries working, remaining 3 need hybrid retrieval approach in Issue #2

**Why Issue #2 is Next Priority:**
- **Target:** Dr. OPA Recall@50 from 62% → 80%+ (close the 38% gap)
- **Impact:** Better retrieval = better context for LLM agent synthesis = higher quality answers
- **Data-backed decision:** Baseline shows dense embeddings alone insufficient for technical medical terminology

---

## Your Mission: Issue #2 - Hybrid Retrieval (Dense + BM25) with RRF Fusion

### Objective
Implement hybrid retrieval combining:
1. **Dense retrieval** (existing ChromaDB with text-embedding-3-small)
2. **Sparse retrieval** (new BM25 index for exact term matching)
3. **RRF fusion** (Reciprocal Rank Fusion to merge results)

### Success Criteria
- ✅ Dr. OPA Recall@50 improves from 62% → 80%+ (measured by re-running eval baselines)
- ✅ Unit tests show improved Recall@50 on gold sets vs dense-only
- ✅ RRF fusion properly combines dense + sparse rankings
- ✅ Agent receives better context for synthesis (especially IPAC, Quality Standards, PHO queries)

### Why Hybrid Retrieval Works
**Dense (semantic) retrieval strengths:**
- Captures meaning/intent (e.g., "kidney care programs" matches "renal health services")
- Works for paraphrased queries

**Dense retrieval weaknesses (observed in baseline):**
- Misses exact technical terms: "IPAC", "semi-critical devices", "Choosing Wisely"
- Struggles with acronyms, policy codes, device names

**BM25 (sparse) retrieval strengths:**
- Exact term matching: "IPAC" → documents containing "IPAC"
- Better for technical vocabulary, codes, acronyms

**RRF fusion:**
- Best of both worlds: semantic understanding + exact matching
- Proven to outperform either method alone

---

## Step 1: Read Relevant Codebase Files

Before generating your implementation plan, read these files to understand the current architecture:

### Evaluation Framework (understand how to measure improvement)
```
eval/run.py                           # Main evaluation CLI
eval/metrics/retrieval.py             # Recall@50, MRR, nDCG@10 implementations
eval/gold/dr_opa/pho_ipac.jsonl       # Example gold dataset (IPAC queries that need term matching)
eval/results/RESULTS.md               # Baseline results and analysis
```

### Dr. OPA Retrieval (what needs to be enhanced)
```
src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py                  # MCP tool handlers (where retrieval is called)
src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/vector_client.py # Current dense-only ChromaDB client
src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py  # Semantic search orchestration
```

### Dr. OFF Retrieval (reference implementation - already hybrid SQL+vector)
```
src/ai_agents/dr_off_agent/mcp/retrieval/vector_client.py        # Vector retrieval
src/ai_agents/dr_off_agent/mcp/retrieval/sql_client.py           # SQL retrieval (reference for dual-path)
src/ai_agents/dr_off_agent/mcp/tools/schedule.py                 # Example of SQL+vector fusion
```

### Configuration & Data
```
improve_retrieval/backlog.md                                      # Issue #2 specification
improve_retrieval/eval_observability_plan.md                      # Reference for plan structure
data/processed/dr_opa/chroma/                                     # Current ChromaDB collections
```

### Key Questions to Answer While Reading:
1. How does `semantic_search.py` currently orchestrate retrieval? (line-by-line understanding)
2. Where in the MCP tool handlers is `semantic_search.search()` called? (6 tools to update)
3. What is the ChromaDB collection structure? (which collections to index with BM25)
4. How does Dr. OFF merge SQL + vector results? (reuse this fusion pattern)
5. What document schema do Dr. OPA collections use? (ensure BM25 indexes same fields)

---

## Step 2: Generate Implementation Plan

After reading the above files, create a detailed implementation plan:

**File to create:** `improve_retrieval/hybrid_retrieval_plan.md`

**Use this structure** (based on `eval_observability_plan.md`):
```markdown
# Hybrid Retrieval (Dense + BM25) - Implementation Plan

**GitHub Issue:** #2
**Status:** Planning
**Priority:** P1 - Critical for Dr. OPA recall improvement
**Estimated Effort:** [Your estimate after reading codebase]

---

## 1. Overview

### Objective
[Your summary of what you'll build]

### Why This Matters
[Impact on baseline metrics, agent synthesis quality]

### Success Criteria
[Specific, measurable goals from baseline data]

---

## 2. Current State Analysis

### Existing Architecture
[What you learned from reading the files above]

### Gaps
[What's missing to achieve hybrid retrieval]

---

## 3. Implementation Tasks

### Task 3.1: Add BM25 Index
**Effort:** [estimate]
**Owner:** [you]

**Library Selection:**
- Option A: Whoosh (pure Python, easy integration)
- Option B: Elasticsearch (powerful, but heavy)
- Option C: Tantivy (Rust-based, fastest)
- **Recommendation:** [Your choice based on requirements]

**Implementation:**
[Detailed steps]

### Task 3.2: Implement RRF Fusion
[Your plan for reciprocal rank fusion]

### Task 3.3: Update MCP Tools
[How you'll integrate hybrid search into 6 Dr. OPA tools]

### Task 3.4: Update Evaluation Framework
[Any changes needed to eval/run.py to test hybrid mode]

### Task 3.5: Measure Improvement
[How you'll prove Recall@50 improvement]

---

## 4. Technical Architecture
[Diagrams, code structure]

---

## 5. Risks & Mitigations
[What could go wrong, how to address]

---

## 6. Timeline
[Your estimated schedule]
```

---

## Step 3: Execute Implementation

Once your plan is approved (or self-approved if clear), proceed with:

1. **Create BM25 index** for Dr. OPA collections
2. **Implement RRF fusion** in `semantic_search.py`
3. **Update 6 MCP tool handlers** to use hybrid search
4. **Add unit tests** for BM25 + RRF
5. **Re-run all 9 baseline evaluations** to measure improvement
6. **Update `eval/results/RESULTS.md`** with new metrics in iteration tracker

---

## Key Files You'll Modify

Expected changes (adjust based on your plan):

```
src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/
├── vector_client.py          # MODIFY: Add BM25 index creation/loading
├── bm25_client.py            # NEW: BM25 search client (or add to vector_client.py)

src/ai_agents/dr_opa_agent/dr_opa_mcp/search/
├── semantic_search.py        # MODIFY: Add hybrid search method with RRF fusion

src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py
├── All 6 tool handlers       # MODIFY: Call hybrid search instead of dense-only

tests/dr_opa_agent/
├── test_bm25_retrieval.py    # NEW: Unit tests for BM25
├── test_rrf_fusion.py        # NEW: Unit tests for RRF

eval/results/
├── RESULTS.md                # UPDATE: Add iteration row after re-running baselines
```

---

## Important Constraints & Context

### 1. This is a RAG System
- **Users don't call these tools directly** - an LLM agent calls them
- **Tools provide context for agent synthesis**, not final answers
- **Better retrieval = better agent-generated responses**
- Keep this context window limitation in mind: agent needs best chunks ranked first

### 2. Baseline Results Location
- **Git-tracked:** `eval/results/RESULTS.md` (analysis + iteration tracker)
- **Not git-tracked:** `eval/results/baseline/*.json` (9 large JSON files with per-query details)
- **Backup copy:** `~/health_assistant/eval/results/baseline/` (same 9 JSON files)

### 3. Collections to Enhance (Dr. OPA only)
```
data/processed/dr_opa/chroma/
├── opa_choosing_wisely_corpus (544 docs) - Need BM25 for recommendation text
├── opa_cpso_corpus (366 docs)            - Need BM25 for policy codes/terms
├── opa_pho_corpus (132 docs)             - Need BM25 for "IPAC", technical terms
├── opa_cep_corpus (57 docs)              - Need BM25 for tool names (PRIORITY - current 25% recall)
├── opa_quality_standards_corpus (340 docs) - Need BM25 for standard numbers/terms
```

**Dr. OFF collections already work well** (87% recall) - don't modify them yet.

**CEP Tools Note:** Small corpus (57 docs) currently at 25% recall. Hybrid retrieval expected to have significant impact here - BM25 should catch exact tool names like "CNCP toolkit", "diabetes screening algorithm", "cardiovascular risk calculator" that embeddings miss.

### 4. Don't Break What Works
- Dr. OFF tools (schedule_get, adp_get, odb_get) already have 87% recall - **don't touch**
- ChromaDB dense retrieval is working - **keep it, add BM25 alongside**
- Evaluation framework is optimized - **keep keyword pre-filter + batch eval**

### 5. Git Workflow
- **Work on:** `feat/agent-retrieval-depth-improvements` branch (already checked out)
- **Commit often** with clear messages
- **Push to this branch** (not main)
- Follow commit message format from previous commit (6219b44) for consistency

---

## Baseline Data to Beat (Dr. OPA)

Your target improvements (from `eval/results/RESULTS.md`):

| Dataset | Current Recall@50 | Target Recall@50 | Gap to Close |
|---------|-------------------|------------------|--------------|
| Choosing Wisely | 75% | 90%+ | +15% |
| CPSO Policies | 80% | 90%+ | +10% |
| PHO IPAC | 80% | 95%+ | +15% |
| CEP Tools | 25% ⚠️ | 75%+ | +50% (needs hybrid) |
| Quality Standards | 75% | 90%+ | +15% |
| OH Programs | N/A (web search) | N/A | - |
| **Average (excl. OH)** | **67%** | **88%+** | **+21%** |

**Overall Dr. OPA target:** 62% → 80%+ Recall@50

**Note on CEP Tools:** Partially fixed in commit a7530d5 (0% → 25% via keyword filter relaxation). Remaining 3/4 queries likely need BM25 exact matching for tool names like "CNCP toolkit", "diabetes screening", "cardiovascular risk". Include CEP in Issue #2 validation.

---

## Testing Your Implementation

### Unit Tests (quick validation)
```bash
# Test BM25 indexing
pytest tests/dr_opa_agent/test_bm25_retrieval.py -v

# Test RRF fusion
pytest tests/dr_opa_agent/test_rrf_fusion.py -v

# Test hybrid search integration
pytest tests/dr_opa_agent/test_semantic_search.py::test_hybrid_search -v
```

### Integration Tests (prove improvement)
```bash
# Re-run ONE baseline to validate (fastest: Choosing Wisely)
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/choosing_wisely.jsonl --output eval/results/hybrid/dr_opa_choosing_wisely.json

# Expected: Recall@50 should be > 75% (baseline)
# If improved, run ALL 6 Dr. OPA baselines to get full picture
```

### Full Baseline Re-run (final validation)
```bash
# Dr. OPA only (6 evaluations)
for dataset in choosing_wisely cpso_policies pho_ipac cep_tools quality_standards ontario_health_programs; do
  python eval/run.py --agent dr_opa --set eval/gold/dr_opa/$dataset.jsonl --output eval/results/hybrid/dr_opa_$dataset.json
done

# Compare to baseline - compute deltas
# Update eval/results/RESULTS.md iteration tracker with improvements
```

---

## Resources & References

### Documentation
- **Baseline Results:** `eval/results/RESULTS.md`
- **Issue #2 Spec:** `improve_retrieval/backlog.md` (lines 32-46)
- **Evaluation Plan Example:** `improve_retrieval/eval_observability_plan.md`

### BM25 Libraries
- **Whoosh:** https://whoosh.readthedocs.io/ (pure Python, easy)
- **Rank-BM25:** https://github.com/dorianbrown/rank_bm25 (lightweight Python)
- **Tantivy:** https://github.com/quickwit-oss/tantivy-py (fast Rust binding)

### RRF Fusion
- **Formula:** `score(doc) = Σ 1/(c + rank_i)` where c ≈ 60
- **Reference:** "Reciprocal Rank Fusion" (Cormack et al., 2009)
- **Implementation:** Simple to code, proven effective

### Example Hybrid Search (from other systems)
- Weaviate hybrid search: https://weaviate.io/developers/weaviate/search/hybrid
- Qdrant sparse+dense: https://qdrant.tech/documentation/concepts/hybrid-queries/

---

## Quick Start Commands

```bash
# 1. Ensure you're on the right branch
git checkout feat/agent-retrieval-depth-improvements
git pull origin feat/agent-retrieval-depth-improvements

# 2. Activate virtual environment
source /Users/liammckendry/spacy_env/bin/activate

# 3. Load environment variables
source ~/thunder_playbook/.env

# 4. Read codebase files (listed in Step 1 above)
# Use Claude Code Read tool to understand current architecture

# 5. Generate implementation plan
# Create improve_retrieval/hybrid_retrieval_plan.md

# 6. Implement BM25 + RRF
# Modify files listed in "Key Files You'll Modify" section

# 7. Test and validate
# Run unit tests, then re-run baselines

# 8. Document improvements
# Update eval/results/RESULTS.md iteration tracker

# 9. Commit and push
git add [modified files]
git commit -m "feat: Implement hybrid retrieval (BM25 + RRF) for Issue #2"
git push origin feat/agent-retrieval-depth-improvements
```

---

## Questions? Check These First

**Q: Which Dr. OPA collections should get BM25 indexing?**
A: All 5 vector collections in `data/processed/dr_opa/chroma/` (choosing_wisely, cpso, pho, cep, quality_standards)

**Q: Should I modify Dr. OFF tools?**
A: No - Dr. OFF already has 87% recall. Focus on Dr. OPA (62% recall).

**Q: What if BM25 makes things slower?**
A: Run dense + BM25 in parallel (like Dr. OFF does SQL + vector). Measure latency and ensure <1s for retrieval.

**Q: How do I know if it's working?**
A: Re-run choosing_wisely baseline first. If Recall@50 > 75%, you're on the right track. Full validation = all 6 Dr. OPA baselines.

**Q: What about the CEP Tools recall issue?**
A: Partially fixed in commit a7530d5 (0% → 25% via relaxed keyword filters). Remaining 3/4 queries (diabetes screening, depression tools, cardiovascular risk) likely need BM25 exact matching for specific tool names. Include CEP in your Issue #2 validation - hybrid retrieval should help significantly.

**Q: Should I change the evaluation framework?**
A: No - keep eval/run.py as-is. It's agent-agnostic and works for both dense-only and hybrid.

---

## Success Looks Like

After completing Issue #2:

✅ **Code:**
- BM25 index created for 5 Dr. OPA collections
- RRF fusion implemented in `semantic_search.py`
- 6 Dr. OPA MCP tools updated to use hybrid search
- Unit tests passing

✅ **Metrics:**
- Dr. OPA Recall@50: 62% → 80%+ (measured on 5 datasets: Choosing Wisely, CPSO, PHO IPAC, Quality Standards, CEP Tools)
- CEP Tools specifically: 25% → 75%+ (BM25 should help with exact tool name matching)
- MRR likely improves too (better ranking from fusion)
- Faithfulness/Helpfulness/Coverage may improve due to better context

✅ **Documentation:**
- `improve_retrieval/hybrid_retrieval_plan.md` created
- `eval/results/RESULTS.md` iteration tracker updated with new metrics
- Clear commit messages explaining changes

✅ **Ready for Issue #3:**
- Hybrid retrieval baseline established
- Next step: Add cross-encoder reranking on top of hybrid results

---

## Final Notes

- **Be methodical:** Read → Plan → Implement → Test → Document
- **Measure everything:** Baseline comparison is your north star
- **Don't overthink:** Hybrid retrieval is well-understood, just needs clean implementation
- **Focus on Dr. OPA:** That's where the 38% recall gap exists
- **Context matters:** You're improving RAG for LLM agents, not end-users directly

Good luck! The baseline data clearly shows where improvement is needed. BM25 + RRF should close the technical term gap.

---

**Handover Date:** 2025-10-06
**Session Context:** This note was created at the end of Issue #1 completion to provide a clean starting point for Issue #2.
