# Proposed Fixes for Agent 97 Excessive API Costs

## Problem Summary
Agent 97 is making 18+ calls to clinician_search tool in a single query, with each call:
- Using Claude Sonnet 4 (expensive model)
- Making 2 web searches + 5 web fetches (7 tool uses per call)
- Timing out after 180s and retrying
- Burning through API credits rapidly

## Root Causes

1. **System instructions say "Use clinician_search for ALL clinical questions"** - forces tool use every time
2. **gpt-5-mini reasoning model retries failed calls** - 14 timeouts out of 18 attempts
3. **Claude API using expensive Sonnet 4 model** with 3000 max_tokens
4. **180s timeout too short** for complex searches with 2 searches + 5 fetches
5. **No limits on Agent 97 tool calls** - it keeps retrying

## Proposed Fixes (In Priority Order)

### 🔥 CRITICAL - Immediate Cost Reduction

#### Fix 1: Reduce Claude API Cost in clinician_search Tool
**File**: `src/ai_agents/agent_97/mcp/clinician_search_server.py`

```python
# Line 192-194: Use cheaper model and lower token limit
response = client.messages.create(
    model="claude-3-5-haiku-20241022",  # CHANGE: Use Haiku instead of Sonnet 4 (20x cheaper)
    max_tokens=1500,                     # CHANGE: Reduce from 3000 to 1500 (50% savings)
    temperature=0.3,                     # Keep same
    ...
```

**Impact**: ~40x cost reduction per clinician_search call
- Sonnet 4: $3/$15 per MTok → Haiku: $0.25/$1.25 per MTok
- Lower max_tokens reduces output costs

#### Fix 2: Reduce Web Tool Usage Limits
**File**: `src/ai_agents/agent_97/mcp/clinician_search_server.py`

```python
# Line 132-133: Lower default limits
max_web_search_uses: int = 1,  # CHANGE: 2 → 1 (50% reduction)
max_web_fetch_uses: int = 3,   # CHANGE: 5 → 3 (40% reduction)
```

**Impact**: 43% fewer web tool calls per search (from 7 to 4)

#### Fix 3: Limit Agent 97 Tool Calls
**File**: `src/ai_agents/agent_97/openai_agent.py`

Add max_tool_uses to Agent creation:

```python
# Line 319 in get_agent():
from agents import ModelSettings, ToolSettings

return Agent(
    name="Agent 97",
    instructions=self.system_instructions,
    model="gpt-5-mini",
    model_settings=ModelSettings(
        reasoning=None if self.reasoning_effort == "off" else {"summary": self.reasoning_effort},
        tool_settings=ToolSettings(
            max_uses_per_tool={"clinician_search": 3}  # ADD: Limit to 3 attempts max
        )
    ),
    mcp_servers=[mcp_server]
)
```

**Impact**: Hard limit on retries - max 3 calls instead of 18

### ⚡ MODERATE - Improve Reliability

#### Fix 4: Increase MCP Timeout
**File**: `src/ai_agents/agent_97/openai_agent.py`

```python
# Line 298: Increase timeout to match worst case
client_session_timeout_seconds=300.0  # CHANGE: 180 → 300 (5 minutes)
```

**Impact**: Reduces timeout-induced retries

#### Fix 5: Soften System Instructions
**File**: `src/ai_agents/agent_97/openai_agent.py`

```python
# Line 226: Change from mandatory to conditional
WHEN TO USE YOUR TOOL:
- Use clinician_search when you need current evidence-based guidance that requires web search
- If you already have sufficient knowledge to answer, you may respond directly with a brief answer
- For complex clinical questions, use the tool to find authoritative sources
- The tool handles all the complexity of searching and filtering trusted sources
```

**Impact**: Allows Agent 97 to skip tool use for simple questions it can answer directly

### 📊 OPTIONAL - Further Optimization

#### Fix 6: Add Caching for Repeated Queries
Add simple in-memory cache in clinician_search_server.py to avoid re-searching identical queries.

#### Fix 7: Use Prompt Caching
Add anthropic prompt caching headers to reduce input token costs for repeated system prompts.

## Recommended Implementation Order

1. **Deploy Fixes 1-3 immediately** (critical cost reduction)
2. **Deploy Fix 4** (reliability)
3. **Test with single query** to validate cost reduction
4. **Deploy Fix 5** if still seeing excessive calls
5. **Consider Fix 6-7** if needed

## Expected Cost Reduction

**Before**:
- 18 calls × (Sonnet 4 @ 3000 tokens + 7 web tools) = ~$5-10 per query

**After (Fixes 1-3)**:
- 3 calls × (Haiku @ 1500 tokens + 4 web tools) = ~$0.10-0.20 per query

**Savings: 95%+ cost reduction**

## Testing Plan

1. Apply fixes 1-4
2. Run single test query with reasoning_effort="auto"
3. Monitor logs for:
   - Number of clinician_search calls (should be ≤3)
   - Claude model used (should be Haiku)
   - Web tool usage (should be ≤4 per call)
   - Timeouts (should be zero)
4. Check response quality is still good
5. If quality suffers, can increase limits incrementally

## Alternative: Disable Agent 97 Temporarily

If immediate cost control needed:
- Comment out Agent 97 initialization in orchestrator
- Use only Dr. OPA and Dr. OFF (no Claude API costs)
- Re-enable after fixes deployed
