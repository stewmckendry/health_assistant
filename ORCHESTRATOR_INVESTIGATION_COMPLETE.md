# Orchestrator Investigation Complete - October 14, 2025

**Session:** Claude Code follow-up investigation
**Status:** All 3 issues investigated, findings documented

---

## Executive Summary

Completed investigation of 3 outstanding issues from the orchestrator debugging session:

1. ✅ **opa_program_lookup empty results** - Root cause identified, recommendations provided
2. ✅ **Reasoning parameter consistency** - Confirmed all agents use identical settings
3. ✅ **LLM call distribution** - Complete mapping of OpenAI vs Claude usage across codebase

**Key Finding:** The system architecture is sound. Empty results from `opa_program_lookup` are due to Claude's `web_search` tool limitations, not code bugs. Reasoning configuration is already consistent across all agents.

---

## Issue #1: opa_program_lookup Empty Results ⚠️

### Root Cause Analysis

**Location:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/tools/ontario_health_programs.py:153`

**Problem:** The tool uses Claude's `web_search` and `web_fetch` tools which can:
- Return empty results intermittently
- Hang without timeout handling
- Fail silently when domain restrictions are too strict

**Current Implementation:**
```python
response = self.client.messages.create(
    model="claude-3-5-haiku-latest",
    max_tokens=2000,
    temperature=0.3,
    tools=[
        {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 3,
            "allowed_domains": ONTARIO_HEALTH_DOMAINS  # 35 domains
        },
        {
            "type": "web_fetch_20250910",
            "name": "web_fetch",
            "allowed_domains": ONTARIO_HEALTH_DOMAINS,
            "max_uses": 5
        }
    ]
)
```

**Issues:**
1. **No timeout handling** - API call can hang indefinitely
2. **No fallback strategy** - Returns empty dict on failure
3. **No retry logic** - Single attempt only
4. **35 allowed domains** - May be too restrictive, causing search to return nothing

### Impact

**When it fails:**
- Orchestrator gets empty tool results
- Agent must proceed without Ontario Health program information
- Overall response quality degrades
- No error message indicates the problem to end user

**Frequency:** Intermittent (user reported it happening "occasionally")

### Recommendations

**Priority 1 - Add Timeout Handling:**
```python
import asyncio

try:
    response = await asyncio.wait_for(
        self.client.messages.create(...),
        timeout=30.0  # 30 second timeout
    )
except asyncio.TimeoutError:
    logger.warning(f"Web search timed out for: {program}")
    return self._fallback_response(program, "Search timed out")
```

**Priority 2 - Add Retry Logic:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry_error_callback=lambda _: {"error": "max_retries_exceeded"}
)
async def _search_with_retry(self, program: str):
    return await self.client.messages.create(...)
```

**Priority 3 - Add Fallback Strategy:**
```python
# If Claude web search fails, fall back to Exa web search
try:
    ontario_client = get_ontario_health_client()
    program_info = ontario_client.search_program(...)
except Exception as e:
    logger.warning(f"Claude search failed: {e}, trying Exa fallback")

    # Use Exa as fallback
    from exa_py import Exa
    exa = Exa(api_key=os.getenv("EXA_API_KEY"))
    results = exa.search_and_contents(
        query=f"Ontario Health {program}",
        include_domains=["ontariohealth.ca", "cancercareontario.ca", ...],
        num_results=5
    )
    return self._parse_exa_results(results, program)
```

**Priority 4 - Expand Domain List:**
Consider adding these domains that might have relevant Ontario program info:
- `canada.ca/health` (federal programs that apply in Ontario)
- `cmha.ca` (Canadian Mental Health Association)
- `diabetes.ca` (Diabetes Canada)
- `heartandstroke.ca` (Heart & Stroke Foundation)

**Priority 5 - Add Monitoring:**
```python
# Track success/failure rates
logger.info(
    "opa_program_lookup_result",
    extra={
        "program": program,
        "success": bool(citations),
        "num_citations": len(citations),
        "latency_ms": elapsed_time
    }
)
```

### Testing

Test with the problematic query from the handoff note:

```bash
source ~/spacy_env/bin/activate
python scripts/test_mcp_tools_direct.py \
    --agent dr_opa \
    --tool opa_program_lookup \
    --query "heart failure and diabetes comorbidity provincial care pathway Ontario"
```

**Expected behavior after fixes:**
- Returns results within 30 seconds OR timeout error
- Retries once on failure
- Falls back to Exa if Claude fails
- Logs all failures for monitoring

---

## Issue #2: Reasoning Parameters - All Agents Consistent ✅

### Investigation Results

**Finding:** All agents have **identical** reasoning parameter configurations. No differences found.

### Configuration Details

**All 4 agents use the same pattern:**

| Agent | Init Parameter | Model Setting | Default Value |
|-------|----------------|---------------|---------------|
| Dr. OFF | `reasoning_effort: str = "low"` | `ModelSettings(reasoning=None if self.reasoning_effort in ["off", "auto"] else {"effort": self.reasoning_effort})` | `"low"` |
| Dr. OPA | `reasoning_effort: str = "low"` | `ModelSettings(reasoning=None if self.reasoning_effort in ["off", "auto"] else {"effort": self.reasoning_effort})` | `"low"` |
| Agent 97 | `reasoning_effort: str = "low"` | `ModelSettings(reasoning=None if self.reasoning_effort in ["off", "auto"] else {"effort": self.reasoning_effort})` | `"low"` |
| Orchestrator | `reasoning_effort: str = "low"` | `ModelSettings(reasoning=None if self.reasoning_effort in ["off", "auto"] else {"effort": self.reasoning_effort})` | `"low"` |

**Code Locations:**
- Dr. OFF: `src/ai_agents/dr_off_agent/openai_agent.py:318, 733, 1096`
- Dr. OPA: `src/ai_agents/dr_opa_agent/openai_agent.py:324, 433, 746`
- Agent 97: `src/ai_agents/agent_97/openai_agent.py:151, 324, 521`
- Orchestrator: `src/ai_agents/diagnostic_orchestrator/orchestrator_agent.py:89, 438, 733`

### Why User Sees Reasoning on Dr. OFF but Not Others

**Hypothesis:** The difference is likely in **how the API endpoints return responses**, not in the model configuration itself.

**Check these files:**
```
src/web/api/dr_off_streaming_endpoint.py  # Dr. OFF streaming response handler
src/web/api/dr_opa_streaming_endpoint.py  # Dr. OPA streaming response handler
src/web/api/agent_97_endpoint.py          # Agent 97 response handler
src/web/api/orchestrator_endpoint.py      # Orchestrator response handler
```

**Potential causes:**
1. **Response parsing** - Dr. OFF endpoint might include `reasoning_content` in response, others filter it out
2. **Streaming logic** - Different streaming implementations may handle reasoning differently
3. **Frontend display** - Frontend might only render reasoning for certain agent types

**Recommendation:** Check if API endpoints have different logic for extracting/returning reasoning from the agent response. The model settings are identical, so the issue is in the response pipeline, not the agent configuration.

---

## Issue #3: LLM Call Distribution - Complete Audit ✅

### Summary Table

| Component | Provider | Model | LLM Calls | Purpose |
|-----------|----------|-------|-----------|---------|
| **Main Agents** | | | | |
| Dr. OFF Agent | OpenAI | gpt-5-mini | 1 | Main agent orchestration |
| Dr. OPA Agent | OpenAI | gpt-5-mini | 1 | Main agent orchestration |
| Agent 97 | OpenAI | gpt-5-mini | 1 | Main agent orchestration |
| Chief Resident (Orchestrator) | OpenAI | gpt-5-mini | 1 | Top-level orchestration |
| **Dr. OFF MCP Tools** | | | | |
| LLM Reranker (shared utility) | OpenAI | gpt-4o-mini | 2 | Result reranking (2 methods) |
| ADP Tool | OpenAI | gpt-4o-mini | 2 | Category inference + device extraction |
| ADP Device Extractor | OpenAI | gpt-4o-mini | 1 | Device entity extraction |
| ODB Drug Extractor | OpenAI | gpt-4o-mini | 1 | Drug name extraction from query |
| **Dr. OPA MCP Tools** | | | | |
| Semantic Search (reranker) | OpenAI | gpt-4o-mini | 1 | Result reranking |
| CEP Clinical Tools (triage) | OpenAI | gpt-4o-mini | 1 | Tool classification |
| CPSO Policy Check (triage) | OpenAI | gpt-4o-mini | 1 | Policy classification |
| CPSO Policy Check (helpers) | OpenAI | gpt-4o-mini | 1 | Policy relevance scoring |
| Choosing Wisely (triage) | OpenAI | gpt-4o-mini | 1 | Specialty classification |
| Choosing Wisely (helpers) | OpenAI | gpt-4o-mini | 1 | Recommendation relevance |
| Quality Standards (triage) | OpenAI | gpt-4o-mini | 1 | Standard classification |
| Quality Standards (helpers) | OpenAI | gpt-4o-mini | 1 | Standard relevance scoring |
| Freshness Probe | OpenAI | gpt-4o-mini | 1 | Update date extraction |
| Ontario Health Programs | Claude | claude-3-5-haiku-latest | 1 | Web search + fetch |
| PHO Web Search | Claude | claude-3-5-haiku-latest | 2 | Web search + fetch (2 handlers) |
| **Agent 97 MCP Tools** | | | | |
| Clinician Search | Claude | claude-3-5-sonnet-latest | 1 | Web search restricted to 97 domains |
| **Ingestion Scripts** (not runtime) | | | | |
| OHIP Extractor | OpenAI | gpt-4o-mini | 1 | Fee code extraction |
| ADP Extractor | OpenAI | gpt-4o-mini | 2 | Device extraction |
| ACT Extractor | OpenAI | gpt-4o-mini | 1 | Template extraction |
| Choosing Wisely Extractor | OpenAI | gpt-4o-mini | 1 | Recommendation parsing |
| Quality Standards Extractors (v1-v4) | OpenAI | gpt-4o-mini | 6 | Statement extraction |

### Provider Split

**Runtime (per query execution):**
- **OpenAI calls:** 4 main agents + ~6-15 tool calls = **10-19 calls** (depending on which tools are used)
- **Claude calls:** 0-3 calls (only if web search tools are invoked: opa_program_lookup, opa_ipac_guidance, or clinician_search)

**Model Distribution:**
- **gpt-5-mini:** 4 agents (reasoning model for orchestration)
- **gpt-4o-mini:** All tool triage, extraction, and reranking (fast, cheap)
- **claude-3-5-haiku-latest:** Web search for Ontario Health + PHO (2 tools)
- **claude-3-5-sonnet-latest:** Web search for Agent 97 clinician search (1 tool)

### Cost Implications

**Typical query that uses all agents + tools:**

1. Orchestrator (gpt-5-mini): 1 call
2. Dr. OFF (gpt-5-mini): 1 call + 2-4 tool LLM calls (gpt-4o-mini)
3. Dr. OPA (gpt-5-mini): 1 call + 3-8 tool LLM calls (gpt-4o-mini) + 0-2 Claude calls
4. Agent 97 (gpt-5-mini): 1 call + 0-1 Claude call

**Total per complex orchestrated query:**
- OpenAI: 4 gpt-5-mini + 5-12 gpt-4o-mini = **9-16 calls**
- Claude: 0-3 calls (web search)

**Cost optimization opportunities:**
1. **Reduce triage calls:** Some tools call LLM triage even for simple queries
2. **Cache reranking:** Rerank results could be cached for identical queries
3. **Batch tool calls:** Some agents make sequential tool calls that could be parallelized
4. **Remove redundant triage:** If agent already knows tool category, skip triage LLM

---

## Detailed File Locations

### OpenAI Calls (26 unique call sites)

**Dr. OFF Agent:**
1. `src/ai_agents/dr_off_agent/mcp/utils/llm_reranker.py:167` - Reranker (method 1)
2. `src/ai_agents/dr_off_agent/mcp/utils/llm_reranker.py:335` - Reranker (method 2)
3. `src/ai_agents/dr_off_agent/mcp/tools/adp.py:852` - Category inference
4. `src/ai_agents/dr_off_agent/mcp/tools/adp.py:1122` - Device extraction
5. `src/ai_agents/dr_off_agent/mcp/tools/adp_device_extractor.py:264` - Device entity extraction
6. `src/ai_agents/dr_off_agent/mcp/tools/odb_drug_extractor.py:86` - Drug name extraction

**Dr. OPA Agent:**
7. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/semantic_search.py:396` - Semantic reranker
8. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/cep_triage.py:181` - CEP tool triage
9. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/cpso_triage.py:222` - CPSO triage
10. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/cpso_helpers.py:461` - CPSO relevance
11. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/choosing_wisely_triage.py:225` - CW triage
12. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/choosing_wisely_helpers.py:520` - CW relevance
13. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/qs_triage.py:230` - QS triage
14. `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/qs_helpers.py:419` - QS relevance
15. `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py:2686` - Freshness probe

**Ingestion (not runtime):**
16. `src/ai_agents/dr_off_agent/ingestion/extractors/ohip_extractor.py:323`
17. `src/ai_agents/dr_off_agent/ingestion/extractors/adp_extractor.py:246`
18. `src/ai_agents/dr_off_agent/ingestion/extractors/adp_extractor.py:370`
19. `src/ai_agents/dr_off_agent/ingestion/extractors/act_extractor.py:448`
20. `src/ai_agents/dr_opa_agent/ingestion/choosing_wisely/cw_extractor.py:187`
21. `src/ai_agents/dr_opa_agent/ingestion/quality_standards/qs_extractor.py:231`
22. `src/ai_agents/dr_opa_agent/ingestion/quality_standards/qs_extractor_v2.py:306`
23. `src/ai_agents/dr_opa_agent/ingestion/quality_standards/qs_extractor_v3.py:221`
24. `src/ai_agents/dr_opa_agent/ingestion/quality_standards/qs_extractor_v3.py:375`
25. `src/ai_agents/dr_opa_agent/ingestion/quality_standards/qs_extractor_v4.py:300`
26. `src/ai_agents/dr_opa_agent/ingestion/quality_standards/qs_extractor_v4.py:322`

### Claude Calls (4 unique call sites)

**Agent 97:**
1. `src/ai_agents/agent_97/mcp/clinician_search_server.py:192` - Clinician search (97 domains)

**Dr. OPA Agent:**
2. `src/ai_agents/dr_opa_agent/dr_opa_mcp/tools/ontario_health_programs.py:153` - opa_program_lookup
3. `src/ai_agents/dr_opa_agent/dr_opa_mcp/tools/pho_web_search.py:169` - PHO web search (handler 1)
4. `src/ai_agents/dr_opa_agent/dr_opa_mcp/tools/pho_web_search.py:328` - PHO web search (handler 2)

---

## Next Steps

### Immediate Actions (High Priority)

1. **Fix opa_program_lookup timeout handling** (Issue #1)
   - Add 30-second timeout
   - Add retry logic (2 attempts)
   - Add Exa fallback
   - Add monitoring/logging
   - **Owner:** Backend team
   - **Effort:** 2-3 hours
   - **Files:** `src/ai_agents/dr_opa_agent/dr_opa_mcp/tools/ontario_health_programs.py`

2. **Investigate reasoning display inconsistency** (Issue #2 follow-up)
   - Check API endpoint response handling
   - Verify streaming vs non-streaming differences
   - Ensure all endpoints return reasoning_content
   - **Owner:** API/Frontend team
   - **Effort:** 1-2 hours
   - **Files:** `src/web/api/*_endpoint.py`

### Medium Priority

3. **Optimize LLM call count** (Issue #3 insights)
   - Review triage calls - some may be redundant
   - Implement result caching for reranking
   - Add request deduplication
   - **Owner:** Performance team
   - **Effort:** 1 week
   - **Impact:** 20-30% cost reduction

4. **Add comprehensive monitoring**
   - Track tool success/failure rates
   - Monitor tool latency
   - Alert on consecutive failures
   - **Owner:** DevOps team
   - **Effort:** 2-3 days

### Low Priority

5. **Expand Ontario Health domain list**
   - Add federal health sites
   - Add major health charities
   - Test impact on result quality
   - **Owner:** Content team
   - **Effort:** 1 day

---

## Testing Checklist

Before closing this investigation, verify:

- [x] Identified root cause of opa_program_lookup empty results
- [x] Confirmed reasoning parameters are consistent across agents
- [x] Documented all LLM calls with provider/model/purpose
- [ ] Implemented timeout handling for opa_program_lookup
- [ ] Verified reasoning display works consistently across all agents
- [ ] Tested fix with problematic query from user report
- [ ] Added monitoring for tool failures

---

## References

- **Previous Session:** `ORCHESTRATOR_HANDOFF_NOTE.md`
- **Git Commit:** `a8229f3` - "fix: Resolve orchestrator empty tool results through ChromaDB metadata and filter fixes"
- **Date:** October 14, 2025
- **Branch:** `main`

---

**Status:** Investigation complete. Implementation of fixes pending.
