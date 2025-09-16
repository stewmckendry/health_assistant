# Performance Optimization: 30s → 5s Response Time

## 🚀 Ready to Optimize!

Your development environment is set up:
- **GitHub Issue**: #11 - Performance: Optimize query response time (currently 30+ seconds)
- **Branch**: `performance-optimization`
- **Worktree**: `../health_assistant_performance`

## 📍 Current Performance Bottlenecks

From Langfuse trace analysis:
- **Total query time**: 29.35s ❌
- **LLM call**: 22.88s (75% of time)
- **Output guardrail**: 4.83s
- **Multiple web fetches**: Sequential, not timed

## 🎯 Implementation Priority

### 1. Research Anthropic Native Features FIRST
Before building custom solutions, investigate:

```python
# Research these Anthropic SDK features:
from anthropic import AsyncAnthropic

# 1. Parallel tool execution
# Check if Anthropic supports concurrent tool calls natively
# Look for: parallel_tool_use, concurrent_tools, or batch parameters

# 2. Streaming with early termination
# Can we stream and stop after N quality results?
# Look for: stream_tools, tool_choice parameters

# 3. Tool result filtering
# Can Anthropic filter tool results before returning?
# Look for: tool_filters, result_constraints
```

**Research Tasks:**
- [ ] Check Anthropic docs for parallel tool execution
- [ ] Test if multiple web_search/web_fetch can run concurrently
- [ ] Investigate streaming tool results
- [ ] Look for native quality/domain filtering

### 2. Parallelize Web Fetches

**Current Problem**: Sequential fetches taking too long

**Solution Architecture:**
```python
# src/assistants/base.py modifications

async def parallel_web_fetch(self, urls: List[str], max_results: int = 2):
    """
    Fetch multiple URLs concurrently, return first N quality results.
    """
    # Use asyncio.gather or concurrent.futures
    # Stream back results as they complete
    # Stop once we have max_results quality pages
```

**Implementation Steps:**
1. Convert web_fetch to async if needed
2. Use `asyncio.gather()` for concurrent fetches
3. Implement quality check (domain authority)
4. Return first 2 that pass quality threshold
5. Cancel remaining fetches

### 3. Domain Allowlist Enforcement

**Current Problem**: Model might select untrusted links

**Solution Architecture:**
```python
# Enforce at search layer BEFORE model sees results

def enforce_domain_allowlist(search_results):
    """Filter search results to only trusted domains."""
    trusted = settings.trusted_domains
    
    # For patient mode: Use 119 trusted domains
    # For provider mode: Use 169 trusted domains
    
    filtered = [
        result for result in search_results 
        if urlparse(result.url).netloc in trusted
    ]
    return filtered[:2]  # Return max 2 results
```

**Files to Modify:**
- `src/assistants/base.py` - Add domain filtering in `_handle_tool_use()`
- `src/config/domains.yaml` - Already has trusted domains ✓

### 4. Top-N Cap with Authority Ranking

**Strategy**: Fetch at most 2 high-authority pages

**Domain Priority Tiers:**
```python
AUTHORITY_TIERS = {
    'tier_1': [  # Government & WHO - fetch first
        'who.int',
        'cdc.gov',
        'nih.gov',
        'pubmed.ncbi.nlm.nih.gov'
    ],
    'tier_2': [  # Major academic hospitals - fetch if tier_1 < 2
        'mayoclinic.org',
        'clevelandclinic.org',
        'hopkinsmedicine.org'
    ]
}
```

**Implementation:**
1. Rank search results by domain authority
2. Fetch 1 from tier_1 if available
3. Fetch 1 from tier_2 if available
4. Stop at 2 total fetches

### 5. Fast Rule-Based Output Guardrails

**Current Problem**: LLM guardrail check taking 4.83s

**Fast Rules to Implement:**
```python
# src/utils/fast_guardrails.py

class FastGuardrailRules:
    """Deterministic checks before LLM escalation."""
    
    # Regex patterns for instant rejection
    DOSING_PATTERNS = [
        r'\d+\s*mg',
        r'take\s+\d+',
        r'dosage',
        r'prescription'
    ]
    
    DIAGNOSIS_PATTERNS = [
        r'you\s+(have|appear to have|likely have)',
        r'diagnosis\s+is',
        r'this\s+is\s+\w+\s+disease'
    ]
    
    def check_output(self, text: str) -> GuardrailResult:
        """Fast rule-based check, escalate only if needed."""
        
        # Step 1: Fast regex checks (< 1ms)
        if self.has_dosing_language(text):
            return GuardrailResult(block=True, reason="dosing")
            
        if self.has_diagnosis_language(text):
            return GuardrailResult(block=True, reason="diagnosis")
        
        # Step 2: Only call LLM if ambiguous (rare)
        if self.needs_llm_review(text):
            return self.llm_guardrails.check(text)
            
        return GuardrailResult(pass=True)
```

**Escalation Logic:**
- ✅ Clear violations → Block immediately (0ms)
- ✅ Clear safe content → Pass immediately (0ms)
- ⚠️ Ambiguous cases → LLM review (4-5s, rare)

## 📝 Implementation Plan

### Step 1: Research & Test Anthropic Native Features
```bash
cd ../health_assistant_performance

# Create test script
python scripts/test_anthropic_parallel.py
```

Test these scenarios:
1. Can we call multiple tools in parallel natively?
2. Does Anthropic support streaming tool results?
3. Can we set tool constraints/filters?

### Step 2: Implement Domain Filtering
```python
# src/assistants/base.py - modify _handle_tool_use()

if tool_name == "web_search":
    # Filter results BEFORE passing to model
    results = await self.web_search(query)
    filtered = self.enforce_domain_allowlist(results)
    return filtered[:2]  # Max 2 results
```

### Step 3: Parallelize Fetches
```python
# If Anthropic doesn't support native parallel:

import asyncio
from concurrent.futures import ThreadPoolExecutor

async def parallel_fetch(urls: List[str]):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_url, url) for url in urls]
        
        completed = []
        for future in asyncio.as_completed(futures):
            result = await future
            if passes_quality_check(result):
                completed.append(result)
                if len(completed) >= 2:
                    # Cancel remaining
                    break
                    
    return completed
```

### Step 4: Implement Fast Guardrails
```python
# Replace LLMGuardrails with FastGuardrails for output

# src/assistants/patient.py - line 248
if self.guardrail_mode in ["llm", "hybrid"]:
    # Try fast rules first
    fast_check = FastGuardrailRules().check_output(response["content"])
    
    if fast_check.needs_llm_review:
        # Only call LLM if ambiguous
        output_check = self.llm_guardrails.check_output(...)
    else:
        output_check = fast_check
```

## 🧪 Testing Strategy

### Performance Benchmarks
Create `tests/performance/test_response_time.py`:
```python
def test_response_time():
    """Ensure response time < 5 seconds."""
    queries = [
        "What are symptoms of flu?",
        "How to manage diabetes?",
        "Signs of heart attack?"
    ]
    
    for query in queries:
        start = time.time()
        response = assistant.query(query)
        elapsed = time.time() - start
        
        assert elapsed < 5.0, f"Query took {elapsed}s"
```

### Quality Validation
Ensure optimizations don't break safety:
- [ ] All guardrail tests still pass
- [ ] Citations from trusted sources only
- [ ] No medical advice slips through

## 📊 Success Metrics

| Metric | Current | Target | 
|--------|---------|--------|
| Total Response Time | 29.35s | <5s |
| LLM Call | 22.88s | <3s |
| Output Guardrail | 4.83s | <0.1s |
| Web Fetches | Unknown | <2s |
| P95 Response Time | >30s | <8s |

## 🚦 Quick Start Commands

```bash
# 1. Switch to performance worktree
cd ../health_assistant_performance

# 2. Check current model configuration
grep -r "model" src/config/

# 3. Run performance tests
python -m pytest tests/performance/ -v

# 4. Monitor with Langfuse
# Watch traces at https://cloud.langfuse.com

# 5. Test changes locally
python scripts/test_assistant.py -q "What are flu symptoms?" --time
```

## ⚡ Quick Wins Checklist

- [ ] Research Anthropic native parallel tools
- [ ] Implement domain filtering at search layer
- [ ] Limit to 2 high-authority fetches
- [ ] Replace LLM guardrails with fast rules
- [ ] Add 30s timeout to all operations
- [ ] Test with common queries
- [ ] Monitor Langfuse for improvements

## 🎯 Expected Outcome

After implementing these changes:
- **Web fetches**: Parallel, max 2, <2s total
- **Output guardrails**: Fast rules, <100ms
- **Total response**: <5s for 90% of queries
- **User experience**: Snappy, responsive, safe

Good luck optimizing! Focus on native Anthropic features first before building custom solutions. 🚀