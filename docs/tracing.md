# Langfuse Tracing Documentation

## Overview

The Health Assistant implements comprehensive observability through Langfuse, providing detailed tracing of all LLM interactions, tool usage, and guardrail decisions. This enables monitoring of performance metrics, debugging of issues, and analysis of user interactions.

## Architecture

### Langfuse Integration

Langfuse is integrated at multiple levels:
- **Base Assistant**: Core LLM calls and tool usage
- **Patient Assistant**: Patient-specific guardrails and safety checks  
- **Provider Assistant**: Professional context and clinical references
- **Web API**: Session management and user feedback

### Trace Hierarchy

```
Trace (Session)
├── Generation (LLM Call)
│   ├── Tool Usage (web_search)
│   ├── Tool Usage (web_fetch)
│   └── Metadata (timing, tokens, citations)
├── Span (Guardrail Check - Input)
│   └── LLM Generation (if using LLM guardrails)
└── Span (Guardrail Check - Output)
    └── LLM Generation (if using LLM guardrails)
```

## Implementation Details

### Non-Streaming Tracing

For standard queries, tracing is handled automatically via the `@observe` decorator:

```python
@observe(name="llm_call", as_type="generation", capture_input=True)
def query(self, query: str, ...) -> Dict[str, Any]:
    # Automatic trace creation
    # Input/output captured
    # Metadata logged
```

Key traced data:
- **Input**: Query text, session ID, user ID
- **Output**: Response text, citations, tool calls
- **Metadata**: Model, timing, token counts, guardrail results
- **Usage**: Token consumption for cost tracking

### Streaming Tracing

Streaming presents unique challenges due to Langfuse's limitations with generators. The implementation uses a collection pattern:

```python
def query_stream(self, ...):
    # Collect trace data during streaming
    trace_data = {
        "query": query,
        "mode": self.mode,
        "ttft": None,  # Time to first token
        "full_response": "",
        "citations": [],
        "tool_calls": []
    }
    
    # Stream events
    for event in stream:
        # Update trace_data
        yield event
    
    # Send complete trace after streaming
    self._log_streaming_trace(trace_data)
```

#### Patient Assistant Streaming

```python
# src/assistants/patient.py:408
def query_stream(self, ...):
    # Initialize trace collection
    trace_data = {...}
    
    # Input guardrails (if enabled)
    if self.enable_input_guardrails:
        input_check = self.llm_guardrails.check_input(query, create_span=False)
        trace_data["input_guardrail_result"] = input_check
    
    # Stream response
    for event in super().query_stream(...):
        # Track TTFT
        if event["type"] == "text" and not first_token_received:
            trace_data["ttft"] = time.time() - start_time
        
        # Accumulate response
        trace_data["full_response"] += event.get("content", "")
        yield event
    
    # Log complete trace
    self._log_streaming_trace_to_langfuse(trace_data)
```

#### Provider Assistant Streaming

```python
# src/assistants/provider.py:275
def query_stream(self, ...):
    # Similar pattern to patient, but:
    # - No input guardrails (providers can handle all queries)
    # - Professional context in metadata
    # - Clinical reference tracking
```

### Tool Usage Tracking

Tools are tracked with detailed metadata:

```python
def _tool_meta(name: str, args: dict = None, result=None):
    """Create metadata for tool observations."""
    
    if name == "web_search":
        return {
            "tool_name": "web_search",
            "query": args.get("query"),
            "domains": args.get("domains"),
            "num_results": len(results)
        }
    
    elif name == "web_fetch":
        return {
            "tool_name": "web_fetch",
            "url": args.get("url"),
            "status": result.get("status"),
            "bytes": len(result.get("body", "")),
            "cache": result.get("cache")
        }
```

## Trace Grouping

### By Assistant Mode

Traces are grouped by the assistant mode for comparative analysis:

| Mode | Characteristics | Key Metrics |
|------|-----------------|--------------|
| **Patient** | - Input/output guardrails<br>- Emergency detection<br>- Medical disclaimers | - Guardrail triggers<br>- Safety interventions<br>- Citation quality |
| **Provider** | - No input guardrails<br>- Professional language<br>- Clinical context | - Response depth<br>- Reference quality<br>- Technical accuracy |

### By Response Type

| Type | Description | Tracked Metrics |
|------|-------------|-----------------|
| **Streaming** | SSE-based real-time responses | - Time to first token (TTFT)<br>- Streaming duration<br>- Event counts |
| **Non-Streaming** | Traditional JSON responses | - Total latency<br>- Processing time<br>- Complete response |

## Key Metrics

### Performance Metrics

```python
metadata = {
    # Timing
    "time_to_first_token": 0.8,  # Seconds (streaming only)
    "total_time": 18.5,           # End-to-end time
    "llm_latency": 15.2,          # LLM processing time
    
    # Content
    "response_length": 1500,      # Characters
    "citations_count": 3,         # Number of citations
    "tool_calls_count": 2,        # web_search + web_fetch
    
    # Guardrails
    "input_guardrail_triggered": False,
    "output_guardrail_triggered": True,
    "guardrail_mode": "llm",      # llm, regex, or hybrid
    "violations": ["diagnostic_language"]
}
```

### Quality Metrics

```python
quality_metrics = {
    # Citation Quality
    "has_trusted_citations": True,
    "trusted_domain_ratio": 0.8,
    "citation_domains": ["cdc.gov", "mayoclinic.org"],
    
    # Response Quality
    "includes_disclaimer": True,
    "professional_tone": True,
    "evidence_based": True,
    
    # Safety
    "emergency_detected": False,
    "crisis_detected": False,
    "inappropriate_content": False
}
```

## Clinical Agents Tracing (OpenAI Agents SDK)

The emergency triage orchestrator uses OpenAI Agents SDK v0.3.1+ with Langfuse integration for comprehensive tracing of clinical agent interactions.

### Integration Approach

The clinical agents use a direct Langfuse SDK integration rather than OpenTelemetry/Logfire due to compatibility and simplicity:

```python
# src/agents/clinical/orchestrator_streaming.py
from langfuse import Langfuse

# Direct SDK initialization
langfuse_client = Langfuse(
    public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
    secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
    host=os.getenv('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')
)

# Authentication verification
if langfuse_client.auth_check():
    print("✅ Langfuse client authenticated successfully")
```

### Trace Creation for Clinical Assessments

```python
async def run_triage_assessment_streaming(...):
    # Create trace for the entire assessment
    langfuse_trace = langfuse_client.start_span(
        name="emergency-triage-assessment",
        input={
            "patient_data": patient_data,
            "session_id": session_id
        },
        metadata={
            "service": "emergency-triage-orchestrator",
            "agents": ["triageNurse", "registrationClerk", "provider"],
            "streaming": True
        }
    )
    
    # Track agent interactions
    for event in runner_stream:
        if isinstance(event, AgentUpdatedStreamEvent):
            # Log agent state changes
            langfuse_trace.event(
                name=f"agent_{event.agent_name}_updated",
                metadata={"state": event.state}
            )
    
    # Complete trace with decision
    langfuse_trace.end(
        output=triage_decision.dict(),
        metadata={
            "acuity_level": triage_decision.acuity_level,
            "recommended_department": triage_decision.recommended_department
        }
    )
```

### Streaming Integration

The orchestrator provides real-time updates with trace IDs for feedback correlation:

```python
class StreamingUpdate(BaseModel):
    type: str  # "progress", "agent_update", "tool_call", "final"
    agent: Optional[str]  # Which agent is active
    tool: Optional[str]  # Tool being used
    message: Optional[str]  # Update message
    trace_id: Optional[str]  # Langfuse trace ID for feedback
    
# Stream updates with trace ID
yield StreamingUpdate(
    type="agent_update",
    agent="triageNurse",
    message="Assessing symptoms",
    trace_id=langfuse_trace.trace_id
)
```

### Agent-Specific Tracing

Each clinical agent has specialized trace metadata:

| Agent | Traced Data | Key Metrics |
|-------|------------|--------------|
| **Triage Nurse** | - Vital signs analysis<br>- Symptom severity<br>- Chief complaint | - Acuity level<br>- Risk factors<br>- Urgency indicators |
| **Registration Clerk** | - Patient demographics<br>- Insurance verification<br>- Medical history | - Registration completeness<br>- Data quality<br>- Processing time |
| **Provider** | - Clinical assessment<br>- Department routing<br>- Treatment urgency | - Decision accuracy<br>- Department match<br>- Escalation rate |

### Feedback Integration

User feedback on triage assessments is linked via trace ID:

```python
# Frontend captures trace_id from streaming updates
const [traceId, setTraceId] = useState<string | null>(null);

// Submit feedback with trace correlation
await fetch('/api/feedback', {
    method: 'POST',
    body: JSON.stringify({
        traceId: traceId,
        sessionId: sessionId,
        rating: rating,
        comment: comment
    })
});
```

### Environment Setup

```bash
# Required for clinical agents tracing
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://us.cloud.langfuse.com

# OpenAI for agents
OPENAI_API_KEY=your_openai_key

# Optional: Logfire integration (future)
# LOGFIRE_TOKEN=your_logfire_token
```

### Monitoring Clinical Decisions

Key metrics for clinical agent monitoring:

```python
clinical_metrics = {
    # Performance
    "total_assessment_time": 12.5,  # Seconds
    "agents_consulted": 3,          # Number of agents
    "tools_used": ["vital_analysis", "risk_assessment"],
    
    # Clinical Quality
    "acuity_level": 2,              # ESI 1-5
    "confidence_score": 0.92,       # Decision confidence
    "risk_factors_identified": 3,    # Count
    
    # Routing
    "recommended_department": "emergency",
    "alternative_departments": ["urgent_care"],
    "wait_time_estimate": "15-30 minutes"
}
```

### Debugging Agent Orchestration

Common trace patterns to investigate:

1. **Agent Disagreement**
   ```
   Filter: metadata.agent_consensus = false
   Review: Individual agent assessments
   Action: Refine agent prompts or decision logic
   ```

2. **High Acuity Misses**
   ```
   Filter: user_rating < 3 AND metadata.acuity_level > 3
   Review: Symptom assessment accuracy
   Action: Enhance critical symptom detection
   ```

3. **Routing Errors**
   ```
   Filter: metadata.department_changed = true
   Review: Initial vs actual department
   Action: Improve department matching logic
   ```

## User Feedback Integration

User feedback is captured as scores in Langfuse:

```python
# src/web/api/main.py:471
@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    langfuse_client.create_score(
        trace_id=request.traceId,
        name="user-rating",        # 1-5 star rating
        value=float(request.rating),
        comment=request.comment
    )
    
    langfuse_client.create_score(
        trace_id=request.traceId,
        name="user-feedback",      # Thumbs up/down
        value=1.0 if request.thumbsUp else 0.0
    )
```

## Langfuse Dashboard Views

### Recommended Dashboards

1. **Response Time Analysis**
   - Filter: `metadata.streaming = true/false`
   - Metrics: TTFT, total_time, llm_latency
   - Comparison: Patient vs Provider mode

2. **Guardrail Effectiveness**
   - Filter: `metadata.guardrail_mode`
   - Metrics: Trigger rates, violation types
   - Trends: Emergency detection accuracy

3. **Citation Quality**
   - Filter: `metadata.has_trusted_citations`
   - Metrics: Domain distribution, citation counts
   - Analysis: Trusted vs untrusted sources

4. **User Satisfaction**
   - Scores: user-rating, user-feedback
   - Correlation: With response time, citation quality
   - Segmentation: By mode, guardrail triggers

### Custom Filters

```sql
-- High latency streaming responses
metadata.streaming = true AND metadata.time_to_first_token > 2

-- Guardrail interventions
metadata.input_guardrail_triggered = true 
OR metadata.output_guardrail_triggered = true

-- Provider mode with multiple tools
metadata.mode = "provider" 
AND metadata.tool_calls_count > 3

-- Failed responses needing investigation  
metadata.error IS NOT NULL 
OR output LIKE "%error%"
```

## Configuration

### Environment Variables

```bash
# Required for tracing
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com  # Or self-hosted URL

# Optional settings
LANGFUSE_ENABLED=true         # Enable/disable tracing
LANGFUSE_FLUSH_INTERVAL=1     # Seconds between flushes
```

### Settings Configuration

```python
# src/config/settings.py
class Settings(BaseSettings):
    # Langfuse configuration
    langfuse_enabled: bool = True
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
```

## Debugging with Traces

### Finding Specific Issues

1. **Slow Responses**
   ```
   Look for: metadata.total_time > 30
   Check: Tool call counts, web fetch delays
   ```

2. **Guardrail False Positives**
   ```
   Filter: metadata.guardrail_triggered = true
   Review: Original vs modified responses
   Analyze: Violation patterns
   ```

3. **Missing Citations**
   ```
   Filter: metadata.citations_count = 0
   Check: Tool call success, domain filtering
   ```

4. **Streaming Failures**
   ```
   Filter: metadata.streaming = true AND metadata.error IS NOT NULL
   Review: Error messages, incomplete responses
   ```

### Trace Correlation

Traces can be correlated across multiple calls:
- **Session ID**: Links all queries in a session
- **User ID**: Tracks user behavior patterns  
- **Trace ID**: Connects feedback to specific responses
- **Parent Span**: Links guardrail checks to main query

## Best Practices

### 1. Meaningful Observation Names

```python
@observe(name="patient_query_with_guardrails")  # Descriptive
@observe(name="query")  # Too generic
```

### 2. Comprehensive Metadata

```python
# Good: Rich context
metadata = {
    "mode": self.mode,
    "guardrail_mode": self.guardrail_mode,
    "session_id": session_id,
    "message_count": len(message_history)
}

# Bad: Missing context
metadata = {"mode": "patient"}
```

### 3. Error Tracking

```python
try:
    response = await generate()
except Exception as e:
    # Log error to trace
    langfuse.update_current_observation(
        metadata={"error": str(e), "error_type": type(e).__name__}
    )
    raise
```

### 4. Cost Optimization

```python
# Track token usage for cost analysis
usage = {
    "input_tokens": message.usage.input_tokens,
    "output_tokens": message.usage.output_tokens,
    "total_tokens": message.usage.total_tokens,
    "estimated_cost": calculate_cost(usage, model)
}
```

## Performance Considerations

### Trace Batching

Langfuse batches traces for efficiency:
- Default flush interval: 1 second
- Manual flush: `langfuse.flush()`
- Shutdown flush: Automatic on app termination

### Async Operations

```python
# Traces are sent asynchronously
# No impact on response time
# Retries on failure
```

### Storage Limits

- Trace retention: Based on plan (7-90 days)
- Metadata limit: 10KB per trace
- Output truncation: Automatic for large responses

## Future Enhancements

1. **Real-time Monitoring**
   - WebSocket integration for live traces
   - Alert rules for anomalies
   - Performance degradation detection

2. **Advanced Analytics**
   - A/B testing different guardrail modes
   - User cohort analysis
   - Response quality scoring models

3. **Integration Extensions**
   - Grafana dashboards
   - Slack notifications
   - PagerDuty alerts

4. **Enhanced Streaming Support**
   - Progressive trace updates
   - Event-level granularity
   - Streaming-specific metrics