# Agent Evaluation Framework - Setup Complete ✅

**Date:** 2025-10-08
**Status:** Ready for Evaluation

---

## What Was Created

### 1. **Synthetic Evaluation Datasets** (80 test cases)

Three comprehensive datasets created in Langfuse:

- **`dr_off_agent_eval`**: 27 test cases
  - OHIP billing, ODB drug coverage, ADP device funding
  - 10 simple, 12 medium, 5 complex
  - 12 edge cases (tool failures, conflicts, invalid input)

- **`dr_opa_agent_eval`**: 35 test cases
  - CPSO policies, IPAC guidelines, CEP tools, Quality Standards, Choosing Wisely, Ontario Health Programs
  - 10 simple, 19 medium, 6 complex
  - 13 edge cases (policy conflicts, freshness, contradictions)

- **`chief_orchestrator_eval`**: 18 test cases
  - Integrated queries requiring multi-agent coordination
  - 4 medium, 14 complex
  - 18 edge cases (ALL cases test orchestration challenges)

### 2. **Scripts Created**

#### `scripts/create_agent_eval_dataset.py`
- Defines all test cases with metadata
- Creates Langfuse datasets
- Supports per-agent or full dataset creation
- **Usage:** `python scripts/create_agent_eval_dataset.py --agent all --overwrite`

#### `scripts/generate_expected_results.py`
- Generates expected results via Exa web search
- Searches Ontario healthcare sources
- Saves to `eval/expected_results/*.json`
- **Usage:** `python scripts/generate_expected_results.py --agent all`

#### `scripts/run_agent_evaluation.py`
- Runs evaluation on Langfuse datasets
- Creates traces for each test case
- Logs results to Langfuse
- **Usage:** `python scripts/run_agent_evaluation.py --agent all --limit 10`

### 3. **Documentation**

- **`eval/DATASET_COVERAGE_SUMMARY.md`**: Detailed coverage analysis
- **`eval/SETUP_COMPLETE.md`**: This file - setup guide
- **`eval/expected_results/README.md`**: Expected results documentation (from Task agent)

---

## Coverage Summary

| Agent | Total | Simple | Medium | Complex | Edge Cases |
|-------|-------|--------|--------|---------|------------|
| Dr. OFF | 27 | 10 | 12 | 5 | 12 (44%) |
| Dr. OPA | 35 | 10 | 19 | 6 | 13 (37%) |
| Chief | 18 | 0 | 4 | 14 | 18 (100%) |
| **TOTAL** | **80** | **20** | **35** | **25** | **43 (54%)** |

### Tool Coverage (Dr. OFF)
- `schedule_get` (OHIP): 15 cases
- `odb_get` (Drugs): 9 cases
- `adp_get` (Devices): 5 cases
- Multi-tool: 3 cases

### Tool Coverage (Dr. OPA)
- `opa_policy_check` (CPSO): 13 cases
- `opa_ipac_guidance` (PHO): 5 cases
- `opa_clinical_tools` (CEP): 6 cases
- `opa_quality_standards`: 4 cases
- `opa_choosing_wisely`: 4 cases
- `opa_program_lookup`: 3 cases
- `opa_search_sections`: 3 cases
- Multi-tool: 3 cases

### Orchestration Coverage (Chief)
- Integrated queries: 5 cases
- Ambiguous intent: 2 cases
- Sequential reasoning: 1 case
- Edge cases: 18 cases

---

## Edge Case Coverage

### Types of Edge Cases Included

1. **Tool Failures** (6 cases)
   - Invalid codes/drugs/devices
   - Nonsensical queries
   - Queries outside system scope

2. **Malformed Input** (6 cases)
   - Incomplete queries
   - Keyword stuffing
   - Ambiguous phrasing

3. **Conflicting Information** (7 cases)
   - Multiple codes for same service
   - Contradictory guidance from different sources
   - Inter-agent conflicts
   - Policy hierarchy questions

4. **Scope Issues** (6 cases)
   - Overly broad queries
   - Multiple simultaneous requests
   - Volume overload

5. **Complex Eligibility** (5 cases)
   - Dual coverage coordination
   - Patient preference conflicts
   - Rare/experimental scenarios

6. **Meta Queries** (3 cases)
   - System capability questions
   - Routing uncertainty
   - Verification requests

7. **Freshness** (2 cases)
   - Recent policy updates
   - Version conflicts

---

## Next Steps

### 1. Generate Expected Results (Optional - Task agent already working on this)

The Task agent is currently generating expected results in the background. Results will be saved to:
- `eval/expected_results/dr_off_expected_results.json`
- `eval/expected_results/dr_opa_expected_results.json`
- `eval/expected_results/chief_expected_results.json`

If you want to generate additional results manually:
```bash
python scripts/generate_expected_results.py --agent all --batch-size 5
```

### 2. Run Evaluation

Run evaluation on all three agents:

```bash
# Activate virtual environment
source /Users/liammckendry/spacy_env/bin/activate

# Run full evaluation (all 80 test cases)
python scripts/run_agent_evaluation.py --agent all

# Or test with a subset first
python scripts/run_agent_evaluation.py --agent dr_off --limit 10
python scripts/run_agent_evaluation.py --agent dr_opa --limit 10
python scripts/run_agent_evaluation.py --agent chief --limit 5
```

### 3. View Results in Langfuse

1. Go to: https://cloud.langfuse.com
2. Navigate to **Datasets** section
3. Select dataset:
   - `dr_off_agent_eval`
   - `dr_opa_agent_eval`
   - `chief_orchestrator_eval`
4. View traces and evaluation runs
5. Compare agent performance across test cases

### 4. Analyze Results

Key metrics to track:
- **Accuracy**: % of correct responses per difficulty level
- **Tool Usage**: % of cases where correct tools were invoked
- **Edge Case Handling**: % of graceful failures
- **Citation Quality**: % of responses with proper source attribution
- **Latency**: Average response time per agent

Filter by tags in Langfuse:
- `edge_case`
- `multi_tool`
- `conflict*`
- `malformed_input`
- `tool_failure`

---

## Evaluation Success Criteria

### Overall Targets
- **Simple cases**: >90% accuracy
- **Medium cases**: >80% accuracy
- **Complex cases**: >70% accuracy
- **Tool invocation**: >95% correct
- **Edge case handling**: >80% graceful failures

### Specific Edge Case Criteria
- **No Results**: Must acknowledge + suggest alternatives (100%)
- **Malformed Input**: Must request clarification (100%)
- **Conflicts**: Must acknowledge + explain hierarchy (90%)
- **Scope Issues**: Must manage scope or request narrowing (90%)
- **Meta Queries**: Must provide accurate system description (100%)

---

## Dataset Locations

### Langfuse (Primary)
- **URL**: https://cloud.langfuse.com
- **Datasets**: `dr_off_agent_eval`, `dr_opa_agent_eval`, `chief_orchestrator_eval`

### Local Files
- **Test case definitions**: `scripts/create_agent_eval_dataset.py`
- **Expected results**: `eval/expected_results/*.json`
- **Documentation**: `eval/DATASET_COVERAGE_SUMMARY.md`
- **Evaluation results**: Will be in Langfuse traces + `evaluation_results/` (if exported)

---

## Troubleshooting

### Issue: "Dataset already exists"
**Solution:** Use `--overwrite` flag
```bash
python scripts/create_agent_eval_dataset.py --agent all --overwrite
```

### Issue: "Langfuse authentication failed"
**Solution:** Check environment variables
```bash
echo $LANGFUSE_PUBLIC_KEY
echo $LANGFUSE_SECRET_KEY
```

### Issue: "Exa API key not found"
**Solution:** Exa key is in `~/.claude.json` (Task agent has access)

### Issue: "Agent not found"
**Solution:** Make sure you're in the correct environment
```bash
source /Users/liammckendry/spacy_env/bin/activate
cd /Users/liammckendry/health_assistant_retrieval_improvements
```

---

## File Structure

```
health_assistant_retrieval_improvements/
├── scripts/
│   ├── create_agent_eval_dataset.py    # Dataset creation
│   ├── generate_expected_results.py     # Expected results generation
│   └── run_agent_evaluation.py          # Evaluation runner
├── eval/
│   ├── DATASET_COVERAGE_SUMMARY.md      # Coverage analysis
│   ├── SETUP_COMPLETE.md                # This file
│   ├── expected_results/
│   │   ├── dr_off_expected_results.json
│   │   ├── dr_opa_expected_results.json
│   │   └── chief_expected_results.json
│   └── gold/                            # Existing manual test cases
│       ├── dr_off/
│       └── dr_opa/
├── src/
│   ├── ai_agents/
│   │   ├── dr_off_agent/
│   │   ├── dr_opa_agent/
│   │   └── diagnostic_orchestrator/     # Chief
│   └── evaluation/                      # Existing eval framework
└── logs/                                # Agent logs
```

---

## Summary

✅ **80 synthetic test cases created** across 3 agents
✅ **54% edge case coverage** (43/80 cases)
✅ **All tools covered** with multiple test cases each
✅ **Realistic scenarios** from simple to complex
✅ **Datasets live in Langfuse** ready for evaluation
✅ **Scripts ready** for expected results and evaluation
✅ **Documentation complete** with coverage analysis

**Ready to run evaluation!** 🚀

The evaluation framework is now complete and ready for:
1. Running comprehensive agent evaluations
2. Comparing agent performance across difficulty levels
3. Identifying edge case failure modes
4. Tracking improvements over time
5. Validating tool usage and citation quality

Use the evaluation results to:
- Identify prompt engineering improvements
- Optimize tool selection logic
- Enhance error handling
- Improve multi-agent coordination (Chief)
- Refine retrieval strategies
