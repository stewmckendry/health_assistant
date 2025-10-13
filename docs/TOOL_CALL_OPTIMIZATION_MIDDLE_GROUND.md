# Chief Resident - Tool Call Optimization (Middle Ground Approach)

## Context

**Date**: October 2025
**Issue**: Complex queries taking 5+ minutes due to excessive tool calls (19+ per query)
**Root Cause**: Aggressive self-check loops - agents calling same MCP tool 6-9 times
**Constraint**: Self-check was introduced to improve quality - cannot remove entirely
**Goal**: Balance quality and speed

---

## Current Performance Analysis

### Trace Evidence (Screenshots from OpenAI Dashboard)

**Example 1 - Total Time: 297.68s (~5 minutes)**
- **Agent 97**: 3x `clinician_search` calls (259s total)
- **Dr. OPA**: 6x MCP tool calls including:
  - opa_policy_check (44s)
  - opa_ipac_guidance (43s)
  - opa_clinical_tools (45s)
  - opa_program_lookup (20s)
  - opa_quality_standards (50s)
  - opa_search_sections (29s)
- **Dr. OFF**: 9x tool calls (203s total):
  - 1x schedule_get (17s)
  - **8x odb_get** (called repeatedly: 4ms, 4ms, 5ms, 6ms, 7ms, 6ms, 7ms)

**Example 2 - Total Time: 296.49s (~5 minutes)**
- **Dr. OPA**: 3x MCP tool calls (190s total)
  - opa_program_lookup (24s)
  - opa_clinical_tools (28s)
  - opa_search_sections (29s)
- **Dr. OFF**: 7+ `schedule_get` calls (198s total)
  - Called repeatedly: 17s, 9s, 8s, 11s, 10s, 20s, 6s...
- **Agent 97**: 4x `clinician_search` calls (251s total)
  - 35s, 34s, 38s, 32s

### Problem Identification

**NOT web_search overuse** - minimal web_search calls observed
**YES MCP tool loops** - same tool called 6-9 times with slightly different queries

**Current Self-Check Logic:**
```
CRITICAL RULES FOR SELF-CHECK:
- Make at least 2 tool calls per query (initial retrieval + ≥1 self-check sub-query)
- Repeat until ≥90% of required fields are filled OR 3 retrieval attempts made
- Try MCP tools first, then web_search if needed
- If all tools return "no results" for a field, mark it as "Not found in available sources"
- NEVER proceed to synthesis with <50% field completeness
```

**Why this causes loops:**
- Agents have detailed "required fields" templates
- Try to achieve 90% completeness
- Will make 3 retrieval attempts per field
- Each attempt can call multiple tools
- **Worst case: 3 agents × 3 attempts × 3 tools = 27 tool calls**

---

## Middle Ground Solution

### Design Principles

1. ✅ **Keep self-check** - quality improved significantly with this feature
2. ✅ **Keep web_search** - important fallback for gaps in MCP data
3. 🔄 **Add hard caps** - prevent runaway loops (max 4 calls per agent)
4. 🔄 **Allow repetition** - but limit to 2x same tool (not 9x)
5. 🔄 **Reduce completeness** - 70% is good enough, not 90%
6. 🔄 **Prioritize fields** - core fields vs nice-to-have

### Strategy

**Smart Limits:**
- Allow 2-4 tool calls per agent (down from unlimited)
- Allow calling same tool twice (initial + self-check)
- Allow using different tools for different aspects
- Target 70% core field completeness (down from 90%)

**Quality Preservation:**
- Keep web_search for when MCP tools fail
- Keep self-check for missing critical fields
- Keep multi-tool strategy for comprehensive coverage
- Define "core" vs "nice-to-have" fields

---

## Proposed Changes

### Dr. OFF Agent (`src/ai_agents/dr_off_agent/openai_agent.py`)

**Current (Lines 532-537):**
```python
CRITICAL RULES FOR SELF-CHECK:
- Make at least 2 tool calls per query (initial retrieval + ≥1 self-check sub-query)
- Repeat until ≥90% of required fields are filled OR 3 retrieval attempts made
- Try MCP tools first, then web_search if needed
- If all tools return "no results" for a field, mark it as "Not found in available sources"
- NEVER proceed to synthesis with <50% field completeness
```

**Proposed:**
```python
CRITICAL RULES FOR SELF-CHECK:
- Make 2-4 tool calls maximum per query:
  * Initial retrieval: 1-2 different tools (e.g., schedule_get for billing codes, odb_get for drugs)
  * Self-check: ONE additional call per tool type if critical fields are missing
  * Example: schedule_get → [check results] → schedule_get again with refined query if needed
  * Do NOT call the same tool more than 2 times
- Stop after ≥70% of core fields are filled OR after 4 total tool calls (whichever comes first)
- Try MCP tools first, then web_search if needed
- For missing non-critical fields, mark as "Details not available in current sources"
- Proceed to synthesis when core query is answerable (even if some fields incomplete)

**Core fields** (must try to fill): billing codes, coverage status, cost
**Nice-to-have fields**: frequency limits, special authorizations, alternative options
```

**Diff:**
```diff
@@ Lines 532-537 @@

 CRITICAL RULES FOR SELF-CHECK:
-- Make at least 2 tool calls per query (initial retrieval + ≥1 self-check sub-query)
-- Repeat until ≥90% of required fields are filled OR 3 retrieval attempts made
+- Make 2-4 tool calls maximum per query:
+  * Initial retrieval: 1-2 different tools (e.g., schedule_get for billing codes, odb_get for drugs)
+  * Self-check: ONE additional call per tool type if critical fields are missing
+  * Example: schedule_get → [check results] → schedule_get again with refined query if needed
+  * Do NOT call the same tool more than 2 times
+- Stop after ≥70% of core fields are filled OR after 4 total tool calls (whichever comes first)
 - Try MCP tools first, then web_search if needed
-- If all tools return "no results" for a field, mark it as "Not found in available sources"
+- For missing non-critical fields, mark as "Details not available in current sources"
-- NEVER proceed to synthesis with <50% field completeness
+- Proceed to synthesis when core query is answerable (even if some fields incomplete)
+
+**Core fields** (must try to fill): billing codes, coverage status, cost
+**Nice-to-have fields**: frequency limits, special authorizations, alternative options
```

---

### Dr. OPA Agent (`src/ai_agents/dr_opa_agent/openai_agent.py`)

**Current (Lines 560-565):**
```python
CRITICAL RULES FOR SELF-CHECK:
- Make at least 2 tool calls per query (initial retrieval + ≥1 self-check sub-query)
- Repeat until ≥90% of required fields are filled OR 3 retrieval attempts made
- Try MCP tools first, then web_search if needed
- If all tools return "no results" for a field, mark it as "Not found in available sources"
- NEVER proceed to synthesis with <50% field completeness
```

**Proposed:**
```python
CRITICAL RULES FOR SELF-CHECK:
- Make 2-4 tool calls maximum per query:
  * Initial retrieval: 1-2 most relevant tools (e.g., opa_policy_check for regulations, opa_quality_standards for clinical guidance)
  * Self-check: ONE additional call per tool type if critical gaps exist
  * Use different tools for different aspects (policy_check + quality_standards is fine)
  * Do NOT call the same tool more than 2 times
- Stop after ≥70% of core fields are filled OR after 4 total tool calls (whichever comes first)
- Try MCP tools first, then web_search if needed
- For missing non-critical fields, mark as "Additional details not available"
- Proceed to synthesis when core query is answerable (even if some fields incomplete)

**Core fields** (must try to fill): CPSO requirements, key policies, mandatory reporting
**Nice-to-have fields**: related guidelines, program details, historical context
```

**Diff:**
```diff
@@ Lines 560-565 @@

 CRITICAL RULES FOR SELF-CHECK:
-- Make at least 2 tool calls per query (initial retrieval + ≥1 self-check sub-query)
-- Repeat until ≥90% of required fields are filled OR 3 retrieval attempts made
+- Make 2-4 tool calls maximum per query:
+  * Initial retrieval: 1-2 most relevant tools (e.g., opa_policy_check for regulations, opa_quality_standards for clinical guidance)
+  * Self-check: ONE additional call per tool type if critical gaps exist
+  * Use different tools for different aspects (policy_check + quality_standards is fine)
+  * Do NOT call the same tool more than 2 times
+- Stop after ≥70% of core fields are filled OR after 4 total tool calls (whichever comes first)
 - Try MCP tools first, then web_search if needed
-- If all tools return "no results" for a field, mark it as "Not found in available sources"
+- For missing non-critical fields, mark as "Additional details not available"
-- NEVER proceed to synthesis with <50% field completeness
+- Proceed to synthesis when core query is answerable (even if some fields incomplete)
+
+**Core fields** (must try to fill): CPSO requirements, key policies, mandatory reporting
+**Nice-to-have fields**: related guidelines, program details, historical context
```

---

### Agent 97 (`src/ai_agents/agent_97/openai_agent.py`)

**Find similar self-check section and apply:**

```diff
-- Make multiple clinician_search calls to ensure comprehensive coverage
-- Repeat until sufficient evidence gathered
+- Make 2-3 clinician_search calls maximum:
+  * Initial search: Broad query for main topic
+  * Self-check: ONE refined search if critical clinical info is missing
+  * Optional third call: Only if user asks for "latest" or "comprehensive" review
+- Stop after 2 calls if good clinical guidance is found
+- Stop after 3 calls regardless of completeness
+- Proceed to synthesis with available evidence (note if evidence is limited)
```

---

## Expected Impact Analysis

### Tool Call Reduction

| Agent | Current Calls | Middle Ground | Reduction |
|-------|---------------|---------------|-----------|
| **Dr. OFF** | 9 calls (8x odb_get) | 2-4 calls (2x odb_get max) | 56-78% |
| **Dr. OPA** | 6 calls (various tools) | 3-4 calls (diverse tools) | 33-50% |
| **Agent 97** | 4 calls (clinician_search) | 2-3 calls | 25-50% |
| **Total** | ~19 tool calls | **7-11 tool calls** | **42-63%** |

### Time Reduction

**Current:**
- Example 1: 297.68s (~5 minutes)
- Example 2: 296.49s (~5 minutes)

**Expected with Middle Ground:**
- Estimated: **2.5-3.5 minutes** (~40-50% reduction)
- Breakdown:
  - Dr. OFF: 203s → 80-120s
  - Dr. OPA: 191s → 80-120s
  - Agent 97: 259s → 120-180s
  - Total: ~280-420s (4.5-7 min) → ~150-210s (2.5-3.5 min)

### Quality Impact (Risk Assessment)

**What We Keep (Low Risk):**
- ✅ Self-check for critical fields
- ✅ Web_search fallback capability
- ✅ Multiple tool types for comprehensive coverage
- ✅ 70% core field completeness (sufficient for most queries)

**What We Lose (Acceptable Trade-off):**
- ⚠️ 90% → 70% completeness target (20% reduction in "nice-to-have" details)
- ⚠️ 3 retrieval attempts → 1 retry (may miss edge cases)
- ⚠️ Some non-critical fields may be marked "not available"

**Mitigation Strategies:**
- Monitor field completeness metrics in Langfuse
- If quality drops below acceptable, increase from 70% → 80%
- If specific queries consistently fail, add to "core fields" list
- User feedback will indicate if responses lack critical info

---

## Implementation Plan

### Phase 1: Update System Prompts (30-45 minutes)

**Files to change:**
1. `src/ai_agents/dr_opa_agent/openai_agent.py` (lines 560-565)
2. `src/ai_agents/dr_off_agent/openai_agent.py` (lines 532-537)
3. `src/ai_agents/agent_97/openai_agent.py` (find similar section)

**Changes per file:**
- Replace "CRITICAL RULES FOR SELF-CHECK" section with new version
- Add "Core fields" vs "Nice-to-have fields" definitions
- Update field completeness threshold from 90% → 70%

### Phase 2: Test with Sample Queries (1-2 hours)

**Test Cases:**
1. **Simple query**: "What OHIP code for diabetes follow-up?"
   - Expected: 1-2 tool calls, <60s
2. **Moderate query**: "CPSO requirements for prescribing opioids"
   - Expected: 2-3 tool calls, 90-120s
3. **Complex query**: "Manage diabetic patient with new hypertension - CPSO requirements, OHIP billing, ODB coverage"
   - Expected: 7-11 tool calls, 150-210s

**Success Criteria:**
- ✅ Tool calls reduced to 2-4 per agent
- ✅ Total time <4 minutes for complex queries
- ✅ Response quality maintained (manual review)
- ✅ Core fields populated in >90% of test cases

### Phase 3: Deploy and Monitor (Ongoing)

**Metrics to track in Langfuse:**
1. **Tool calls per agent** (target: 2-4)
2. **Total response time** (target: <3.5 min for complex)
3. **Field completeness** (target: >70% core fields)
4. **User satisfaction** (thumbs up/down feedback)

**Rollback triggers:**
- Field completeness drops below 60%
- User satisfaction drops >20%
- Complaints about missing critical information

### Phase 4: Fine-Tune (If Needed)

**If quality drops:**
- Increase 70% → 75% → 80% core field requirement
- Increase 4 → 5 tool call limit
- Add specific fields to "core" list based on user feedback

**If still too slow:**
- Reduce 70% → 65% completeness target
- Reduce 4 → 3 tool call limit
- Remove some "nice-to-have" fields entirely

---

## Monitoring Dashboard (Langfuse)

### Key Metrics to Track

**Performance:**
- Average tool calls per query (baseline: 19, target: 7-11)
- Average response time (baseline: 296s, target: 150-210s)
- P50, P90, P95 latencies

**Quality:**
- Core field completeness % (target: >70%)
- Nice-to-have field completeness % (expected: 40-60%)
- User feedback scores (thumbs up/down)
- Specific feedback comments about missing info

**Cost:**
- Token usage per query (should decrease with fewer tool calls)
- API cost per query (should decrease proportionally)

### Alert Thresholds

**Performance Alerts:**
- 🔴 Average tool calls >12 (optimization not working)
- 🟡 Average response time >240s (not hitting speed target)

**Quality Alerts:**
- 🔴 Core field completeness <60% (quality degradation)
- 🔴 User satisfaction <70% thumbs up (users unhappy)
- 🟡 Nice-to-have completeness <30% (may be too aggressive)

---

## Rollback Plan

If optimization causes unacceptable quality degradation:

### Step 1: Immediate Rollback (5 minutes)
```bash
git revert HEAD  # Revert the prompt changes
git push origin main
# Railway auto-deploys original version
```

### Step 2: Partial Rollback (Adjust Parameters)
Instead of full revert, adjust thresholds:
- Change 70% → 80% completeness
- Change 4 → 5 tool call limit
- Change "1 retry" → "2 retries"

### Step 3: Alternative Approach
If middle ground doesn't work:
- Consider caching common MCP tool results
- Implement smarter tool selection logic
- Use different models for different agents (faster models for simple lookups)

---

## Success Metrics (90 Days Post-Implementation)

**Must Achieve:**
- ✅ Average tool calls: <12 per query
- ✅ Average response time: <4 minutes
- ✅ Core field completeness: >70%
- ✅ User satisfaction: >75% thumbs up

**Nice to Have:**
- 🎯 Average tool calls: 7-11 per query
- 🎯 Average response time: 2.5-3.5 minutes
- 🎯 Core field completeness: >75%
- 🎯 User satisfaction: >80% thumbs up

**If achieved**: Consider further optimization (e.g., model switching, caching)
**If not achieved**: Analyze failures and adjust parameters or rollback

---

## Related Documents

- `CHIEF_RESIDENT_PERFORMANCE_OPTIMIZATION.md` - Overall performance analysis including model selection
- `CHIEF_RESIDENT_API.md` - API documentation for evaluation workflow
- `COLD_START_BUG_FIX.md` - Recent initialization bug fix

---

## Revision History

- **2025-10-12**: Initial middle ground proposal based on OpenAI trace analysis
  - Identified MCP tool loops as root cause (not web_search)
  - Proposed 2-4 tool call limits with smart self-check
  - Target: 60% reduction in tool calls, 40-50% reduction in time
