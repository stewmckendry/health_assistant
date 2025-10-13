# Chief Resident API Documentation

## Overview

The Chief Resident API provides programmatic access to an intelligent medical orchestrator that coordinates between three specialized AI agents to provide comprehensive Ontario-specific clinical decision support:

- **Dr. OPA**: Ontario Practice Advice (CPSO policies, clinical pathways, quality standards)
- **Dr. OFF**: Ontario Finance & Formulary (OHIP billing, ODB drug coverage, ADP devices)
- **Agent 97**: Evidence-based clinical guidance from 97 trusted medical sources

This API is designed for automated evaluation workflows, allowing researchers to test the system against large datasets of clinical questions.

## Base URL

**Production (Railway):**
```
https://healthassistant-production-3613.up.railway.app
```

**Local Development:**
```
http://localhost:8000
```

## Authentication

Currently, no authentication is required. This is an experimental deployment for research purposes.

⚠️ **Note**: Do not send any real patient data or PHI through this API.

---

## Endpoints

### 1. Query Chief Resident (Non-Streaming)

Submit a clinical query and receive a comprehensive synthesized response.

**Endpoint:** `POST /agents/orchestrator/query`

**Request Body:**
```json
{
  "sessionId": "string (required)",
  "query": "string (required)",
  "userId": "string (optional)"
}
```

**Parameters:**
- `sessionId`: Unique identifier for the conversation session. Use a unique ID for each evaluation run or reuse for multi-turn conversations.
- `query`: The clinical question or scenario to evaluate.
- `userId`: Optional identifier for tracking purposes.

**Example Request:**
```bash
curl -X POST https://healthassistant-production-3613.up.railway.app/agents/orchestrator/query \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "eval-001",
    "query": "What are the CPSO documentation requirements for treating a 65-year-old diabetic patient with metformin?",
    "userId": "researcher-001"
  }'
```

**Response:**
```json
{
  "response": "string (markdown formatted clinical guidance)",
  "agents_consulted": ["Dr. OPA", "Dr. OFF", "Agent 97"],
  "citations": ["array of citation URLs/strings"],
  "confidence": 0.9,
  "orchestrator": "Chief",
  "trace_id": "string (Langfuse trace ID)",
  "model": "gpt-4o",
  "sessionId": "eval-001",
  "timestamp": "2025-10-12T14:30:00.000Z"
}
```

**Response Fields:**
- `response`: Complete clinical guidance in markdown format with embedded citations
- `agents_consulted`: List of specialist agents that were consulted
- `citations`: Array of source URLs and references used
- `confidence`: Confidence score (typically 0.9 for multi-agent synthesis)
- `orchestrator`: Always "Chief" for this endpoint
- `trace_id`: Langfuse trace ID for debugging and analytics
- `model`: AI model used (currently "gpt-4o" or "o1-mini" for reasoning)
- `sessionId`: Echo of the session ID from request
- `timestamp`: ISO 8601 timestamp

---

### 2. Health Check

Verify the API is running and ready to accept requests.

**Endpoint:** `GET /health`

**Example Request:**
```bash
curl https://healthassistant-production-3613.up.railway.app/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-12T14:30:00.000Z"
}
```

---

### 3. Orchestrator Status

Check the status of Chief Resident and its available sub-agents.

**Endpoint:** `GET /agents/orchestrator/status`

**Example Request:**
```bash
curl https://healthassistant-production-3613.up.railway.app/agents/orchestrator/status
```

**Response:**
```json
{
  "orchestrator": "Chief Resident - Ontario Healthcare Coordinator",
  "description": "Coordinates Ontario-specific guidance from Dr. OPA (regulations), Dr. OFF (coverage), and Agent 97 (clinical evidence)",
  "status": "ready",
  "initialized": true,
  "available_agents": [
    {
      "name": "Dr. OPA",
      "description": "Ontario Practice Advice - CPSO policies, clinical pathways",
      "status": "available"
    },
    {
      "name": "Dr. OFF",
      "description": "Ontario Finance & Formulary - OHIP billing, ODB coverage",
      "status": "available"
    },
    {
      "name": "Agent 97",
      "description": "Medical education from 97 trusted sources",
      "status": "available"
    }
  ],
  "capabilities": [
    "Intelligent query routing to specialist agents",
    "Multi-agent consultation and synthesis",
    "Session-based conversation continuity",
    "Real-time streaming responses",
    "Citation aggregation and deduplication"
  ],
  "model": "gpt-4o",
  "timestamp": "2025-10-12T14:30:00.000Z"
}
```

---

## Important Considerations

### ⏱️ Response Latency

**Expected Response Time: 30 seconds to 5 minutes per query**

Chief Resident uses reasoning-enabled models (o1-mini) that are trained to think deeply before responding. The system:
- Consults multiple specialist agents in parallel when possible
- Each agent performs MCP tool lookups against Ontario healthcare databases
- The orchestrator synthesizes responses with careful reasoning
- Longer, more complex queries may take up to 5 minutes

**For batch evaluation:**
- Plan for 2-3 minutes average per query
- For 100 queries: ~3-5 hours total runtime
- For 1000 queries: ~30-50 hours total runtime
- Consider running evaluations overnight or over weekends

### 🚦 Rate Limits

**External API Dependencies:**
- **OpenAI API**: 500 requests/minute (o1-mini tier) - shared across all users
- **Anthropic API**: 50 requests/minute (for fallback/other agents)
- **MCP Tools**: No explicit limits but hosted on Railway with resource constraints

**Recommended Approach:**
- **Sequential processing**: Send one request at a time, wait for completion
- **Add delays**: Include 2-5 second delays between requests to be respectful
- **Retry logic**: Implement exponential backoff for 429 (rate limit) errors
- **Monitor failures**: Log any 500 errors or timeouts for investigation

**Example Python Script Pattern:**
```python
import time
import requests

def evaluate_query(query, session_id):
    url = "https://healthassistant-production-3613.up.railway.app/agents/orchestrator/query"
    payload = {
        "sessionId": session_id,
        "query": query,
        "userId": "eval-script"
    }

    try:
        response = requests.post(url, json=payload, timeout=360)  # 6 min timeout
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "timeout"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Process queries sequentially with delays
results = []
for i, query in enumerate(test_queries):
    print(f"Processing query {i+1}/{len(test_queries)}...")
    result = evaluate_query(query, f"eval-{i}")
    results.append(result)

    # Wait between requests
    if i < len(test_queries) - 1:
        time.sleep(3)  # 3 second delay between queries
```

### 💾 Session Management

**Session IDs:**
- Use unique session IDs for independent evaluations
- Reuse session IDs for multi-turn conversations
- Sessions are stored in-memory and will reset on server restart
- No session cleanup/expiration currently implemented

**Best Practice:**
- For single-query evaluation: Use unique session ID per query (`eval-001`, `eval-002`, etc.)
- For conversation testing: Reuse session ID across related queries

### 🔒 Security & Privacy

**Current State (Experimental):**
- ✅ No authentication required
- ✅ HTTPS encryption in transit
- ❌ No rate limiting per user
- ❌ No request logging/audit trail
- ❌ No PHI/PII filtering

**Safe Usage:**
- Use synthetic/de-identified test cases only
- Do not submit real patient data
- Do not include names, MRNs, or other identifiers
- Suitable for clinical scenarios and medical knowledge testing

### 🐛 Error Handling

**Common Errors:**

**500 Internal Server Error:**
- Cause: Orchestrator initialization failure, MCP tool errors, OpenAI API errors
- Action: Check `/agents/orchestrator/status` endpoint, retry after delay

**504 Gateway Timeout:**
- Cause: Query took longer than Railway's timeout (typically 5 minutes)
- Action: Simplify query or retry with different session ID

**429 Too Many Requests:**
- Cause: OpenAI rate limit exceeded
- Action: Implement exponential backoff (wait 60s, then retry)

**Example Error Response:**
```json
{
  "detail": "Error message describing the failure"
}
```

### 📊 Response Quality

**What to expect:**
- High-quality synthesized responses with citations
- Ontario-specific guidance when applicable
- Evidence-based clinical recommendations
- May include lengthy responses (500-2000 words) for complex queries

**Limitations:**
- Not a diagnostic tool - educational purposes only
- May occasionally miss relevant sources
- Citations may not always be comprehensive
- Reasoning process is hidden from API response (visible in Langfuse traces)

### 🔍 Monitoring & Debugging

**Langfuse Integration:**
- Every query generates a `trace_id` in the response
- Traces are logged to Langfuse for observability
- Access to traces requires Langfuse credentials (contact maintainer)
- Traces include: reasoning steps, agent consultations, tool calls, timing

**Useful for:**
- Understanding why a particular response was generated
- Debugging failures or unexpected outputs
- Analyzing agent consultation patterns
- Performance optimization

---

## Complete Example: Batch Evaluation Script

```python
#!/usr/bin/env python3
"""
Example script for batch evaluation of Chief Resident API
"""
import requests
import json
import time
from datetime import datetime
from typing import List, Dict

API_BASE = "https://healthassistant-production-3613.up.railway.app"
TIMEOUT = 360  # 6 minutes
DELAY_BETWEEN_REQUESTS = 3  # seconds

def check_api_health() -> bool:
    """Verify API is healthy before starting evaluation"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        return response.status_code == 200
    except:
        return False

def query_chief_resident(query: str, session_id: str) -> Dict:
    """Send a query to Chief Resident and return the response"""
    url = f"{API_BASE}/agents/orchestrator/query"
    payload = {
        "sessionId": session_id,
        "query": query,
        "userId": "batch-eval"
    }

    try:
        start_time = time.time()
        response = requests.post(url, json=payload, timeout=TIMEOUT)
        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            result['elapsed_time'] = elapsed
            return result
        else:
            return {
                "error": f"HTTP {response.status_code}",
                "detail": response.text,
                "elapsed_time": elapsed
            }
    except requests.exceptions.Timeout:
        return {"error": "timeout", "elapsed_time": TIMEOUT}
    except Exception as e:
        return {"error": str(e)}

def run_evaluation(queries: List[str], output_file: str):
    """Run evaluation on a list of queries"""

    # Check API health
    print("Checking API health...")
    if not check_api_health():
        print("ERROR: API health check failed. Aborting.")
        return
    print("API is healthy. Starting evaluation.\n")

    results = []
    total_queries = len(queries)

    for i, query in enumerate(queries, 1):
        print(f"[{i}/{total_queries}] Processing query...")
        print(f"Query: {query[:100]}...")

        session_id = f"eval-{datetime.now().strftime('%Y%m%d')}-{i:04d}"
        result = query_chief_resident(query, session_id)

        # Add metadata
        result['query_index'] = i
        result['query'] = query
        result['session_id'] = session_id
        result['timestamp'] = datetime.now().isoformat()

        results.append(result)

        # Print summary
        if 'error' in result:
            print(f"❌ ERROR: {result['error']}")
        else:
            agents = result.get('agents_consulted', [])
            response_length = len(result.get('response', ''))
            print(f"✅ SUCCESS: {len(agents)} agents, {response_length} chars, "
                  f"{result.get('elapsed_time', 0):.1f}s")

        # Save intermediate results
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        # Delay before next request
        if i < total_queries:
            print(f"Waiting {DELAY_BETWEEN_REQUESTS}s before next query...\n")
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Print summary
    print("\n" + "="*60)
    print("EVALUATION COMPLETE")
    print("="*60)
    successful = sum(1 for r in results if 'error' not in r)
    print(f"Total queries: {total_queries}")
    print(f"Successful: {successful}")
    print(f"Failed: {total_queries - successful}")
    print(f"Results saved to: {output_file}")

# Example usage
if __name__ == "__main__":
    test_queries = [
        "What are the CPSO requirements for informed consent in Ontario?",
        "What OHIP codes should I use for a new patient comprehensive assessment?",
        "What are the evidence-based guidelines for managing type 2 diabetes in elderly patients?",
        # Add more queries here
    ]

    run_evaluation(test_queries, "chief_resident_eval_results.json")
```

---

## Support & Questions

This is an experimental API for research purposes. For questions or issues:

1. Check the `/agents/orchestrator/status` endpoint for system health
2. Review error messages and adjust queries accordingly
3. For persistent issues, contact the maintainer with:
   - The query that failed
   - Session ID
   - Trace ID (if available)
   - Error message

**Deployment Platform:** Railway
**Expected Uptime:** Best-effort (experimental research deployment)
**Data Retention:** In-memory sessions only, no persistent storage
