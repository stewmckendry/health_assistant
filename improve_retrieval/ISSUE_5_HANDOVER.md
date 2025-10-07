# Issue #5 Handover: Next Session Instructions

**Date:** 2025-10-07
**Status:** ✅ Implementation Complete - Ready for Evaluation
**Expected Session Time:** 2-3 hours for full evaluation

---

## What Was Completed This Session

✅ **Implemented 4-Step Answer Planner + Self-Check Loop (Option A: Prompt-Based)**

1. Updated Dr. OFF agent system prompt (`src/ai_agents/dr_off_agent/openai_agent.py`)
   - Added structured 4-step workflow with 5 intent schemas
   - Integrated web_search fallback guidance
   - Streamlined prompt by removing redundant sections

2. Updated Dr. OPA agent system prompt (`src/ai_agents/dr_opa_agent/openai_agent.py`)
   - Added structured 4-step workflow with 6 intent schemas
   - Integrated web_search fallback guidance
   - Streamlined prompt for clarity

3. Created test script (`test_issue5_implementation.py`)
4. Created documentation (`improve_retrieval/ISSUE_5_IMPLEMENTATION_SUMMARY.md`)
5. Updated backlog (`improve_retrieval/backlog.md`)

---

## What to Do Next Session

### Step 1: Quick Verification (5 minutes)

Run the quick test to verify agents work with new prompts:

```bash
cd /Users/liammckendry/health_assistant_retrieval_improvements
source ~/spacy_env/bin/activate
python test_issue5_implementation.py
```

**Expected Output:**
- Dr. OFF: ≥2 tool calls per query ✓
- Dr. OPA: ≥2 tool calls per query ✓

**If Test Fails:**
- Check agent logs for errors
- Verify OpenAI API key is loaded
- Check MCP servers are starting correctly

---

### Step 2: Full Evaluation (1-2 hours)

Run evaluations on all 9 datasets to measure improvement:

#### Dr. OFF (3 datasets):

```bash
# OHIP Billing
python eval/run.py --agent dr_off --set eval/gold/dr_off/ohip_billing.jsonl \
  --output eval/results/issue5/dr_off_ohip.json

# ODB Drugs
python eval/run.py --agent dr_off --set eval/gold/dr_off/odb_drugs.jsonl \
  --output eval/results/issue5/dr_off_odb.json

# ADP Devices
python eval/run.py --agent dr_off --set eval/gold/dr_off/adp_devices.jsonl \
  --output eval/results/issue5/dr_off_adp.json
```

#### Dr. OPA (6 datasets):

```bash
# CPSO Policies
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cpso_policies.jsonl \
  --output eval/results/issue5/dr_opa_cpso.json

# Ontario Health Programs
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/ontario_health_programs.jsonl \
  --output eval/results/issue5/dr_opa_programs.json

# PHO IPAC
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/pho_ipac.jsonl \
  --output eval/results/issue5/dr_opa_ipac.json

# CEP Tools
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl \
  --output eval/results/issue5/dr_opa_cep.json

# Quality Standards
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/quality_standards.jsonl \
  --output eval/results/issue5/dr_opa_quality.json

# Choosing Wisely
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/choosing_wisely.jsonl \
  --output eval/results/issue5/dr_opa_choosingwisely.json
```

**Note:** Each eval takes ~5-15 minutes depending on dataset size.

---

### Step 3: Analyze Results (30 minutes)

#### Compare to Baseline:

```bash
# Create comparison scripts if needed
python scripts/compare_eval_results.py \
  eval/results/baseline/dr_off_ohip.json \
  eval/results/issue5/dr_off_ohip.json
```

#### Key Metrics to Check:

| Metric | Baseline | Target | Pass/Fail |
|--------|----------|--------|-----------|
| **Coverage** | 19% | ≥75% | ? |
| **Helpfulness** | 25% | ≥70% | ? |
| **Tool Calls/Query** | ~1 | ≥2 | ? |
| **Faithfulness** | 86% | ≥90% (maintain) | ? |

#### Manual Quality Review:

Randomly select 10 answers and check:
- [ ] Does answer follow schema structure?
- [ ] Are all schema fields addressed (filled or marked "not found")?
- [ ] Are citations complete with section_path?
- [ ] Would a physician find this actionable?

---

### Step 4: Decision Point

#### ✅ If Metrics Met (Coverage ≥75%, Helpfulness ≥70%):

1. **Create Completion Report:**
   ```bash
   # Copy template
   cp improve_retrieval/ISSUE_5_IMPLEMENTATION_SUMMARY.md \
      improve_retrieval/ISSUE_5_COMPLETION_REPORT.md

   # Add final metrics, qualitative review, and recommendations
   ```

2. **Update Backlog:**
   - Mark Issue #5 as "✅ COMPLETED WITH RESULTS" in `improve_retrieval/backlog.md`
   - Add final metrics to the summary section

3. **Commit Changes:**
   ```bash
   git add src/ai_agents/*/openai_agent.py \
           test_issue5_implementation.py \
           improve_retrieval/*.md \
           eval/results/issue5/

   git commit -m "feat: Complete Issue #5 - Answer Planner + Self-Check Loop

   - Implemented 4-step workflow in agent system prompts
   - Added 11 intent-specific schemas (5 Dr. OFF + 6 Dr. OPA)
   - Integrated web_search fallback guidance
   - Streamlined prompts to avoid confusion

   Results:
   - Coverage: 19% → X% (Xx improvement)
   - Helpfulness: 25% → X% (Xx improvement)
   - Tool calls: ~1 → X.X avg (multi-retrieval pattern)

   Option A (prompt-based) achieved target metrics without
   requiring Option B (helper tools)."
   ```

4. **Move to Next Issue:**
   - Review `improve_retrieval/backlog.md` for next priority
   - Likely Issue #4 (Intent Router) or Issue #7 (Synonym Injection)

---

#### ❌ If Metrics NOT Met (Coverage <75% or Helpfulness <70%):

**Diagnosis & Refinement Options:**

1. **If Coverage improved but <75%:**
   - **Likely cause:** Agent isn't making enough self-check sub-queries
   - **Solution:** Strengthen Step 3 rules in prompt:
     - Make "≥2 tool calls" rule more prominent (move to top)
     - Add explicit examples of self-check behavior
     - Consider adding penalty for incomplete answers

2. **If Helpfulness improved but <70%:**
   - **Likely cause:** Schema fields filled but answer format poor
   - **Solution:** Refine Step 4 synthesis template:
     - Add explicit formatting examples
     - Show example of well-structured answer in prompt
     - Clarify section heading requirements

3. **If Tool Calls still ~1:**
   - **Likely cause:** Agent skipping Self-Check step entirely
   - **Solution:** Consider implementing Option B:
     - Add `verify_answer_completeness()` MCP tool
     - Make verification programmatic (not prompt-based)
     - Force agent to call verification before synthesis

4. **If Multiple Issues:**
   - **Solution:** Implement Option B (Helper Tools):
     - Create `src/ai_agents/dr_off_agent/mcp/tools/answer_planner.py`
     - Create `src/ai_agents/dr_opa_agent/dr_opa_mcp/tools/answer_planner.py`
     - Add `get_answer_schema()` and `verify_answer_completeness()` tools
     - Update system prompts to reference these tools

**Refinement Iteration:**
- Make prompt/tool changes
- Re-run evaluation on 2-3 datasets (not all 9)
- If improved, run full eval again
- Repeat until target metrics met or 3 iterations attempted

---

## Troubleshooting Common Issues

### Issue: Agents crash on startup

**Symptoms:**
- MCP server fails to initialize
- "Connection timeout" errors

**Solutions:**
1. Check MCP server logs: `logs/dr_off_agent/` or `logs/dr_opa_agent/`
2. Verify ChromaDB paths exist: `data/processed/dr_off/chroma/` and `data/processed/dr_opa/chroma/`
3. Check environment variables loaded: `echo $OPENAI_API_KEY`

### Issue: Evaluation hangs or times out

**Symptoms:**
- Eval script runs for >30 minutes on small dataset
- "Timeout waiting for tool response" errors

**Solutions:**
1. Check if MCP server is responding: Look for tool call logs
2. Reduce dataset size temporarily: Test with first 3 queries only
3. Increase timeout: Edit `mcp_server` timeout parameter in agent files

### Issue: LLM-judge evaluation fails

**Symptoms:**
- "Failed to evaluate answer quality" errors
- Missing Coverage/Helpfulness scores in results

**Solutions:**
1. Check OpenAI API key is valid and has credits
2. Verify eval/metrics/answer_quality.py is using correct model (gpt-4o-mini)
3. Check for rate limiting: Add delays between queries

---

## Key Files Reference

### Modified Files:
- `src/ai_agents/dr_off_agent/openai_agent.py` (lines 397-559)
- `src/ai_agents/dr_opa_agent/openai_agent.py` (lines 380-558)
- `improve_retrieval/backlog.md` (Issue #5 section)

### Created Files:
- `test_issue5_implementation.py`
- `improve_retrieval/ISSUE_5_IMPLEMENTATION_SUMMARY.md`
- `ISSUE_5_HANDOVER.md` (this file)

### Expected Output Files:
- `eval/results/issue5/dr_off_*.json` (3 files)
- `eval/results/issue5/dr_opa_*.json` (6 files)
- `improve_retrieval/ISSUE_5_COMPLETION_REPORT.md` (after success)

### Backup Locations:
- Original agent prompts backed up in git history
- No database changes made (Issue #5 is prompt-only)

---

## Success Criteria Checklist

Use this checklist to determine if Issue #5 is complete:

- [ ] **Quick test passes:** Both agents make ≥2 tool calls
- [ ] **Coverage ≥75%:** Agent fills ≥75% of required schema fields
- [ ] **Helpfulness ≥70%:** Answers address user's specific question
- [ ] **Tool calls ≥2:** Multi-retrieval pattern present in all queries
- [ ] **Faithfulness ≥90%:** Citation accuracy maintained or improved
- [ ] **Schema compliance ≥90%:** Answers follow structured format
- [ ] **Manual review:** 10 random answers are complete and actionable
- [ ] **Documentation:** Results captured in completion report
- [ ] **Backlog updated:** Issue #5 marked as completed with metrics
- [ ] **Committed:** All changes committed to git with descriptive message

If all checkboxes pass → **Issue #5 is COMPLETE** ✅

If any fail → **Iterate on refinement** and re-evaluate

---

## Questions for Next Session

If you need clarification during evaluation:

1. **Q: Should I run evaluations sequentially or in parallel?**
   - A: Sequential is safer (avoids OpenAI rate limits). Parallel possible if you have high rate limits.

2. **Q: What if one dataset takes >30 minutes?**
   - A: Check logs for hanging tool calls. Consider reducing dataset size or increasing timeout.

3. **Q: How do I know if Coverage/Helpfulness is "good enough"?**
   - A: Target is ≥75% Coverage, ≥70% Helpfulness. Anything above is excellent.

4. **Q: Should I implement Option B if metrics are at 70% Coverage?**
   - A: No - 70% is close enough to target. Only implement Option B if <65% or after 3 refinement attempts.

5. **Q: What if Faithfulness dropped below 90%?**
   - A: This is a critical issue. Review if agent is hallucinating due to pressure to "fill fields." May need to relax completeness requirement.

---

## Estimated Timeline

- **Quick Test:** 5 minutes
- **Full Evaluation:** 1-2 hours (9 datasets × 5-15 min each)
- **Analysis:** 30 minutes
- **Refinement (if needed):** 1-2 hours
- **Documentation:** 30 minutes

**Total:** 2-5 hours depending on whether refinement is needed

---

## Contact/References

- **Handover Note:** `improve_retrieval/HANDOVER_ISSUE_5.md` (original requirements)
- **Implementation Summary:** `improve_retrieval/ISSUE_5_IMPLEMENTATION_SUMMARY.md`
- **Baseline Results:** `eval/results/RESULTS.md`
- **Backlog:** `improve_retrieval/backlog.md`

---

**Good luck with the evaluation! The hard part (implementation) is done - now we validate it works! 🚀**
