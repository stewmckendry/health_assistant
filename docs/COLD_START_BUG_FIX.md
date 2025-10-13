# Cold Start Bug Fix - Chief Resident API

## Summary

**Fixed**: Critical initialization bug causing all API queries to fail with `'NoneType' object has no attribute 'mcp_server'`

**Root Cause**: HTTP orchestrator's `initialize()` method was incomplete:
1. Missing Agent 97 initialization
2. Missing `initialize_mcp_tools()` calls for all agents
3. No defensive checks in endpoint

## Changes Made

### 1. Fixed `orchestrator_agent_http.py` - Complete Agent Initialization

**File**: `src/ai_agents/diagnostic_orchestrator/orchestrator_agent_http.py`

**Before** (Lines 52-63):
```python
async def initialize(self):
    """Initialize the orchestrator with HTTP-aware sub-agents"""
    self.session_logger.info("Initializing Clinical Intelligence Orchestrator with HTTP support")

    # Initialize sub-agents with HTTP support
    self.dr_opa_wrapper = DrOpaAgent(session_id=self.session_id)
    self.dr_off_wrapper = DrOffAgent(session_id=self.session_id)

    # Agent 97 doesn't need MCP servers directly
    # It uses the patient assistant which has its own web search

    self.session_logger.info("Sub-agents initialized with HTTP MCP support")
```

**After**:
```python
async def initialize(self):
    """Initialize the orchestrator with HTTP-aware sub-agents"""
    self.session_logger.info("Initializing Clinical Intelligence Orchestrator with HTTP support")

    try:
        # Initialize Dr. OPA wrapper with HTTP support - disable Langfuse to avoid conflicts
        self.dr_opa_wrapper = DrOpaAgent(session_id=self.session_id, enable_langfuse=False)
        await self.dr_opa_wrapper.initialize_mcp_tools()
        self.session_logger.info("Dr. OPA wrapper initialized with HTTP MCP (Langfuse disabled for sub-agent)")

        # Initialize Dr. OFF wrapper with HTTP support - disable Langfuse to avoid conflicts
        self.dr_off_wrapper = DrOffAgent(session_id=self.session_id, enable_langfuse=False)
        await self.dr_off_wrapper.initialize_mcp_tools()
        self.session_logger.info("Dr. OFF wrapper initialized with HTTP MCP (Langfuse disabled for sub-agent)")

        # Initialize Agent 97 wrapper - disable Langfuse to avoid conflicts
        from src.ai_agents.agent_97.openai_agent import Agent97Agent
        self.agent_97_wrapper = Agent97Agent(enable_langfuse=False)
        await self.agent_97_wrapper.initialize_mcp_tools()
        self.session_logger.info("Agent 97 wrapper initialized (Langfuse disabled for sub-agent)")

        self.session_logger.info("All agent wrappers initialized successfully with HTTP MCP support")

    except Exception as e:
        self.session_logger.error(f"Error initializing agent wrappers: {e}")
        raise
```

**Changes**:
- ✅ Added Agent 97 initialization (was missing entirely)
- ✅ Added `await initialize_mcp_tools()` calls for all three agents
- ✅ Added Langfuse disable flag for sub-agents (avoid conflicts)
- ✅ Added try/except for better error handling
- ✅ Added detailed logging for each agent

---

### 2. Added Defensive Checks in `orchestrator_endpoint.py`

**File**: `src/web/api/orchestrator_endpoint.py`

**Before** (Lines 50-57):
```python
async def get_orchestrator() -> DiagnosticOrchestrator:
    """Get or create the orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        logger.info("Creating new Chief Resident orchestrator instance...")
        _orchestrator_instance = await create_diagnostic_orchestrator()
        logger.info("Chief Resident orchestrator initialized")
    return _orchestrator_instance
```

**After**:
```python
async def get_orchestrator() -> DiagnosticOrchestrator:
    """Get or create the orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        logger.info("Creating new Chief Resident orchestrator instance...")
        _orchestrator_instance = await create_diagnostic_orchestrator()
        logger.info("Chief Resident orchestrator initialized")
    else:
        # Verify that the wrappers are actually initialized (defensive check)
        if (_orchestrator_instance.dr_opa_wrapper is None or
            _orchestrator_instance.dr_off_wrapper is None or
            _orchestrator_instance.agent_97_wrapper is None):
            logger.warning("Orchestrator exists but wrappers are None, re-initializing...")
            await _orchestrator_instance.initialize()
            logger.info("Chief Resident orchestrator wrappers re-initialized")
    return _orchestrator_instance
```

**Changes**:
- ✅ Added defensive check to verify all wrappers are not None
- ✅ Auto-recovery: re-initializes wrappers if they're None
- ✅ Logging for debugging

---

## Deployment Instructions

### Step 1: Commit Changes

```bash
cd /Users/liammckendry/health_assistant

git add src/ai_agents/diagnostic_orchestrator/orchestrator_agent_http.py
git add src/web/api/orchestrator_endpoint.py

git commit -m "fix: Initialize all agent wrappers and add defensive checks for cold start bug

- Add Agent 97 initialization (was missing in HTTP orchestrator)
- Call initialize_mcp_tools() on all three sub-agents
- Add defensive checks in endpoint to auto-recover from uninitialized wrappers
- Disable Langfuse for sub-agents to avoid conflicts
- Add comprehensive error handling and logging

Fixes 'NoneType' object has no attribute 'mcp_server' error"
```

### Step 2: Push to GitHub

```bash
git push origin main
```

### Step 3: Deploy to Railway

Railway should auto-deploy when you push to `main`. If not:

1. Go to Railway dashboard: https://railway.app
2. Find the `health_assistant` project
3. Click on the service
4. Click "Deploy" → "Redeploy"

### Step 4: Wait for Deployment

- Railway typically takes 3-5 minutes to rebuild and deploy
- Watch the deployment logs for any errors
- Look for log lines:
  - `"Dr. OPA wrapper initialized with HTTP MCP"`
  - `"Dr. OFF wrapper initialized with HTTP MCP"`
  - `"Agent 97 wrapper initialized"`
  - `"All agent wrappers initialized successfully"`

### Step 5: Test the Fix

After deployment completes, test the API:

```bash
# Test 1: Health check
curl https://healthassistant-production-3613.up.railway.app/health

# Test 2: Orchestrator status
curl https://healthassistant-production-3613.up.railway.app/agents/orchestrator/status

# Test 3: Simple query (should now work!)
curl -X POST https://healthassistant-production-3613.up.railway.app/agents/orchestrator/query \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-fix-001",
    "query": "What is CPSO?",
    "userId": "test"
  }' \
  --max-time 180
```

**Expected**: Should return a proper response with `agents_consulted` array containing agent names, not an error message.

---

## Verification Checklist

After deployment, verify:

- [ ] Health endpoint returns `{"status": "healthy"}`
- [ ] Status endpoint returns `"initialized": true`
- [ ] Query endpoint returns successful response (not error message)
- [ ] Response includes `"agents_consulted": ["Dr. OPA", "Dr. OFF", "Agent 97"]` or similar
- [ ] Response includes `"orchestrator": "Chief"`
- [ ] Response includes `"trace_id"` for Langfuse
- [ ] No `'NoneType' object has no attribute 'mcp_server'` errors

---

## What This Fixes

### Before (Broken):
```json
{
  "response": "I apologize, but the Medical Diagnostic Orchestrator is experiencing technical difficulties...",
  "agents_consulted": [],
  "confidence": 0.0,
  "error": "'NoneType' object has no attribute 'mcp_server'"
}
```

### After (Working):
```json
{
  "response": "CPSO stands for the College of Physicians and Surgeons of Ontario...",
  "agents_consulted": ["Dr. OPA", "Agent 97"],
  "citations": ["https://www.cpso.on.ca/..."],
  "confidence": 0.9,
  "orchestrator": "Chief",
  "trace_id": "abc123...",
  "model": "gpt-4o"
}
```

---

## Impact on Evaluation Workflow

### Before Fix:
- ❌ All queries failed
- ❌ No agents consulted
- ❌ Evaluation impossible

### After Fix:
- ✅ Queries succeed
- ✅ All three agents can be consulted
- ✅ Evaluation can proceed
- ⚠️ Still need warm-up request and retry logic (best practice)
- ⚠️ Still need rate limit handling (separate issue)

---

## Technical Details

### Why Agent 97 Was Missing

The HTTP orchestrator had this comment:
```python
# Agent 97 doesn't need MCP servers directly
# It uses the patient assistant which has its own web search
```

This was incorrect reasoning. While Agent 97 doesn't have HTTP MCP servers (it uses web search directly), it still needs to be instantiated as an object. The orchestrator calls `agent_97_tool = agent_97_agent.as_tool(...)` which requires `self.agent_97_wrapper` to exist and be an Agent object, not None.

### Why initialize_mcp_tools() Was Missing

The HTTP agent constructors (`DrOpaAgentHTTP.__init__`) initialize their MCP servers via `_initialize_http_mcp_server()`, but the `initialize_mcp_tools()` method still needs to be called for:
1. Logging purposes
2. Consistency with the base orchestrator pattern
3. Future expansion (if tools need async setup)

While the current `initialize_mcp_tools()` is mostly a logging no-op, calling it maintains consistency and ensures any future initialization logic will be executed.

---

## Monitoring

After deployment, monitor:

1. **Railway Logs**: Look for initialization success messages
2. **Langfuse Traces**: Verify traces are being created with proper agent consultations
3. **Error Rates**: Should drop to near-zero for initialization errors
4. **Response Times**: Should see proper 30s-3min response times (not instant failures)

---

## Follow-Up Tasks

After this fix is deployed and verified:

1. **Update API Documentation**: Remove cold-start bug from critical risks
2. **Simplify Evaluation Script**: Can remove some defensive retry logic
3. **Test Multi-Agent Queries**: Verify complex queries consult all three agents
4. **Monitor for New Issues**: Watch for other edge cases

---

## Rollback Plan

If this causes new issues:

```bash
git revert HEAD
git push origin main
```

Railway will auto-deploy the previous version. The old behavior (all queries failing) will return.

---

## Questions?

If the fix doesn't work after deployment:

1. Check Railway deployment logs for errors
2. Verify environment variables are set (OPENAI_API_KEY, etc.)
3. Check if MCP HTTP servers are running on ports 8002, 8003
4. Provide Railway logs for debugging
