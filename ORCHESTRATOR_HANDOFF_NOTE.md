# Orchestrator Performance Improvements - Handoff Note

**Date:** October 14, 2025
**Session:** Claude Code debugging orchestrator timeout and empty tool results
**Commit:** `a8229f3` - "fix: Resolve orchestrator empty tool results through ChromaDB metadata and filter fixes"

---

## What Was Fixed ✅

### 1. CEP Clinical Tools - ChromaDB $or Filter Bug
**Problem:** Tool returned 0 results despite correct triage (confidence 0.95)

**Root Cause:** ChromaDB's `$or` operator requires at least 2 items in the list. When only 1 clinical tool was identified, the query failed with:
```
Expected where value for $and or $or to be a list with at least two where expressions
```

**Fix:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/cep_helpers.py:167-179`
```python
if len(tool_urls) == 1:
    where_filter = {"source_url": tool_urls[0]}
else:
    where_filter = {
        "$or": [{"source_url": url} for url in tool_urls]
    }
```

**Result:** ✅ Now returns 5 chunks with confidence 0.80 (was 0 before)

**Test Command:**
```bash
source ~/spacy_env/bin/activate
python scripts/test_mcp_tools_direct.py --agent dr_opa --tool opa_clinical_tools --query "guideline-directed medical therapy for heart failure"
```

---

### 2. Choosing Wisely Triage - LLM Misclassification
**Problem:** Clinical queries misclassified as "specialty_discovery" instead of "specific_recommendation"

**Example:** "Choosing Wisely recommendations relevant to heart failure" was incorrectly classified as specialty_discovery

**Fix:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/choosing_wisely_triage.py:174-181`

Added explicit classification rules:
```python
**Critical Rules**:
- If query mentions ANY clinical condition, disease, test, procedure, or patient scenario → "specific_recommendation"
- If query asks about "recommendations FOR/ABOUT X" (where X is a condition/test) → "specific_recommendation"
- ONLY use "specialty_discovery" if query is literally "What does X specialty recommend?" with NO clinical context
```

**Result:** ✅ Correct classification, returns appropriate results

---

### 3. Choosing Wisely Metadata - Nested Structure
**Problem:** Only 1 recommendation returned despite retrieving 10 chunks

**Root Cause:** ChromaDB stores metadata in nested `metadata.metadata` structure, but code accessed top-level only

**Fix 1:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py:2382-2396` (handler-specific)
**Fix 2:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py:496-500` (global)

Added metadata flattening logic:
```python
nested_metadata = metadata.get('metadata', {})
if nested_metadata:
    metadata = {**metadata, **nested_metadata}
```

**Result:** ✅ Returns 4 recommendations (was 1 before)

---

### 4. Choosing Wisely Limiting - Incorrect Sort Logic
**Problem:** Limited by `recommendation_number <= k` instead of total count

**Fix:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py:2515-2523`

Changed from:
```python
recommendations.sort(key=lambda r: r.metadata['recommendation_number'])
if len(recommendations) > k:
    max_rec_num = k
    recommendations = [r for r in recommendations if r.metadata['recommendation_number'] <= max_rec_num]
```

To:
```python
recommendations.sort(key=lambda r: (-r.relevance_score, r.metadata['recommendation_number']))
if len(recommendations) > k:
    recommendations = recommendations[:k]
```

**Result:** ✅ Properly limits to top k by relevance, then by number

---

### 5. Schedule Tool - AttributeError with Document Objects
**Problem:** `'Document' object has no attribute 'get'` after LLM reranker

**Root Cause:** `_merge_citations()` expected `List[Dict]` but received `List[Document]` from reranker

**Fix:** `src/ai_agents/dr_off_agent/mcp/tools/schedule.py:551-556`
```python
if isinstance(result, Document):
    metadata = result.metadata or {}
else:
    metadata = result.get('metadata', {})
```

**Result:** ✅ Tool handles both Dict and Document objects

---

## What Still Needs Investigation ⏸️

### Issue 2: Reasoning Parameter Differences
**User Feedback:** "I only see reasoning on Dr OFF, not the other agents. can you check if there's a difference in how the modelsettings for reasoning are set up (what param is set for summary). They should also provide summary reasoning"

**Files to Check:**
- `src/ai_agents/dr_off_agent/openai_agent.py`
- `src/ai_agents/dr_opa_agent/openai_agent.py`
- `src/ai_agents/agent_97/openai_agent.py`
- `src/ai_agents/diagnostic_orchestrator/orchestrator_agent.py`

**Search for:** `reasoning_effort`, `reasoningEffort`, `include_reasoning_content`

**Status:** Not started

---

### Issue 3: opa_program_lookup Empty Results
**User Feedback:** "opa_program_lookup returned empty results on one of the queries. this shouldn't happen with a web search"

**Example Input:**
```python
opa_program_lookup({
  "query": "heart failure and diabetes comorbidity provincial care pathway Ontario 'heart failure diabetes' 'care pathway' 'Ontario Health' 'CorHealth'",
  "k": 8
})
```

**Output:** All fields empty (items: [], citations: [], etc.)

**Root Cause:** Uses Claude's `web_search` tool which can hang or return empty

**Investigation Needed:**
1. Check timeout settings for Claude API calls
2. Verify web_search tool configuration in `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py` (search for `opa_program_lookup`)
3. Test if this is reproducible or intermittent
4. Consider fallback strategies if web search fails

**Status:** Not started

---

### Issue 4: LLM Call Analysis
**User Request:** "Review src code to analyze and then summarize the number of LLM calls by agent tool, grouped by OpenAI vs. Claude. Include the agent themselves in the list (which make its own openai llm calls)"

**Approach:**
1. Grep for `openai.chat.completions.create` and `anthropic.messages.create`
2. Map each call to agent/tool
3. Create summary table:
   ```
   | Agent/Tool                    | Provider | Model          | Purpose                    |
   |-------------------------------|----------|----------------|----------------------------|
   | Dr. OPA Agent                 | OpenAI   | gpt-4o-mini    | Main agent orchestration   |
   | opa_clinical_tools (triage)   | OpenAI   | gpt-4o-mini    | Tool classification        |
   | opa_choosing_wisely (triage)  | OpenAI   | gpt-4o-mini    | Specialty classification   |
   | opa_program_lookup            | Claude   | claude-3-5-... | Web search wrapper         |
   | ...                           | ...      | ...            | ...                        |
   ```

**Status:** Not started

---

## Testing Commands

### Test All Dr. OPA Tools
```bash
source ~/spacy_env/bin/activate

# CEP Clinical Tools
python scripts/test_mcp_tools_direct.py --agent dr_opa --tool opa_clinical_tools --query "heart failure management"

# Choosing Wisely
python scripts/test_mcp_tools_direct.py --agent dr_opa --tool opa_choosing_wisely --query "unnecessary imaging low back pain"

# Program Lookup
python scripts/test_mcp_tools_direct.py --agent dr_opa --tool opa_program_lookup --query "heart failure care pathway Ontario"
```

### Test Orchestrator
```bash
python test_orchestrator_reasoning.py
```

**Expected:** Should complete without timeout, tools should return non-empty results

---

## Key Files Modified (Committed)

1. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/cep_helpers.py`
2. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/choosing_wisely_triage.py`
3. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py`
4. `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py`
5. `src/ai_agents/dr_off_agent/mcp/tools/schedule.py`

---

## Key Learnings

1. **ChromaDB `$or` Constraint:** Requires at least 2 items in the list. Always check list length before using `$or`.

2. **Nested Metadata:** ChromaDB can store metadata in `metadata.metadata` structure. Always flatten when accessing.

3. **LLM Triage Prompts:** Need very explicit rules to prevent misclassification. "DEFAULT" behavior must be clearly stated.

4. **Type Handling:** After reranking, results can be `Document` objects instead of dicts. Always check types.

5. **Orchestrator Debugging:** Empty tool results during orchestration can have different root causes than when testing tools directly. Always test both ways.

---

## Environment Info

- **Python:** 3.11+
- **Virtual Env:** `~/spacy_env/bin/activate`
- **API Keys:** Loaded from `~/thunder_playbook/.env`
- **Server:** http://localhost:8000 (uvicorn)
- **Branch:** `main` (commit `a8229f3`)

---

## Next Steps for Fresh Session

1. **Start Here:** Pull latest from main (`git pull`)
2. **Verify Fixes:** Run test commands above to confirm tools work
3. **Issue #2:** Investigate reasoning parameter differences between agents
4. **Issue #3:** Debug opa_program_lookup empty results (web search)
5. **Issue #4:** Analyze and document LLM call distribution

**Priority Order:** Issue #3 (program_lookup) is most urgent as it directly impacts orchestrator functionality.

---

**Note:** Orchestrator still times out occasionally (5-10 min) due to unrelated issues (e.g., web search hanging). The fixes above resolve **empty tool results**, not timeouts.
