# Handover Note: Issue #3 - Cross-Encoder Reranking

**Date:** 2025-10-06
**From:** Previous Claude Code session (Issue #2 completion)
**To:** New Claude Code session
**Status:** Ready to start
**Priority:** **P0 - IMMEDIATE** (most impactful improvement after Issue #2 findings)

---

## Executive Summary

Implement **cross-encoder reranking** using `bge-reranker-v2-m3` to improve ranking quality (MRR/nDCG@10) for Dr. OPA retrieval. This is the **most impactful next step** based on Issue #2 findings.

**Why Issue #3 is more valuable than Issue #2:**
- Issue #2 (Hybrid Retrieval) **did not improve performance** - Recall@50 stayed at 75-80%
- **Real bottleneck:** Ranking quality (MRR: 0.335, nDCG@10: 0.444), not recall
- Cross-encoder reranking will improve ranking **without** hybrid search complexity

**Expected Impact:**
- **MRR:** 0.335 → 0.70+ (best document moves from rank ~3 to top-2)
- **nDCG@10:** 0.444 → 0.80+ (better top-10 ranking)
- **Recall@50:** Unchanged (reranking doesn't change what's retrieved)
- **Answer quality:** LLM agent gets best context first → better synthesis

---

## Context from Issue #2

### Key Finding: Ranking Quality is the Bottleneck, Not Recall

**Hybrid Retrieval Results (Issue #2):**
```
| Dataset          | Baseline R@50 | Hybrid R@50 | Δ     | Baseline MRR | Hybrid MRR | Δ      |
|------------------|---------------|-------------|-------|--------------|------------|--------|
| PHO IPAC         | 80%           | 80%         | 0%    | 0.533        | 0.550      | +3.1%  |
| CPSO Policies    | 80%           | 100%        | +25%  | 0.800        | 0.545      | -31.9% ⚠️ |
| Quality Standards| 75%           | 75%         | 0%    | 0.350        | 0.349      | -0.3%  |
| Choosing Wisely  | 75%           | 75%         | 0%    | 0.288        | 0.293      | +1.6%  |
```

**Key Insights:**
1. Recall@50 already at 75-80% (good coverage)
2. Hybrid search **degraded MRR** (CPSO: 0.800 → 0.545) by diluting dense rankings
3. BM25 doesn't add value for semantic medical queries
4. **The problem:** Relevant docs are retrieved but ranked poorly (MRR: 0.335 = rank ~3)

**Conclusion:** Skip hybrid search complexity. Focus on reranking already-retrieved documents.

---

## Technical Approach

### Pipeline

```
Query
  ↓
Dense Vector Search (Chroma)
  ↓
Top-50 candidates
  ↓
Cross-Encoder Reranking (bge-reranker-v2-m3)
  ↓
Top-10 reranked results → LLM Agent
```

### Implementation Steps

1. **Add Cross-Encoder Reranker Class** (`src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/cross_encoder_reranker.py`)
   ```python
   from transformers import AutoTokenizer, AutoModelForSequenceClassification
   import torch

   class CrossEncoderReranker:
       def __init__(self, model_name="BAAI/bge-reranker-v2-m3"):
           self.tokenizer = AutoTokenizer.from_pretrained(model_name)
           self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
           self.model.eval()

       def rerank(self, query: str, documents: List[Dict], top_k: int = 10) -> List[Dict]:
           """
           Rerank documents using cross-encoder.

           Args:
               query: Search query
               documents: List of retrieved documents with 'text' field
               top_k: Number of top results to return

           Returns:
               Reranked documents with 'ce_score' field added
           """
           # Batch encode query-document pairs
           pairs = [(query, doc['text']) for doc in documents]

           with torch.no_grad():
               inputs = self.tokenizer(pairs, padding=True, truncation=True,
                                       return_tensors='pt', max_length=512)
               scores = self.model(**inputs, return_dict=True).logits.view(-1, ).float()

           # Attach scores and sort
           for doc, score in zip(documents, scores.tolist()):
               doc['ce_score'] = score

           documents.sort(key=lambda x: x['ce_score'], reverse=True)
           return documents[:top_k]
   ```

2. **Update semantic_search.py**
   - Add `use_ce_reranking=True` parameter to `search()` method
   - After retrieving top-50 from dense search, call reranker
   - Log reranking scores for debugging

3. **Update MCP Tool Handlers**
   - Enable reranking by default: `use_reranking=True`
   - Log "before/after reranking" document IDs for debugging

4. **Add Unit Tests** (`tests/dr_opa_agent/test_cross_encoder_reranker.py`)
   - Test reranker initialization
   - Test reranking logic (mock model)
   - Test integration with semantic_search.py

5. **Run Evaluations**
   - Re-run all 6 Dr. OPA baselines with reranking enabled
   - Compare MRR/nDCG@10 before/after
   - Target: MRR 0.335 → 0.70+, nDCG@10 0.444 → 0.80+

---

## Acceptance Criteria

**Metrics:**
- ✅ **MRR improves:** Dr. OPA 0.335 → 0.70+ (best doc in top-2)
- ✅ **nDCG@10 improves:** Dr. OPA 0.444 → 0.80+ (better top-10 ranking)
- ✅ **Recall@50 unchanged:** Reranking doesn't change retrieved set
- ✅ **Latency acceptable:** <500ms rerank on 50 items (CPU), <200ms (GPU)

**Code Quality:**
- ✅ Unit tests pass (test reranker logic, integration with semantic_search)
- ✅ Logging shows reranking scores and before/after document order
- ✅ Reranking toggle works (`use_reranking=True/False`)

**Documentation:**
- ✅ Update `eval/results/RESULTS.md` with Issue #3 iteration results
- ✅ Update `improve_retrieval/backlog.md` to mark Issue #3 complete
- ✅ Create handover note for Issue #5 (next recommended issue)

---

## Files to Modify

**New Files:**
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/cross_encoder_reranker.py`
- `tests/dr_opa_agent/test_cross_encoder_reranker.py`

**Files to Update:**
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py` (add reranking step)
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py` (enable reranking in tool handlers)
- `eval/results/RESULTS.md` (add Iteration 2 results)
- `improve_retrieval/backlog.md` (mark Issue #3 complete)

---

## Evaluation Instructions

### Run Evaluations

```bash
# Activate environment
source /Users/liammckendry/spacy_env/bin/activate
source .env

# Run Dr. OPA evaluations (6 datasets)
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/pho_ipac.jsonl --output eval/results/03_cross_encoder/dr_opa_pho_ipac.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cpso_policies.jsonl --output eval/results/03_cross_encoder/dr_opa_cpso_policies.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl --output eval/results/03_cross_encoder/dr_opa_cep_tools.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/quality_standards.jsonl --output eval/results/03_cross_encoder/dr_opa_quality_standards.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/choosing_wisely.jsonl --output eval/results/03_cross_encoder/dr_opa_choosing_wisely.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/ontario_health_programs.jsonl --output eval/results/03_cross_encoder/dr_opa_ontario_health_programs.json
```

### Compare Results

```python
# Compare MRR/nDCG@10 improvements
python3 <<'EOF'
import json

files = [
    "dr_opa_pho_ipac.json",
    "dr_opa_cpso_policies.json",
    "dr_opa_quality_standards.json",
    "dr_opa_choosing_wisely.json"
]

for filename in files:
    with open(f"eval/results/baseline/{filename}") as f:
        baseline = json.load(f)
    with open(f"eval/results/03_cross_encoder/{filename}") as f:
        reranked = json.load(f)

    b_mrr = baseline["summary"]["avg_mrr"]
    r_mrr = reranked["summary"]["avg_mrr"]
    b_ndcg = baseline["summary"]["avg_ndcg@10"]
    r_ndcg = reranked["summary"]["avg_ndcg@10"]

    print(f"{filename}:")
    print(f"  MRR:     {b_mrr:.3f} → {r_mrr:.3f} ({(r_mrr-b_mrr)*100:+.1f}%)")
    print(f"  nDCG@10: {b_ndcg:.3f} → {r_ndcg:.3f} ({(r_ndcg-b_ndcg)*100:+.1f}%)")
EOF
```

---

## Known Issues from Issue #2

### 1. CEP Tools - Keyword Filter Bug (Unrelated to Reranking)
- **Status:** 0% → 25% Recall@50 after partial fix (commit a7530d5)
- **Root cause:** Keyword filters too strict, rejecting valid chunks
- **Not blocking Issue #3:** Reranking will improve ranking of whatever CEP retrieves

### 2. Baseline Had Empty Document IDs
- **Status:** Fixed during Issue #2 implementation
- **Impact:** Baseline vs hybrid comparison was invalid
- **Resolution:** Hybrid results have correct document IDs now

### 3. Answer Quality Metrics (Faithfulness, Helpfulness, Coverage) Are Low
- **Status:** Expected - tools only retrieve, don't synthesize answers
- **Not blocking Issue #3:** Reranking improves retrieval quality; answer synthesis is Issue #5

---

## Dependencies

**Python Packages (add to requirements.txt):**
```
transformers>=4.35.0
torch>=2.0.0
sentence-transformers>=2.2.0  # For embeddings compatibility
```

**Model Download:**
- Model will auto-download on first use: `BAAI/bge-reranker-v2-m3` (~1.2GB)
- Ensure internet connection for first run
- Model caches to `~/.cache/huggingface/`

---

## Performance Expectations

### Latency Targets

**CPU (M1/M2 Mac):**
- 50 documents @ 512 tokens each: ~300-500ms
- Acceptable for evaluation and development

**GPU (if available):**
- 50 documents: ~100-200ms
- Significantly faster for production

### Model Specifications

**bge-reranker-v2-m3:**
- Type: Cross-encoder (BERT-based)
- Max sequence length: 512 tokens
- Parameters: ~560M
- Best for: Reranking 10-100 candidates
- NOT for: Initial retrieval from millions of documents (use bi-encoder)

---

## Success Criteria Summary

**Must Have:**
1. MRR improves from 0.335 to ≥0.70 (2x improvement)
2. nDCG@10 improves from 0.444 to ≥0.80 (80% improvement)
3. No regression in Recall@50 (stays at 75-80%)
4. Unit tests pass
5. Results documented in RESULTS.md

**Nice to Have:**
1. Latency <300ms on CPU
2. Configurable reranking toggle per tool
3. Reranking scores logged for debugging

---

## Next Steps After Issue #3

After completing Issue #3, **recommend Issue #5 (Answer Planner + Self-Check)** as next priority:

**Why Issue #5:**
- Retrieval quality will be good (Recall@50: 75-80%, MRR: 0.70+, nDCG@10: 0.80+)
- **New bottleneck:** Answer synthesis quality (Coverage: 19%, Helpfulness: 25%)
- Tools return raw chunks; LLM agent needs structured schemas per intent
- Expected impact: Coverage 19% → 85%+, Helpfulness 25% → 70%+

**Issue #5 Scope:**
- Intent-specific schemas (e.g., IPAC: requirements_mandatory, equipment, validation)
- Self-check loop: verify schema fields filled, generate sub-queries if missing
- Convert raw chunks into decision-ready answers

---

## Questions or Blockers?

**Contact:** See `improve_retrieval/backlog.md` for full backlog context

**Reference Documents:**
- Baseline results: `eval/results/RESULTS.md`
- Issue #2 findings: `eval/results/RESULTS.md` (Iteration 1 section)
- Hybrid search implementation: `improve_retrieval/HYBRID_SEARCH_TECHNICAL_EXPLANATION.md`
- Gold datasets: `eval/gold/dr_opa/*.jsonl`

---

**Good luck with Issue #3! This will be the most impactful improvement yet.** 🚀
