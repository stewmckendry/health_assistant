# Evaluation Framework for Dr. OFF and Dr. OPA Agents

This directory contains the evaluation infrastructure for measuring retrieval and answer quality across all knowledge sources.

## Directory Structure

```
eval/
├── gold/                  # Gold standard datasets (SME-annotated)
│   ├── dr_off/           # Dr. OFF (Ontario Funding Finder)
│   │   ├── ohip_billing.jsonl
│   │   ├── adp_devices.jsonl
│   │   └── odb_drugs.jsonl
│   └── dr_opa/           # Dr. OPA (Ontario Practice Advice)
│       ├── cpso_policies.jsonl
│       ├── ontario_health_programs.jsonl
│       ├── pho_ipac.jsonl
│       ├── cep_tools.jsonl
│       ├── quality_standards.jsonl
│       └── choosing_wisely.jsonl
│
├── metrics/              # Metric computation modules
│   ├── retrieval.py     # Recall@50, MRR, nDCG@10, Hit@10
│   └── answer_quality.py # LLM-judge (Faithfulness, Helpfulness, Coverage)
│
├── results/              # Evaluation outputs
│   └── BASELINE_REPORT.md
│
├── run.py               # Main evaluation CLI
└── README.md           # This file
```

## Quick Start

### Run Evaluation

```bash
# Dr. OFF evaluations
python eval/run.py --agent dr_off --set eval/gold/dr_off/ohip_billing.jsonl

# Dr. OPA evaluations
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cpso_policies.jsonl

# Custom output path
python eval/run.py --agent dr_off --set eval/gold/dr_off/ohip_billing.jsonl --output results/custom.json
```

### Run All Baseline Evaluations

```bash
# Dr. OFF (3 datasets)
python eval/run.py --agent dr_off --set eval/gold/dr_off/ohip_billing.jsonl --output results/baseline_dr_off_ohip.json
python eval/run.py --agent dr_off --set eval/gold/dr_off/adp_devices.jsonl --output results/baseline_dr_off_adp.json
python eval/run.py --agent dr_off --set eval/gold/dr_off/odb_drugs.jsonl --output results/baseline_dr_off_odb.json

# Dr. OPA (6 datasets)
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cpso_policies.jsonl --output results/baseline_dr_opa_cpso.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/ontario_health_programs.jsonl --output results/baseline_dr_opa_oh_programs.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/pho_ipac.jsonl --output results/baseline_dr_opa_pho.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl --output results/baseline_dr_opa_cep.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/quality_standards.jsonl --output results/baseline_dr_opa_qs.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/choosing_wisely.jsonl --output results/baseline_dr_opa_cw.json
```

## Gold Dataset Format

Each gold dataset is a JSONL file where each line is a JSON object:

```json
{
  "id": "billing_001",
  "query": "Can I bill C124 as MRP for a patient discharged after 3 days?",
  "agent": "dr_off",
  "domain": "billing",
  "intent": "ohip_billing",
  "expected_sources": [
    {
      "collection": "ohip_documents",
      "doc_id": "schedule_of_benefits_section_c",
      "relevant_chunks": ["chunk_c124_definition", "chunk_c124_prerequisites"],
      "reason": "Contains C124 billing requirements and MRP definitions"
    }
  ],
  "expected_answer_elements": [
    "C124 is billable as MRP if patient admitted >48 hours",
    "3 days = 72 hours meets requirement",
    "Cite Schedule of Benefits Section C"
  ],
  "expert_answer": "Yes, C124 can be billed as MRP for a patient discharged after 3 days...",
  "difficulty": "medium",
  "tags": ["discharge", "mrp", "length_of_stay"]
}
```

## Metrics

### Retrieval Metrics
- **Recall@50**: Fraction of relevant chunks in Top-50 results
- **MRR**: Mean Reciprocal Rank (1/rank of first relevant item)
- **nDCG@10**: Normalized Discounted Cumulative Gain at Top-10
- **Hit@10**: Binary indicator if any relevant item in Top-10

### Answer Quality Metrics (LLM-Judge)
- **Faithfulness**: Does answer only contain claims supported by context?
- **Helpfulness**: Is the answer useful for the clinician's question?
- **Coverage**: What percentage of required facts are included?

## Coverage

**Dr. OFF (3 datasets, 15-21 queries):**
- OHIP Billing → `schedule.get` tool
- ADP Devices → `adp.get` tool
- ODB Drugs → `odb.get` tool

**Dr. OPA (6 datasets, 27-40 queries):**
- CPSO Policies → `opa_policy_check` tool
- Ontario Health Programs → `opa_program_lookup` tool (Claude + Web Search)
- PHO IPAC → `opa_ipac_guidance` tool
- CEP Tools → `opa_clinical_tools` tool
- Quality Standards → `opa_quality_standards` tool
- Choosing Wisely → `opa_choosing_wisely` tool

**Total: 42-61 queries across 9 datasets**

## Related Documentation

- **Implementation Plan**: `improve_retrieval/eval_observability_plan.md`
- **GitHub Issue**: https://github.com/stewmckendry/health_assistant/issues/33
- **Agent Docs**: `docs/agents/dr_off_agent/`, `docs/agents/dr_opa_agent/`
