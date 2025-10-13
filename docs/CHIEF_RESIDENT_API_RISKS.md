# Chief Resident API - Risk Analysis & Mitigations

## Executive Summary

The Chief Resident API is functional for batch evaluation workflows, but several risks exist in the current experimental deployment. This document identifies key risks and provides practical mitigations for a research QI project with ~100-1000 queries.

---

## Critical Risks (Address Before Large-Scale Use)

### 1. 🔴 Cold Start / Initialization Failures

**Risk:** MCP servers and agent instances may not be properly initialized on first request after Railway instance restart, causing early queries to fail with `'NoneType' object has no attribute 'mcp_server'`

**Impact:**
- First 1-3 queries in a batch may fail
- Unpredictable failures if Railway restarts during evaluation
- Wasted evaluation time

**Current Evidence:**
- Test query returned initialization error despite `/status` showing "initialized: true"
- Status endpoint checks cached instance, not actual MCP server state

**Mitigation:**

**Option A: Warm-Up Request (Recommended for QI Project)**
```python
def warm_up_api():
    """Send a simple warm-up query to initialize all agents"""
    warmup_query = "What is CPSO?"
    print("Warming up API...")
    result = query_chief_resident(warmup_query, "warmup-001")
    if 'error' in result:
        print(f"⚠️ Warmup failed: {result['error']}")
        print("Retrying in 10 seconds...")
        time.sleep(10)
        result = query_chief_resident(warmup_query, "warmup-002")
    print(f"✅ API warmed up")
    return 'error' not in result

# Use in evaluation script:
if not warm_up_api():
    print("ERROR: API failed to initialize. Aborting.")
    sys.exit(1)

# Now proceed with actual evaluation queries
```

**Option B: Retry Logic with Exponential Backoff**
```python
def query_with_retry(query, session_id, max_retries=3):
    """Query with automatic retry on initialization errors"""
    for attempt in range(max_retries):
        result = query_chief_resident(query, session_id)

        # Check for initialization errors
        if 'error' in result and 'NoneType' in str(result.get('detail', '')):
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            print(f"⚠️ Initialization error, retry {attempt+1}/{max_retries} in {wait_time}s")
            time.sleep(wait_time)
            continue

        return result

    return {"error": "max_retries_exceeded"}
```

**Code Fix (If You Want to Address Root Cause):**
```python
# In orchestrator_endpoint.py, line 50-57
async def get_orchestrator() -> DiagnosticOrchestrator:
    """Get or create the orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        logger.info("Creating new Chief Resident orchestrator instance...")
        _orchestrator_instance = await create_diagnostic_orchestrator()
        logger.info("Chief Resident orchestrator initialized")

    # ADD THIS: Verify MCP servers are actually initialized
    if not hasattr(_orchestrator_instance, 'dr_opa_wrapper') or \
       _orchestrator_instance.dr_opa_wrapper is None:
        logger.warning("Orchestrator exists but wrappers not initialized, re-initializing...")
        await _orchestrator_instance.initialize()

    return _orchestrator_instance
```

---

### 2. 🟡 Rate Limiting (OpenAI API)

**Risk:** OpenAI's o1-mini and GPT-4o models have shared rate limits across all Railway API users. Batch evaluation could hit rate limits.

**Impact:**
- 429 "Too Many Requests" errors
- Failed queries requiring re-runs
- Extended evaluation time

**Current Limits:**
- o1-mini: 500 requests/minute tier (shared)
- gpt-4o: 500 requests/minute tier (shared)
- If multiple evaluations run simultaneously, could saturate

**Mitigation:**

**Sequential Processing with Delays (Recommended)**
```python
# In evaluation script, add configurable delay
DELAY_BETWEEN_REQUESTS = 5  # Start conservative, tune down if needed

for i, query in enumerate(queries):
    result = query_chief_resident(query, f"eval-{i}")
    results.append(result)

    if i < len(queries) - 1:
        time.sleep(DELAY_BETWEEN_REQUESTS)
```

**Rate Limit Error Handling**
```python
def query_with_rate_limit_handling(query, session_id):
    """Handle 429 rate limit errors with backoff"""
    max_retries = 5
    base_wait = 30  # Start with 30 second wait

    for attempt in range(max_retries):
        result = query_chief_resident(query, session_id)

        # Check for rate limit (429 or specific error message)
        if result.get('error') == 'HTTP 429' or 'rate_limit' in str(result).lower():
            wait_time = base_wait * (2 ** attempt)  # 30s, 60s, 120s, 240s, 480s
            print(f"⚠️ Rate limited, waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            continue

        return result

    return {"error": "rate_limit_exceeded_max_retries"}
```

**Coordination Between Evaluators**
- If multiple people are running evaluations, coordinate schedules
- Consider running overnight to avoid contention
- Monitor for 429 errors and adjust delays

---

### 3. 🟡 Timeout Failures (Long Queries)

**Risk:** Complex queries may exceed Railway's timeout limits (~5 minutes), causing 504 Gateway Timeout errors

**Impact:**
- Lost evaluation data for complex questions
- Incomplete dataset coverage

**Current Timeout:**
- Code sets 360s (6 min) timeout
- Railway may enforce shorter limits
- Reasoning models can take 2-5 minutes for complex synthesis

**Mitigation:**

**Appropriate Timeout Configuration**
```python
# Set realistic timeout in requests
TIMEOUT = 360  # 6 minutes

response = requests.post(url, json=payload, timeout=TIMEOUT)
```

**Graceful Timeout Handling**
```python
def query_with_timeout_handling(query, session_id):
    """Handle timeouts gracefully"""
    try:
        result = query_chief_resident(query, session_id)
        return result
    except requests.exceptions.Timeout:
        # Mark as timeout rather than failure
        return {
            "error": "timeout",
            "query": query,
            "session_id": session_id,
            "note": "Query may be too complex or system overloaded"
        }
```

**Query Simplification Strategy**
- If evaluation includes very complex multi-part questions, consider breaking them into simpler queries
- Track which queries timeout and analyze patterns
- May need to exclude extremely complex queries from automated evaluation

---

### 4. 🟢 Memory Leaks / Resource Exhaustion

**Risk:** Long-running evaluations (1000 queries over 50+ hours) could cause Railway instance to run out of memory

**Impact:**
- API crashes mid-evaluation
- Need to restart evaluation from checkpoint

**Current State:**
- In-memory session storage grows unbounded
- No cleanup of old orchestrator instances
- MCP servers stay connected for duration

**Mitigation:**

**Checkpoint/Resume Support**
```python
def save_checkpoint(results, checkpoint_file="checkpoint.json"):
    """Save progress periodically"""
    with open(checkpoint_file, 'w') as f:
        json.dump(results, f, indent=2)

def load_checkpoint(checkpoint_file="checkpoint.json"):
    """Resume from checkpoint"""
    try:
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# In evaluation loop:
results = load_checkpoint()
start_index = len(results)  # Resume from where we left off

for i in range(start_index, len(queries)):
    result = query_chief_resident(queries[i], f"eval-{i}")
    results.append(result)

    # Save every 10 queries
    if i % 10 == 0:
        save_checkpoint(results)
```

**Unique Session IDs Per Query**
- Don't reuse session IDs - this prevents memory buildup in session store
- Use: `f"eval-{timestamp}-{i:04d}"` for each query

**Monitor Railway Metrics**
- Check Railway dashboard for memory usage trends
- If approaching limits, consider breaking into multiple smaller evaluation runs

---

### 5. 🟢 No Authentication / Open Access

**Risk:** API is publicly accessible without authentication. Anyone with the URL can send queries.

**Impact:**
- Potential abuse/DDOS
- Unexpected cost overruns from OpenAI/Anthropic APIs
- Resource contention during evaluation

**Current State:**
- No API keys required
- No per-user rate limiting
- Suitable for short-term research only

**Mitigation:**

**Short-Term (Acceptable for QI Project):**
- Keep Railway URL private (don't commit to public GitHub)
- Run evaluations during off-peak hours
- Monitor Railway logs for unexpected traffic
- Accept the risk for time-limited experiment

**Long-Term (If Continuing Beyond QI Project):**
```python
# Add simple API key authentication
API_KEY_HEADER = "X-API-Key"
VALID_API_KEYS = {
    "researcher-001": "eval",
    "researcher-002": "eval"
}

@app.middleware("http")
async def validate_api_key(request: Request, call_next):
    if request.url.path.startswith("/agents/"):
        api_key = request.headers.get(API_KEY_HEADER)
        if api_key not in VALID_API_KEYS:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"}
            )
    return await call_next(request)
```

---

### 6. 🟢 Data Privacy / PHI Risk

**Risk:** Users might accidentally submit real patient data through the API

**Impact:**
- HIPAA/PHIPA violations
- Privacy breach
- Langfuse traces contain PHI

**Current State:**
- No PHI filtering or detection
- All queries logged to Langfuse
- Session data stored in-memory

**Mitigation:**

**Clear Documentation (Already Done)**
- API docs explicitly state "Do not send real patient data"
- Recommend synthetic/de-identified test cases only

**Evaluation Dataset Review**
- Review all evaluation queries before running
- Ensure no real patient names, MRNs, dates of birth
- Use generic clinical scenarios only

**Example Safe Query:**
```
❌ BAD: "John Smith, MRN 12345, DOB 1950-03-15 presents with chest pain"
✅ GOOD: "65-year-old male with hypertension presents with acute chest pain"
```

**Langfuse Data Retention**
- Accept that traces will be logged
- All traces are in US cloud (Langfuse cloud)
- If truly sensitive, could disable Langfuse tracing (requires code change)

---

## Medium Risks (Acceptable for Experiment)

### 7. 🟡 Inconsistent Responses (Non-Deterministic)

**Risk:** Same query may produce slightly different responses across runs due to:
- Model temperature settings
- Different agent consultation patterns
- Timing variations

**Impact:**
- Evaluation reproducibility issues
- Difficulty comparing across runs
- Statistical significance questions

**Mitigation:**
- Accept variability as inherent to LLM systems
- If testing specific changes, use same evaluation set before/after
- Consider running each query 2-3 times to measure variance
- Focus on major correctness metrics rather than exact text matching

---

### 8. 🟡 Citation Quality / Completeness

**Risk:** Not all relevant citations may be included in responses

**Impact:**
- Difficulty validating responses
- Missing attribution for sources
- May need manual citation lookup

**Mitigation:**
- Use `citations` array in response for programmatic analysis
- Manual spot-checking of high-importance queries
- Focus evaluation on clinical correctness rather than citation completeness

---

### 9. 🟡 Railway Instance Restarts

**Risk:** Railway may restart the instance during long evaluation runs (deployments, scaling, maintenance)

**Impact:**
- Evaluation interruption
- Loss of in-memory sessions (not critical for this use case)
- Need to resume from checkpoint

**Mitigation:**
- Use checkpoint/resume strategy (see #4)
- Monitor Railway deployment logs
- Avoid running during known maintenance windows
- Accept that some restarts may occur

---

## Low Risks (Accept for QI Project)

### 10. 🟢 Cost Overruns (API Costs)

**Risk:** Large evaluation runs could incur significant OpenAI API costs

**Estimated Costs (Conservative):**
- o1-mini: ~$0.02-0.05 per query (input + output + reasoning)
- 100 queries: $2-5
- 1000 queries: $20-50

**Mitigation:**
- Start with small pilot (10-20 queries) to estimate costs
- Monitor OpenAI dashboard for usage
- Set billing alerts
- Risk is acceptable for research project of this scale

---

### 11. 🟢 No Trace/Debug Access for Evaluator

**Risk:** Evaluator won't have access to Langfuse traces for debugging

**Impact:**
- Can't investigate why specific queries failed
- Limited debugging for unexpected responses

**Mitigation:**
- `trace_id` is included in every response
- Evaluator can provide trace IDs to you for investigation
- For systematic issues, you can review traces in Langfuse
- Consider exporting relevant traces to share (Langfuse API)

---

## Recommended Evaluation Workflow

```python
#!/usr/bin/env python3
"""
Production-ready evaluation script with all mitigations
"""
import requests
import json
import time
from datetime import datetime
from typing import List, Dict

API_BASE = "https://healthassistant-production-3613.up.railway.app"
TIMEOUT = 360
DELAY_BETWEEN_REQUESTS = 5
CHECKPOINT_FILE = "eval_checkpoint.json"

def check_health():
    """Check API health"""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=10)
        return r.status_code == 200
    except:
        return False

def warm_up():
    """Warm up the API with a simple query"""
    print("🔥 Warming up API...")
    for attempt in range(3):
        try:
            r = requests.post(
                f"{API_BASE}/agents/orchestrator/query",
                json={"sessionId": "warmup", "query": "What is CPSO?"},
                timeout=60
            )
            if r.status_code == 200:
                data = r.json()
                if 'error' not in data or data.get('agents_consulted'):
                    print("✅ API ready")
                    return True
        except:
            pass
        print(f"   Retry {attempt+1}/3...")
        time.sleep(5)
    print("❌ Warmup failed")
    return False

def query_with_retry(query: str, session_id: str, max_retries=3):
    """Query with retry logic for initialization and rate limit errors"""
    for attempt in range(max_retries):
        try:
            r = requests.post(
                f"{API_BASE}/agents/orchestrator/query",
                json={"sessionId": session_id, "query": query, "userId": "qip-eval"},
                timeout=TIMEOUT
            )

            result = r.json() if r.status_code == 200 else {"error": f"HTTP {r.status_code}"}

            # Handle rate limits
            if result.get('error') == 'HTTP 429':
                wait = 60 * (2 ** attempt)
                print(f"   ⚠️ Rate limited, wait {wait}s...")
                time.sleep(wait)
                continue

            # Handle initialization errors
            if 'NoneType' in str(result):
                wait = 5 * (attempt + 1)
                print(f"   ⚠️ Init error, retry in {wait}s...")
                time.sleep(wait)
                continue

            return result

        except requests.exceptions.Timeout:
            return {"error": "timeout", "query": query}
        except Exception as e:
            return {"error": str(e)}

    return {"error": "max_retries_exceeded"}

def load_checkpoint():
    """Load previous progress"""
    try:
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_checkpoint(results):
    """Save progress"""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(results, f, indent=2)

def run_evaluation(queries: List[str]):
    """Run full evaluation with all mitigations"""

    # Preflight checks
    print("="*60)
    print("CHIEF RESIDENT EVALUATION")
    print("="*60)
    print(f"Total queries: {len(queries)}")
    print(f"Estimated time: {len(queries) * 2.5 / 60:.1f} hours")
    print()

    if not check_health():
        print("❌ API health check failed")
        return

    if not warm_up():
        print("❌ API warmup failed")
        return

    # Load checkpoint
    results = load_checkpoint()
    start_idx = len(results)

    if start_idx > 0:
        print(f"📂 Resuming from checkpoint (completed {start_idx}/{len(queries)})")

    # Process queries
    for i in range(start_idx, len(queries)):
        print(f"\n[{i+1}/{len(queries)}] Query: {queries[i][:80]}...")

        session_id = f"eval-{datetime.now().strftime('%Y%m%d')}-{i:04d}"
        start = time.time()

        result = query_with_retry(queries[i], session_id)
        elapsed = time.time() - start

        result.update({
            "query": queries[i],
            "query_index": i,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "elapsed_time": elapsed
        })

        results.append(result)

        # Status
        if 'error' in result:
            print(f"   ❌ {result['error']} ({elapsed:.1f}s)")
        else:
            agents = len(result.get('agents_consulted', []))
            chars = len(result.get('response', ''))
            print(f"   ✅ {agents} agents, {chars} chars ({elapsed:.1f}s)")

        # Save checkpoint every 10 queries
        if (i + 1) % 10 == 0:
            save_checkpoint(results)
            print(f"   💾 Checkpoint saved")

        # Delay
        if i < len(queries) - 1:
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Final save
    save_checkpoint(results)

    # Summary
    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    success = sum(1 for r in results if 'error' not in r)
    print(f"Successful: {success}/{len(queries)} ({success/len(queries)*100:.1f}%)")
    print(f"Results: {CHECKPOINT_FILE}")

if __name__ == "__main__":
    # Load your evaluation queries here
    queries = [
        "What are the CPSO requirements for informed consent?",
        # ... add your queries
    ]

    run_evaluation(queries)
```

---

## Summary Recommendations

### For 100-Query QI Project: ✅ GO AHEAD

**Must Do:**
1. Implement warm-up request before batch
2. Add retry logic for initialization errors
3. Use 3-5 second delays between requests
4. Implement checkpoint/resume for long runs

**Should Do:**
5. Review evaluation dataset for PHI
6. Start with 10-query pilot to estimate timing/costs
7. Monitor for rate limit errors

**Nice to Have:**
8. Rate limit exponential backoff
9. Coordinate with other users on timing

**Accept These Risks:**
- Some query variability (non-deterministic)
- Occasional timeouts on very complex queries
- Manual debugging via trace IDs
- ~$2-5 in API costs

### For 1000-Query Evaluation: ⚠️ NEEDS MORE PREP

All above, plus:
- Mandatory checkpoint/resume implementation
- Consider breaking into multiple runs
- Monitor Railway memory usage
- Expect 30-50 hour runtime
- Budget $20-50 for API costs

---

## If Things Go Wrong

### "Most queries are failing"
→ Check Railway logs, verify instance didn't restart, re-run warmup

### "Getting lots of 429 errors"
→ Increase `DELAY_BETWEEN_REQUESTS` to 10-15 seconds

### "Evaluation taking way longer than expected"
→ Check if reasoning model is being used (o1-mini), expect 2-3 min per query

### "Railway instance crashed"
→ Resume from checkpoint, contact maintainer if persistent

### "Need to debug a specific query"
→ Provide `trace_id` from response, maintainer can review in Langfuse
