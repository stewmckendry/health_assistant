# Agent 97 Cost Control Fixes - Applied

## Date: 2025-10-13

## Changes Implemented

### 1. Claude Model Change
**File**: `src/ai_agents/agent_97/mcp/clinician_search_server.py:192`

```python
# BEFORE
model=settings.primary_model,  # claude-sonnet-4-20250514

# AFTER
model="claude-3-7-sonnet-20250219",  # Use Claude 3.7 Sonnet
```

**Impact**: Better cost/performance ratio with Claude 3.7

### 2. Reduced Max Tokens
**File**: `src/ai_agents/agent_97/mcp/clinician_search_server.py:193`

```python
# BEFORE
max_tokens=3000

# AFTER
max_tokens=2000
```

**Impact**: 33% reduction in max output tokens, reducing costs

### 3. Reduced Web Search Usage
**File**: `src/ai_agents/agent_97/mcp/clinician_search_server.py:132`

```python
# BEFORE
max_web_search_uses: int = 2

# AFTER
max_web_search_uses: int = 1
```

**Impact**: 50% reduction in web search calls per clinician_search (from 2 to 1)

### 4. Added Max Tool Call Limit
**Files**:
- `src/ai_agents/agent_97/openai_agent.py:325` (get_agent method)
- `src/ai_agents/agent_97/openai_agent.py:523` (query_stream method)

```python
# ADDED
max_tool_uses={"clinician_search": 3}  # Limit to max 3 calls
```

**Impact**: Hard limit prevents excessive retries (18 → 3 max calls)

### 5. Increased MCP Timeout
**File**: `src/ai_agents/agent_97/openai_agent.py:298`

```python
# BEFORE
client_session_timeout_seconds=180.0  # 3 minutes

# AFTER
client_session_timeout_seconds=300.0  # 5 minutes
```

**Impact**: Reduces timeout-induced retries by giving more time for completion

## Expected Cost Reduction

### Before Changes
- **18 calls** to clinician_search per query
- **14 timeouts** causing retries
- Each call: 2 web_search + 5 web_fetch = **7 web tool uses**
- Model: Claude Sonnet 4 @ 3000 max tokens
- **Estimated cost**: $5-10 per query

### After Changes
- **Max 3 calls** to clinician_search per query (hard limit)
- Fewer timeouts (300s timeout vs 180s)
- Each call: 1 web_search + 5 web_fetch = **6 web tool uses** (14% reduction)
- Model: Claude 3.7 Sonnet @ 2000 max tokens
- **Estimated cost**: $0.50-1.50 per query

### Overall Savings
- **83-85% cost reduction** per query
- From 18 × 7 = 126 total web tool uses → 3 × 6 = 18 total web tool uses (86% reduction)

## Files Modified

1. `src/ai_agents/agent_97/mcp/clinician_search_server.py`
   - Line 132: Reduced web_search default from 2 → 1
   - Line 192: Changed model to claude-3-7-sonnet-20250219
   - Line 193: Reduced max_tokens from 3000 → 2000
   - Line 188-189: Updated logging for tool configuration

2. `src/ai_agents/agent_97/openai_agent.py`
   - Line 298: Increased timeout from 180s → 300s
   - Line 325: Added max_tool_uses limit (get_agent method)
   - Line 523: Added max_tool_uses limit (query_stream method)

## Testing Recommendations

1. **Restart the FastAPI server** to load changes
2. **Run a single test query** with Agent 97
3. **Monitor logs** for:
   - Number of clinician_search calls (should be ≤3)
   - Model used (should be claude-3-7-sonnet-20250219)
   - Web tool usage (should be 1 search + 5 fetches per call)
   - Timeouts (should be significantly reduced or zero)
4. **Check response quality** - ensure clinical guidance is still comprehensive
5. **Monitor API costs** - should see 80%+ reduction

## Rollback Plan

If issues arise, revert changes by:
1. `git checkout src/ai_agents/agent_97/mcp/clinician_search_server.py`
2. `git checkout src/ai_agents/agent_97/openai_agent.py`
3. Restart server

## Next Steps

- Monitor first few production queries to validate cost reduction
- If quality suffers, can incrementally increase limits:
  - web_search: 1 → 1.5 average by allowing 2 on retry
  - max_tool_uses: 3 → 4 if needed
  - max_tokens: 2000 → 2500 if responses too short
- Consider adding query caching for repeated questions (future optimization)
