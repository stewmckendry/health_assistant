# Issue #5 Implementation Summary: 4-Step Answer Planner Workflow

**Date:** 2025-10-07
**Status:** ✅ IMPLEMENTED (Awaiting Evaluation)
**Implementation Approach:** Option A (Prompt-Based)

---

## What Was Implemented

### Problem Statement
- **Baseline Performance:** Coverage 19%, Helpfulness 25%, Faithfulness 86%
- **Root Cause:** Agent synthesized answers immediately without planning or verification
- **Bottleneck:** Answer synthesis, NOT retrieval (71% Recall@50 was already good)

### Solution: 4-Step Structured Workflow

Implemented a mandatory 4-step workflow in agent system prompts to guide complete fact extraction:

```
STEP 1: PLAN → Classify intent and identify required schema fields
STEP 2: RETRIEVE → Call MCP tools and extract facts into schema
STEP 3: SELF-CHECK → Verify completeness, make sub-queries for missing fields
STEP 4: SYNTHESIZE → Format complete answer only after ≥90% fields filled
```

---

## Implementation Details

### Files Modified

1. **`src/ai_agents/dr_off_agent/openai_agent.py`**
   - Updated `_get_system_instructions()` method (lines 397-559)
   - Added 5 intent-specific schemas (Billing, Drug Coverage, Device Funding, Eligibility, Documentation)
   - Removed redundant prompt sections to avoid confusion

2. **`src/ai_agents/dr_opa_agent/openai_agent.py`**
   - Updated `_get_system_instructions()` method (lines 380-558)
   - Added 6 intent-specific schemas (CPSO Policy, IPAC Guidelines, Clinical Programs, Clinical Tools, Quality Standards, Choosing Wisely)
   - Streamlined prompt for clarity

### Key Design Decisions

#### Why Option A (Prompt-Based)?
- ✅ Faster to implement and iterate (2-4 hours vs 8-12 hours for Option B)
- ✅ Leverages OpenAI Agents SDK native stateful reasoning
- ✅ Non-intrusive - no changes to existing MCP tools
- ✅ Easy to refine based on eval results

#### Why NOT Option B (Helper Tools)?
- ❌ More code to maintain
- ❌ Slower iteration cycle (code changes vs prompt tuning)
- ❌ Can implement later if Option A doesn't hit target metrics

#### Web Search Integration
Added clear guidance in Step 3 (Self-Check) for when to use `web_search` tool:
- Primary: MCP tools (structured, embedded knowledge)
- Fallback: web_search (when MCP tools return insufficient results)
- Covers: Recent policy changes, user asks for "latest" info, cross-reference official sites

---

## Schema Examples

### Dr. OFF - Billing Intent Schema
```yaml
primary_codes: List of OHIP codes with descriptions and fees
modifiers: Applicable modifiers (if any)
billing_conditions: When these codes apply
frequency_limits: Maximum billing frequency (if any)
common_errors: Common billing mistakes to avoid
citations: Source references with specific codes
```

### Dr. OPA - CPSO Policy Intent Schema
```yaml
regulatory_requirements: Mandatory requirements and expectations
compliance_obligations: What physicians must do
documentation_requirements: Required documentation standards
sanctions_consequences: Consequences of non-compliance
implementation_guidance: How to implement in practice
citations: Source references with policy numbers and sections
```

*(Full schemas defined in system prompts)*

---

## Mandatory Rules Enforced

To prevent agents from skipping the workflow, added strict rules:

```
1. ✓ ALWAYS follow all 4 steps - never skip Step 3 (Self-Check)
2. ✓ ALWAYS make at least 2 tool calls per query (initial + self-check)
3. ✓ ALWAYS fill ≥90% of required schema fields before synthesis
4. ✓ ALWAYS mark missing fields as "Not found" - never hallucinate
5. ✓ ALWAYS use specific codes/DINs in citations
6. ✗ NEVER synthesize before self-check passes
7. ✗ NEVER skip schema fields - address all required fields
8. ✗ NEVER make vague statements - be specific
```

---

## Expected Impact

### Target Metrics (From Handover Note)

| Metric | Baseline | Target | Expected Improvement |
|--------|----------|--------|---------------------|
| **Coverage** | 19% | ≥75% | **3-4x improvement** |
| **Helpfulness** | 25% | ≥70% | **2-3x improvement** |
| **Tool Calls/Query** | ~1 | ≥2 | **2x minimum** |
| **Faithfulness** | 86% | ≥90% | Maintain or improve |

### Why This Should Work

1. **Structured Planning:** Agent identifies ALL required information upfront
2. **Active Extraction:** Agent maps retrieved facts to schema fields systematically
3. **Self-Check Loop:** Agent verifies completeness and makes follow-up queries for missing data
4. **Complete Answers:** Agent only synthesizes after ≥90% schema fields filled

---

## Testing & Evaluation

### Quick Test Script

Created `test_issue5_implementation.py` to verify:
- ✓ Agents make ≥2 tool calls per query
- ✓ Self-check behavior present (multiple calls)
- ✓ Structured response format

**Run:**
```bash
python test_issue5_implementation.py
```

### Full Evaluation

**Dr. OFF Datasets (3):**
```bash
# OHIP Billing
python eval/run.py --agent dr_off --set eval/gold/dr_off/ohip_billing.jsonl --output eval/results/issue5/dr_off_ohip.json

# ODB Drugs
python eval/run.py --agent dr_off --set eval/gold/dr_off/odb_drugs.jsonl --output eval/results/issue5/dr_off_odb.json

# ADP Devices
python eval/run.py --agent dr_off --set eval/gold/dr_off/adp_devices.jsonl --output eval/results/issue5/dr_off_adp.json
```

**Dr. OPA Datasets (6):**
```bash
# CPSO Policies
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cpso_policies.jsonl --output eval/results/issue5/dr_opa_cpso.json

# Ontario Health Programs
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/ontario_health_programs.jsonl --output eval/results/issue5/dr_opa_programs.json

# PHO IPAC
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/pho_ipac.jsonl --output eval/results/issue5/dr_opa_ipac.json

# CEP Tools
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/cep_tools.jsonl --output eval/results/issue5/dr_opa_cep.json

# Quality Standards
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/quality_standards.jsonl --output eval/results/issue5/dr_opa_quality.json

# Choosing Wisely
python eval/run.py --agent dr_opa --set eval/gold/dr_opa/choosing_wisely.jsonl --output eval/results/issue5/dr_opa_choosingwisely.json
```

### Compare to Baseline

```bash
# Create comparison reports
python scripts/compare_eval_results.py \
  eval/results/baseline/dr_off_ohip.json \
  eval/results/issue5/dr_off_ohip.json
```

---

## Success Criteria

✅ **Primary Metrics (MUST ACHIEVE):**
1. Coverage ≥75% (from 19%)
2. Helpfulness ≥70% (from 25%)
3. Multi-Retrieval Pattern ≥2 calls/query (from ~1)

✅ **Secondary Metrics (NICE TO HAVE):**
1. Faithfulness ≥90% (maintain current 86%)
2. Answer Structure Compliance ≥90%
3. Schema-based formatting present

---

## Next Steps

### Immediate (Before Considering Complete)

1. ✅ **Quick Test:** Run `test_issue5_implementation.py` to verify agents work
2. ⏳ **Full Eval:** Run all 9 dataset evaluations (3 Dr. OFF + 6 Dr. OPA)
3. ⏳ **Compare Metrics:** Check if Coverage ≥75%, Helpfulness ≥70%
4. ⏳ **Qualitative Review:** Manually review 10 random answers for structure/completeness

### If Target Metrics NOT Met (<75% Coverage)

**Option B: Add Helper MCP Tools**
- `get_answer_schema(intent)` - Returns schema for an intent
- `verify_answer_completeness(intent, extracted_facts)` - Programmatic verification
- Provides stronger guardrails for self-check step

**OR: Refine System Prompt**
- Strengthen mandatory rules emphasis
- Add more examples of self-check behavior
- Adjust schema field definitions for clarity

### If Target Metrics MET (≥75% Coverage)

1. ✅ Update `improve_retrieval/backlog.md` Issue #5 status to "✅ COMPLETED"
2. ✅ Create `ISSUE_5_COMPLETION_REPORT.md` with final metrics
3. ✅ Commit changes with message: "feat: Complete Issue #5 - Answer Planner + Self-Check Loop"
4. ✅ Move to next issue in backlog

---

## Troubleshooting Guide

### Problem: Agents still make only 1 tool call

**Diagnosis:** Self-check step not being followed

**Solutions:**
1. Add more explicit examples in Step 3 showing sub-query generation
2. Make the "≥2 tool calls" rule more prominent (move to top)
3. Consider implementing Option B verification tool

### Problem: Coverage improved but Helpfulness didn't

**Diagnosis:** Schema fields filled but answer format poor

**Solutions:**
1. Refine Step 4 synthesis template with better examples
2. Add explicit formatting requirements (sections, bullet points, citations)
3. Show example of well-structured answer in prompt

### Problem: Agent skips required schema fields

**Diagnosis:** Unclear field definitions or agent doesn't understand requirement

**Solutions:**
1. Clarify field descriptions in schema definitions
2. Provide examples of what each field should contain
3. Make "address ALL fields" rule more emphatic

### Problem: Agent hallucinates missing information

**Diagnosis:** Not following "mark as 'Not found'" rule

**Solutions:**
1. Strengthen rule #4: "ALWAYS mark missing fields as 'Not found'"
2. Add example showing proper "Missing Information" section
3. Penalize hallucination in evaluation rubric

---

## Technical Notes

### Prompt Length Considerations

- **Before:** ~800 lines (verbose, redundant sections)
- **After:** ~160 lines for Dr. OFF, ~180 lines for Dr. OPA
- **Removed:** Redundant tool selection, response format, citation format sections
- **Kept:** Only essential 4-step workflow and mandatory rules

### Why This Length is Acceptable

1. OpenAI GPT-4o has large context window (128K tokens)
2. System prompts are processed once per conversation (minimal overhead)
3. Clear structure (visual separators) helps agent parse instructions
4. Alternative (Option B with helper tools) would be MORE complex

### Model Behavior Expectations

- GPT-4o excels at following structured instructions
- Multi-step reasoning is a core capability of Agents SDK
- Natural language schemas are more effective than rigid JSON formats
- Self-correction behavior aligns with model training

---

## References

- **Handover Note:** `improve_retrieval/HANDOVER_ISSUE_5.md`
- **Baseline Metrics:** `eval/results/RESULTS.md`
- **Backlog:** `improve_retrieval/backlog.md`
- **Issue #6 (Parent/Child Chunking):** `improve_retrieval/ISSUE_6_COMPLETION_SUMMARY.md`

---

## Changelog

### 2025-10-07: Initial Implementation
- ✅ Added 4-step workflow to Dr. OFF agent system prompt
- ✅ Added 4-step workflow to Dr. OPA agent system prompt
- ✅ Defined 5 intent schemas for Dr. OFF (Billing, Drug Coverage, Device Funding, Eligibility, Documentation)
- ✅ Defined 6 intent schemas for Dr. OPA (CPSO Policy, IPAC, Programs, Tools, Quality Standards, Choosing Wisely)
- ✅ Integrated web_search tool guidance in Step 3 (Self-Check)
- ✅ Removed redundant prompt sections to avoid confusion
- ✅ Created test script: `test_issue5_implementation.py`
- ✅ Created this implementation summary

### Next: Evaluation Phase
- ⏳ Run quick test to verify agents work
- ⏳ Run full evaluation (9 datasets)
- ⏳ Analyze metrics and determine if target achieved
- ⏳ Create completion report or refinement plan
