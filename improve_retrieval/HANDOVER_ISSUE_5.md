# Handover Note: Issue #5 - Answer Planner + Self-Check Loop

**Date:** 2025-10-07
**From:** Previous Claude Code session (Issue #6 completion)
**To:** New Claude Code session
**Status:** Ready to start
**Priority:** P0 - HIGHEST ROI (current bottleneck is answer synthesis, not retrieval)

---

## Executive Summary

**Current State:**
- ✅ Retrieval is working well: 71% Recall@50, 0.503 MRR
- ✅ Issue #6 completed: Parent/child chunking + metadata enrichment (19,223 → 4,728 chunks)
- ❌ **Answer synthesis is the bottleneck:**
  - Coverage: 19% (agent misses 81% of required facts)
  - Helpfulness: 25% (answers don't address user's specific question)
  - Faithfulness: 86% (citations are accurate, but incomplete)

**Why This Matters:**
- Tools return relevant chunks, but agent doesn't know what information is important
- Agent synthesizes immediately without planning or verification
- No structured extraction → random fact selection → incomplete answers

**Solution:** Implement 4-step agent workflow (Plan → Retrieve → Self-Check → Synthesize) with intent-specific schemas to guide complete fact extraction.

**Expected Impact:** Coverage 19% → 75%+, Helpfulness 25% → 70%+ (3-4x improvement)

---

## Context: Architecture & Implementation Location

### Our AI Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  User Query: "How do I bill for diabetic retinopathy?"      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  OpenAI Agents SDK Agent (Dr. OFF / Dr. OPA)                │
│  - Receives query                                            │
│  - Calls MCP tools natively                                  │
│  - Synthesizes answer from tool responses                    │
│  ─────────────────────────────────────────────────────────  │
│  IMPLEMENTATION LOCATION: This is where we add the 4-step    │
│  workflow via system prompt + optional helper tools          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  MCP Tools (Model Context Protocol)                          │
│  - search_ohip_schedule(query, top_k)                        │
│  - search_cpso_policies(query, top_k)                        │
│  - search_cep_tools(query, top_k)                            │
│  ─────────────────────────────────────────────────────────  │
│  IMPLEMENTATION LOCATION: NO CHANGES NEEDED                  │
│  Tools continue to return List[RetrievedItem] with:          │
│  - text, section_path, relevance_score, metadata             │
│  - Parent context enrichment already implemented             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Vector Database (ChromaDB)                                  │
│  - Parent/child chunks with section_path metadata            │
│  - 1536-dim embeddings (text-embedding-3-small)              │
│  ─────────────────────────────────────────────────────────  │
│  IMPLEMENTATION LOCATION: NO CHANGES NEEDED                  │
│  Issue #6 completed all restructuring                        │
└─────────────────────────────────────────────────────────────┘
```

**Key Insight:** Issue #5 is implemented at the **Agent level** (OpenAI Agents SDK), NOT in the MCP tools. The tools already return good chunks - we need the agent to use them better.

---

## Implementation Strategy

### Option A: Agent System Prompt (Primary Implementation - START HERE)

**File:** `src/ai_agents/dr_off_agent/agent.py` (and `dr_opa_agent/agent.py`)

**Approach:** Add 4-step workflow to system prompt - agent naturally follows the structured process.

**Advantages:**
- ✅ Non-intrusive: No changes to existing MCP tools
- ✅ Leverages OpenAI Agents SDK native capabilities (stateful, multi-step reasoning)
- ✅ Easy to iterate: Prompt engineering is faster than code changes
- ✅ Works immediately without new tool development

**System Prompt Template:**

```python
SYSTEM_PROMPT = """
You are Dr. OFF, an expert medical billing assistant for Ontario physicians.

IMPORTANT: Use this 4-step workflow for every query:

═══════════════════════════════════════════════════════════════
STEP 1: PLAN - Identify Intent and Required Fields
═══════════════════════════════════════════════════════════════

First, classify the query intent:
- Billing: User asks about OHIP billing codes, fees, or how to bill
- Coverage: User asks about eligibility, coverage criteria, or restrictions
- Eligibility: User asks about which patients qualify
- Documentation: User asks about required documentation or forms

Then, load the required fields schema for this intent:

**Billing Intent Schema:**
- primary_codes: List of OHIP codes with descriptions and fees
- modifiers: List of applicable modifiers (if any)
- billing_conditions: When these codes apply
- frequency_limits: Maximum billing frequency (if any)
- common_errors: Common billing mistakes to avoid (if available)
- citations: Source references with section_path

**Coverage Intent Schema:**
- eligibility_criteria: Who is covered
- excluded_populations: Who is NOT covered
- documentation_requirements: Required documentation
- approval_process: Pre-authorization requirements (if any)
- citations: Source references with section_path

**Eligibility Intent Schema:**
- patient_criteria: Age, diagnosis, or other requirements
- exclusion_criteria: When NOT eligible
- duration_limits: Time-based restrictions
- citations: Source references with section_path

**Documentation Intent Schema:**
- required_forms: List of forms needed
- required_fields: What must be documented
- submission_process: How to submit
- citations: Source references with section_path

═══════════════════════════════════════════════════════════════
STEP 2: RETRIEVE - Call Tools and Extract Facts
═══════════════════════════════════════════════════════════════

Call the appropriate MCP tools:
- search_ohip_schedule(query="...", top_k=5)
- search_adp(query="...", top_k=5)
- search_odb(query="...", top_k=5)

As you review the tool responses, extract facts into the schema fields:
- Read each retrieved chunk carefully
- Map facts to schema fields (e.g., "E083A - $245.00" → primary_codes)
- Note which fields are filled and which are empty

═══════════════════════════════════════════════════════════════
STEP 3: SELF-CHECK - Verify Completeness and Fill Gaps
═══════════════════════════════════════════════════════════════

Review your schema:
- Which required fields are empty?
- Which fields have partial information?

For EACH missing or incomplete field:
1. Generate a focused sub-query targeting that specific field
   Example: If missing "frequency_limits" for E083A:
   Sub-query: "What are the frequency limits for OHIP code E083A?"

2. Call the tool again with the sub-query

3. Extract the information and fill the field

REPEAT until either:
- ≥90% of required fields are filled, OR
- 3 retrieval attempts have been made, OR
- Tool returns "no results" for the missing field

═══════════════════════════════════════════════════════════════
STEP 4: SYNTHESIZE - Format Complete Answer
═══════════════════════════════════════════════════════════════

Only proceed to synthesis AFTER self-check passes.

Format your answer using the schema structure:

**[Intent Type] - [Brief Summary]**

[Schema Section 1]:
- Fact 1 [Citation]
- Fact 2 [Citation]
- ...

[Schema Section 2]:
- Fact 1 [Citation]
- Fact 2 [Citation]
- ...

[Missing Information]:
- Field X: Not found in available sources
- Field Y: Partial information available

**Citations:**
[1] Source Name > section_path
[2] Source Name > section_path
...

═══════════════════════════════════════════════════════════════
CRITICAL RULES:
═══════════════════════════════════════════════════════════════

1. NEVER skip Step 3 (Self-Check) - incomplete answers are worse than no answer
2. ALWAYS make at least 2 tool calls per query (initial retrieval + self-check sub-queries)
3. ALWAYS use section_path in citations (not just source name)
4. ALWAYS mark fields as "Not found" if not available (don't hallucinate)
5. NEVER synthesize before self-check passes (≥90% fields filled)

═══════════════════════════════════════════════════════════════

Now, apply this workflow to the user's query.
"""
```

**Implementation Steps:**

1. **Update agent.py system prompts:**
   - `src/ai_agents/dr_off_agent/agent.py` - Add Dr. OFF system prompt with Billing/Coverage/Eligibility/Documentation schemas
   - `src/ai_agents/dr_opa_agent/agent.py` - Add Dr. OPA system prompt with IPAC/Guidelines/Standards/Forms schemas

2. **Test with eval datasets:**
   ```bash
   python eval/run.py --agent dr_off --set eval/gold/dr_off_ohip_billing.json --output eval/results/05_answer_planner/dr_off_ohip.json
   ```

3. **Measure improvement:**
   - Coverage: Should increase from 19% → 75%+
   - Helpfulness: Should increase from 25% → 70%+
   - Tool calls: Should average 2-3 calls per query (vs 1 currently)

---

### Option B: Helper MCP Tools (Optional Enhancement)

**ONLY implement this if Option A (prompt-based) doesn't achieve target metrics.**

**New Files to Create:**
- `src/ai_agents/dr_off_agent/mcp/tools/answer_planner.py`
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/tools/answer_planner.py`

**New Tools:**

```python
@tool("get_answer_schema")
def get_answer_schema(intent: str) -> dict:
    """Returns required fields schema for the given intent.

    This is a helper tool - agent can also use schema from prompt.

    Args:
        intent: One of "billing", "coverage", "eligibility", "ipac", etc.

    Returns:
        Schema dict with required_fields and field_descriptions
    """
    SCHEMAS = {
        "billing": {
            "required_fields": [
                "primary_codes",
                "modifiers",
                "billing_conditions",
                "frequency_limits",
                "common_errors"
            ],
            "field_descriptions": {
                "primary_codes": "List of OHIP codes with descriptions and fees",
                "modifiers": "Applicable modifiers and when to use them",
                "billing_conditions": "Clinical conditions when codes apply",
                "frequency_limits": "Maximum billing frequency per time period",
                "common_errors": "Common billing mistakes to avoid"
            }
        },
        "ipac": {
            "required_fields": [
                "requirements_mandatory",
                "recommendations_best_practice",
                "setting_specifics",
                "equipment_rooming",
                "validation_checks"
            ],
            ...
        }
    }
    return SCHEMAS.get(intent, {"error": f"Unknown intent: {intent}"})


@tool("verify_answer_completeness")
def verify_answer_completeness(
    intent: str,
    extracted_facts: dict
) -> dict:
    """Checks which required fields are missing and suggests sub-queries.

    Args:
        intent: Query intent (billing, coverage, ipac, etc.)
        extracted_facts: Dict of schema_field → extracted_value

    Returns:
        {
            "completeness_score": 0.75,
            "filled_fields": ["primary_codes", "billing_conditions"],
            "missing_fields": ["frequency_limits", "common_errors"],
            "suggested_sub_queries": [
                "What are the frequency limits for OHIP code E083A?",
                "What are common billing errors for diabetic retinopathy?"
            ]
        }
    """
    schema = SCHEMAS[intent]
    filled = []
    missing = []

    for field in schema["required_fields"]:
        if field in extracted_facts and extracted_facts[field]:
            filled.append(field)
        else:
            missing.append(field)

    # Generate focused sub-queries for missing fields
    sub_queries = []
    for field in missing:
        # Use extracted context to make sub-query specific
        sub_query = _generate_sub_query(intent, field, extracted_facts)
        sub_queries.append(sub_query)

    completeness = len(filled) / len(schema["required_fields"])

    return {
        "completeness_score": completeness,
        "filled_fields": filled,
        "missing_fields": missing,
        "suggested_sub_queries": sub_queries,
        "pass_threshold": completeness >= 0.9
    }
```

**When to Use Option B:**
- Option A (prompt-based) doesn't achieve ≥75% Coverage
- Agent struggles to self-generate good sub-queries
- Need more structured verification logic

**Advantages of Option B:**
- ✅ Programmatic verification (more reliable than prompt-based)
- ✅ Consistent sub-query generation
- ✅ Can track metrics (tool call patterns)

**Disadvantages:**
- ❌ More code to maintain
- ❌ Slower to iterate (code changes vs prompt changes)
- ❌ Requires agent to learn new tool interface

---

## Current Baseline Performance (Post Issue #6)

From `eval/results/RESULTS.md`:

### Dr. OFF Agent
- **Recall@50:** 87% (retrieval finds relevant docs)
- **MRR:** 0.822 (best doc usually in top 2)
- **Faithfulness:** 97% (citations are accurate)
- **Coverage:** 24% ❌ (misses 76% of required facts)
- **Helpfulness:** 33% ❌ (answers often incomplete)

### Dr. OPA Agent
- **Recall@50:** 62% (retrieval finds relevant docs - will improve with Issue #6 restructuring)
- **MRR:** 0.335 (best doc at rank ~3)
- **Faithfulness:** 80% (citations mostly accurate)
- **Coverage:** 16% ❌ (misses 84% of required facts)
- **Helpfulness:** 21% ❌ (answers very incomplete)

**Key Observation:** Retrieval is decent (71% recall overall), but answer synthesis is terrible (19% coverage, 25% helpfulness). **This is the bottleneck.**

---

## Success Criteria

### Primary Metrics (Must Achieve):
1. **Coverage ≥75%** (from 19%)
   - Agent fills ≥75% of required schema fields
   - Measured via LLM-judge evaluation

2. **Helpfulness ≥70%** (from 25%)
   - Answers address user's specific question completely
   - Measured via LLM-judge evaluation

3. **Multi-Retrieval Pattern ≥2 calls/query** (from ~1)
   - Agent makes initial retrieval + ≥1 self-check sub-query
   - Measured via tool call logs

### Secondary Metrics (Nice to Have):
4. **Faithfulness ≥90%** (maintain current 86%)
   - Don't regress citation accuracy

5. **Answer Structure Compliance ≥90%**
   - Answers follow schema-based format
   - Include section headings per schema

---

## Testing Strategy

### Phase 1: Unit Tests (New)
Create `tests/agents/test_answer_planner.py`:

```python
def test_agent_follows_four_step_workflow():
    """Agent should: Plan → Retrieve → Self-Check → Synthesize."""
    agent = DrOFFAgent()
    query = "How do I bill for diabetic retinopathy laser treatment?"

    # Mock tool responses
    with mock_tool_responses():
        response = agent.query(query)

    # Verify 4-step workflow
    assert agent.tool_call_count >= 2, "Agent should make ≥2 tool calls (initial + self-check)"
    assert "primary_codes" in response.lower(), "Should extract primary codes"
    assert "frequency_limits" in response.lower() or "not found" in response.lower(), "Should address frequency limits"
    assert "[1]" in response, "Should include citations"

def test_agent_fills_schema_fields():
    """Agent should fill ≥90% of schema fields."""
    agent = DrOFFAgent()
    query = "What are the billing requirements for E083A?"

    response = agent.query(query)

    # Extract filled fields
    filled_fields = extract_filled_fields(response, intent="billing")
    required_fields = ["primary_codes", "billing_conditions", "frequency_limits"]

    completeness = len(filled_fields) / len(required_fields)
    assert completeness >= 0.9, f"Only filled {completeness:.0%} of required fields"
```

### Phase 2: Integration Tests (Existing Eval Framework)

```bash
# Run existing eval datasets with new agent
python eval/run.py --agent dr_off --set eval/gold/dr_off_ohip_billing.json --output eval/results/05_answer_planner/dr_off_ohip.json
python eval/run.py --agent dr_opa --set eval/gold/dr_opa_pho_ipac.json --output eval/results/05_answer_planner/dr_opa_pho.json

# Compare to baseline
python scripts/compare_eval_results.py \
  eval/results/baseline/dr_off_ohip_billing.json \
  eval/results/05_answer_planner/dr_off_ohip.json
```

**Expected Results:**
- Coverage: 24% → 75%+ (3x improvement)
- Helpfulness: 33% → 70%+ (2x improvement)
- Tool calls: ~1 → 2-3 per query

### Phase 3: Qualitative Review

Manually review 10 random answers from eval results:
1. Does answer follow schema structure?
2. Are all schema fields addressed (filled or marked "not found")?
3. Are citations complete with section_path?
4. Would a physician find this answer actionable?

---

## Implementation Checklist

### Phase 1: System Prompt Implementation (Option A)
- [ ] Update `src/ai_agents/dr_off_agent/agent.py` with 4-step workflow prompt
- [ ] Update `src/ai_agents/dr_opa_agent/agent.py` with 4-step workflow prompt
- [ ] Define intent schemas for Dr. OFF: Billing, Coverage, Eligibility, Documentation
- [ ] Define intent schemas for Dr. OPA: IPAC, Guidelines, Standards, Forms
- [ ] Test with 3 sample queries per agent (manual verification)

### Phase 2: Evaluation
- [ ] Run eval on all Dr. OFF datasets (3 datasets)
- [ ] Run eval on all Dr. OPA datasets (6 datasets)
- [ ] Compare Coverage and Helpfulness to baseline
- [ ] Verify ≥2 tool calls per query in logs
- [ ] Qualitative review of 10 random answers

### Phase 3: Iteration (If Needed)
- [ ] If Coverage <75%: Refine schema definitions or add Option B helper tools
- [ ] If Helpfulness <70%: Improve synthesis template in prompt
- [ ] If Faithfulness <90%: Add citation verification step

### Phase 4: Documentation
- [ ] Update `improve_retrieval/backlog.md` Issue #5 status to "✅ COMPLETED"
- [ ] Create `improve_retrieval/ISSUE_5_COMPLETE_SUMMARY.md` with results
- [ ] Update system prompt templates in repo documentation

---

## Key Files to Work With

### Agent Implementation (PRIMARY CHANGES):
- `src/ai_agents/dr_off_agent/agent.py` - Add system prompt with 4-step workflow
- `src/ai_agents/dr_opa_agent/agent.py` - Add system prompt with 4-step workflow

### Evaluation (RUN TESTS):
- `eval/run.py` - Run evaluations with new agent
- `eval/results/baseline/` - Compare against baseline metrics
- `eval/gold/` - Gold datasets for testing (9 datasets total)

### Existing Tools (NO CHANGES):
- `src/ai_agents/dr_off_agent/mcp/tools/*.py` - Tools already return good chunks
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/tools/*.py` - Parent context enrichment working

### Optional Helper Tools (IF OPTION A INSUFFICIENT):
- `src/ai_agents/dr_off_agent/mcp/tools/answer_planner.py` (NEW FILE - create if needed)
- `src/ai_agents/dr_opa_agent/dr_opa_mcp/tools/answer_planner.py` (NEW FILE - create if needed)

---

## Common Pitfalls to Avoid

### ❌ DON'T: Modify MCP Tools
The existing retrieval tools (`search_ohip_schedule`, `search_cpso_policies`, etc.) already work well. Don't add answer planning logic to tools - keep them focused on retrieval.

### ❌ DON'T: Hardcode Answer Templates
Don't create rigid answer templates. Use schema fields as guidance, but let the agent synthesize naturally based on available information.

### ❌ DON'T: Skip Self-Check Step
The self-check loop is critical. Without it, agent will miss information just like the baseline. Make sure agent actually generates sub-queries and calls tools again.

### ✅ DO: Start with Prompt Engineering (Option A)
Option A (system prompt) is faster to implement and iterate. Only add Option B (helper tools) if Option A doesn't hit target metrics.

### ✅ DO: Log Tool Calls
Add logging to track:
- How many tool calls per query
- What sub-queries are generated
- Which schema fields remain unfilled

This will help debug if Coverage doesn't improve.

### ✅ DO: Use Existing Eval Framework
Don't create new evaluation code. Use `eval/run.py` and existing LLM-judge metrics.

---

## Example Query Walkthrough (Expected Behavior)

**User Query:** "How do I bill for diabetic retinopathy laser treatment?"

**Step 1 - PLAN:**
```
Agent thinks:
- Intent: Billing (user asks "how do I bill")
- Schema: [primary_codes, modifiers, billing_conditions, frequency_limits, common_errors]
```

**Step 2 - RETRIEVE (Initial):**
```
Agent calls: search_ohip_schedule(query="diabetic retinopathy laser treatment", top_k=5)

Retrieved chunks:
1. "E083A - Diabetic retinopathy, laser photocoagulation - $245.00"
2. "E083B - Diabetic retinopathy, follow-up - $82.50"
3. "E083C - Extensive photocoagulation - $490.00"
4. "Conditions: Type 1 or 2 diabetes, documented retinopathy"
5. "Coverage: Eligible patients with diabetic retinopathy diagnosis"

Agent extracts:
✓ primary_codes: [E083A, E083B, E083C]
✓ billing_conditions: [Type 1/2 diabetes, documented retinopathy]
✗ modifiers: (not found)
✗ frequency_limits: (not found)
✗ common_errors: (not found)
```

**Step 3 - SELF-CHECK:**
```
Agent checks schema:
- Completeness: 2/5 fields = 40%
- Missing: [modifiers, frequency_limits, common_errors]

Agent generates sub-queries:
1. "What are the frequency limits for OHIP code E083A?"
2. "What modifiers apply to diabetic retinopathy laser codes?"
3. "What are common billing errors for diabetic retinopathy?"

Agent calls: search_ohip_schedule(query="E083A frequency limits", top_k=3)

Retrieved:
1. "E083A: Maximum once per 6 months per eye"

Agent extracts:
✓ frequency_limits: "E083A: max once per 6 months per eye"

Agent calls: search_ohip_schedule(query="diabetic retinopathy modifiers", top_k=3)
Retrieved: No relevant results

Agent calls: search_ohip_schedule(query="diabetic retinopathy billing errors", top_k=3)
Retrieved: No relevant results

Final completeness: 3/5 = 60% (below 90% threshold, but no more results available)
```

**Step 4 - SYNTHESIZE:**
```
Agent formats answer:

Billing Codes for Diabetic Retinopathy Laser Treatment

Primary Codes:
- E083A: Laser photocoagulation ($245.00) [1]
- E083B: Follow-up examination ($82.50) [1]
- E083C: Extensive treatment ($490.00) [1]

Billing Conditions:
- Patient must have Type 1 or Type 2 diabetes [2]
- Documented diabetic retinopathy required [2]

Frequency Limits:
- E083A: Maximum once per 6 months per eye [3]

Missing Information:
- Modifiers: Not found in available sources
- Common Errors: Not found in available sources

Citations:
[1] OHIP Schedule of Benefits > E > Ophthalmology > Retinal Procedures
[2] OHIP Schedule of Benefits > E > Ophthalmology > Coverage Criteria
[3] OHIP Schedule of Benefits > E > Ophthalmology > Frequency Limits
```

**Result:**
- Coverage: 60% (3/5 schema fields)
- Helpfulness: HIGH (actionable answer with clear structure)
- Faithfulness: 100% (all facts cited, missing info marked as "not found")
- Tool calls: 4 (initial + 3 sub-queries)

---

## Questions? Blockers?

### Q: Should I use Option A (prompt) or Option B (helper tools) first?
**A:** Start with Option A (prompt-based). It's faster to iterate and leverages OpenAI Agents SDK native capabilities. Only add Option B if Option A doesn't hit ≥75% Coverage.

### Q: How do I know if the agent is following the 4-step workflow?
**A:** Check tool call logs. You should see:
- ≥2 tool calls per query (initial + sub-queries)
- Sub-queries are more specific than initial query
- Final answer has schema structure (section headings)

### Q: What if Coverage improves but Helpfulness doesn't?
**A:** This means schema fields are filled, but answer format is poor. Improve the synthesis template in Step 4 of the prompt (add examples of well-formatted answers).

### Q: What if agent skips self-check step?
**A:** Strengthen the prompt instructions:
- Add "CRITICAL: Do NOT skip Step 3"
- Add "NEVER proceed to Step 4 until self-check passes"
- Consider adding Option B `verify_answer_completeness()` tool to force programmatic check

---

## Success Definition

Issue #5 is considered **COMPLETE** when:
1. ✅ Coverage ≥75% on all eval datasets
2. ✅ Helpfulness ≥70% on all eval datasets
3. ✅ Tool calls average ≥2 per query
4. ✅ Answers follow schema-based structure (section headings per schema)
5. ✅ Documentation updated in backlog.md

**After Issue #5:** We'll have high-quality retrieval (Issue #6) + structured answer synthesis (Issue #5) = production-ready AI agents.

---

## Timeline Estimate

- **Option A Implementation:** 2-4 hours (prompt engineering)
- **Evaluation:** 1-2 hours (run eval scripts)
- **Iteration:** 2-4 hours (refine prompts based on results)
- **Option B (if needed):** +4-6 hours (implement helper tools)
- **Total:** 5-16 hours depending on whether Option B is needed

---

## Final Note

**Remember:** The goal is NOT to make retrieval better (that's already 71% recall). The goal is to make the **agent use the retrieved information better** through structured extraction and verification.

Good luck! 🚀
