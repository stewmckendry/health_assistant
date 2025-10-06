# Evaluation Results Tracker

This file tracks all evaluation runs to compare performance across iterations.

## Directory Structure

```
eval/results/
├── baseline/                    # Initial baseline (Issue #33)
├── hybrid_retrieval/            # After BM25 + RRF (Issue #2)
├── cross_encoder_reranking/     # After reranker (Issue #3)
├── intent_router/               # After routing (Issue #4)
└── answer_planner/              # After planner (Issue #5)
```

Each directory contains:
- Individual JSON reports per dataset
- `summary.json` - Aggregated metrics across all datasets
- `comparison.json` - Delta vs previous iteration

---

## Baseline (2025-10-03)

**Git Commit:** TBD
**Issue:** #33 - Eval & Observability Baseline

### Dr. OFF Results

| Dataset | Queries | Recall@50 | MRR | nDCG@10 | Faithfulness | Helpfulness | Coverage |
|---------|---------|-----------|-----|---------|--------------|-------------|----------|
| OHIP Billing | 5 | TBD | TBD | TBD | TBD | TBD | TBD |
| ADP Devices | 5 | TBD | TBD | TBD | TBD | TBD | TBD |
| ODB Drugs | 5 | TBD | TBD | TBD | TBD | TBD | TBD |
| **Average** | **15** | **TBD** | **TBD** | **TBD** | **TBD** | **TBD** | **TBD** |

### Dr. OPA Results

| Dataset | Queries | Recall@50 | MRR | nDCG@10 | Faithfulness | Helpfulness | Coverage |
|---------|---------|-----------|-----|---------|--------------|-------------|----------|
| CPSO Policies | 5 | TBD | TBD | TBD | TBD | TBD | TBD |
| OH Programs | 5 | N/A* | N/A* | N/A* | TBD | TBD | TBD |
| PHO IPAC | 5 | TBD | TBD | TBD | TBD | TBD | TBD |
| CEP Tools | 4 | TBD | TBD | TBD | TBD | TBD | TBD |
| Quality Standards | 4 | TBD | TBD | TBD | TBD | TBD | TBD |
| Choosing Wisely | 4 | TBD | TBD | TBD | TBD | TBD | TBD |
| **Average** | **27** | **TBD** | **TBD** | **TBD** | **TBD** | **TBD** | **TBD** |

*N/A: opa_program_lookup uses web search, not vector retrieval

### Key Findings
- TBD after baseline run

### Commands Run
```bash
# Dr. OFF
python eval/run.py --agent dr_off --set eval/gold/dr_off/ohip_billing.jsonl --output eval/results/baseline/dr_off_ohip.json
python eval/run.py --agent dr_off --set eval/gold/dr_off/adp_devices.jsonl --output eval/results/baseline/dr_off_adp.json
python eval/run.py --agent dr_off --set eval/gold/dr_off/odb_drugs.jsonl --output eval/results/baseline/dr_off_odb.json

# Dr. OPA
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cpso_policies.jsonl --output eval/results/baseline/dr_opa_cpso.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/ontario_health_programs.jsonl --output eval/results/baseline/dr_opa_oh.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/pho_ipac.jsonl --output eval/results/baseline/dr_opa_pho.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl --output eval/results/baseline/dr_opa_cep.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/quality_standards.jsonl --output eval/results/baseline/dr_opa_qs.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/choosing_wisely.jsonl --output eval/results/baseline/dr_opa_cw.json
```

---

## Hybrid Retrieval (TBD)

**Git Commit:** TBD
**Issue:** #2 - Hybrid Retrieval (Dense + BM25) with RRF Fusion
**Target Improvements:**
- +10% Recall@50 for IPAC queries (technical terminology)
- +5% Recall@50 overall

### Results
TBD

### Comparison vs Baseline
```json
{
  "dr_opa_pho_ipac": {
    "recall@50": {
      "baseline": 0.64,
      "hybrid": 0.74,
      "delta": +0.10,
      "improvement": "+15.6%"
    }
  }
}
```

---

## Cross-Encoder Reranking (TBD)

**Git Commit:** TBD
**Issue:** #3 - Cross-Encoder Reranker
**Target Improvements:**
- +0.15 MRR for billing queries
- +0.10 MRR overall

### Results
TBD

---

## Evaluation Run Template

Use this template when adding new evaluation runs:

```markdown
## [Feature Name] (YYYY-MM-DD)

**Git Commit:** abc1234
**Issue:** #X - [Issue Title]
**Target Improvements:**
- Specific metric goal 1
- Specific metric goal 2

### Dr. OFF Results

| Dataset | Recall@50 Δ | MRR Δ | nDCG@10 Δ | Faithfulness Δ | Helpfulness Δ | Coverage Δ |
|---------|-------------|-------|-----------|----------------|---------------|------------|
| OHIP    | +0.05       | +0.02 | +0.03     | +0.01          | +0.02         | +0.01      |
| ADP     | +0.03       | +0.01 | +0.02     | 0.00           | +0.01         | 0.00       |
| ODB     | +0.02       | +0.03 | +0.04     | 0.00           | +0.01         | +0.02      |

### Key Findings
- What worked well
- What didn't improve as expected
- Unexpected results

### Commands Run
```bash
[Evaluation commands]
```
```

---

## Metrics Definitions

For reference, here's what each metric measures:

### Retrieval Metrics
- **Recall@50**: Did we find most of the relevant documents? (fraction in Top-50)
- **MRR**: How quickly do we find a relevant result? (1/rank of first relevant)
- **nDCG@10**: Are the most relevant results ranked highest?
- **Hit@10**: Did we find at least one relevant result in Top-10?

### Answer Quality Metrics
- **Faithfulness**: Is the answer grounded in source material? (no hallucinations)
- **Helpfulness**: Would this answer actually help the clinician?
- **Coverage**: Did we include all important facts? (% of expected elements)

---

## Best Practices

1. **Always compare to baseline**: Use delta (Δ) columns
2. **Document git commit**: Ensures reproducibility
3. **Note unexpected results**: Learn from failures too
4. **Update this file**: After every evaluation run
5. **Archive failed experiments**: Learn what doesn't work
