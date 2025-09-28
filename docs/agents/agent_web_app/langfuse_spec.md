# Langfuse Tracing Implementation Specification

## Overview
This document describes the Langfuse tracing implementation for Dr. OFF and Dr. OPA agents in the health assistant application. Langfuse provides observability and monitoring for LLM applications, enabling trace collection, user feedback correlation, and performance monitoring.

## Architecture

### Integration Approach
- **Primary Integration**: Logfire instrumentation with OTLP export to Langfuse
- **SDK**: Langfuse Python SDK v3 (OpenTelemetry-based)
- **Agents Framework**: OpenAI Agents SDK with automatic instrumentation

### Components
1. **Logfire**: Provides automatic instrumentation for OpenAI Agents SDK
2. **Langfuse Client**: Handles trace creation, span management, and user feedback
3. **OTLP Exporter**: Sends telemetry data from Logfire to Langfuse

## Implementation Details

### Environment Configuration
```bash
# Required environment variables
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com  # US region

# Optional configuration
LANGFUSE_ENABLED=true  # Enable/disable tracing
```

### Agent Initialization

Both Dr. OFF and Dr. OPA agents follow the same initialization pattern:

```python
class DrOffAgent:
    def __init__(self, enable_langfuse: bool = True):
        self.enable_langfuse = enable_langfuse and LANGFUSE_AVAILABLE
        
        if self.enable_langfuse:
            # Handle uvloop compatibility
            if nest_asyncio:
                import asyncio
                loop = asyncio.get_event_loop()
                if not loop.__class__.__module__.startswith('uvloop'):
                    nest_asyncio.apply()
            
            # Configure Logfire for automatic instrumentation
            logfire.configure(
                service_name='dr_off_agent',
                send_to_logfire=False,  # Only send to Langfuse
            )
            
            # Instrument OpenAI Agents SDK
            logfire.instrument_openai_agents()
            
            # Get Langfuse client for manual operations
            self.langfuse = get_client()
            
            # Verify authentication
            if self.langfuse.auth_check():
                logger.info("Langfuse client authenticated")
            else:
                self.enable_langfuse = False
```

### Trace Creation Pattern

#### Streaming Methods
```python
async def query_stream(self, user_input: str, session_id: str = None, user_id: str = None):
    # Create trace ID and update current trace
    trace_id = self.langfuse.create_trace_id()
    self.langfuse.update_current_trace(
        user_id=user_id,
        session_id=session_id,
        metadata={
            "agent": "dr_off",
            "model": "gpt-4o-mini",
            "trace_id": trace_id
        },
        tags=["dr_off", "streaming"]
    )
    
    # Start a span for the query
    langfuse_span = self.langfuse.start_span(
        name="dr_off_query_stream",
        input={"query": user_input}
    )
    
    # Process query...
    
    # Log tool calls as spans
    for tool_call in tool_calls:
        self.langfuse.start_span(
            name=f"tool_call_{tool_call['name']}",
            input={"arguments": tool_call['arguments']}
        )
    
    # Update span with output
    if langfuse_span:
        langfuse_span.update(
            output={
                "response": accumulated_text,
                "tool_calls": tool_calls,
                "citations": citations
            }
        )
        langfuse_span.end()
```

#### Non-Streaming Methods
```python
async def query(self, user_input: str, session_id: str = None, user_id: str = None):
    # Same trace creation pattern
    trace_id = self.langfuse.create_trace_id()
    self.langfuse.update_current_trace(
        user_id=user_id,
        session_id=session_id,
        metadata={
            "agent": "dr_off",
            "model": "gpt-4o-mini",
            "trace_id": trace_id
        },
        tags=["dr_off", "non-streaming"]
    )
    
    langfuse_span = self.langfuse.start_span(
        name="dr_off_query",
        input={"query": user_input}
    )
    
    # Process query...
    
    # Update and end span
    if langfuse_span:
        langfuse_span.update(
            output={
                "response": result.final_output,
                "tool_calls": tool_calls,
                "citations": citations
            }
        )
        langfuse_span.end()
    
    # Flush events
    self.langfuse.flush()
    
    return {"trace_id": trace_id, ...}
```

## API Endpoints

### Streaming Endpoint
```python
@app.post("/agents/{agent_id}/stream")
async def stream_agent_response(request: StreamRequest):
    # Pass user_id and session_id to agent
    agent = await create_agent()
    
    async for event in agent.query_stream(
        request.query, 
        session_id=request.sessionId,
        user_id=request.userId
    ):
        # Stream events include trace_id in metadata
        if event['type'] == 'complete':
            trace_id = event.get('metadata', {}).get('trace_id')
```

### User Feedback Endpoint
```python
@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    langfuse = get_client()
    
    # Score the trace
    langfuse.score(
        trace_id=request.trace_id,
        name="user_feedback",
        value=request.score,  # 1 (thumbs up) or 0 (thumbs down)
        comment=request.comment,
        user_id=request.user_id
    )
```

## Frontend Integration

### Trace ID Management
```typescript
interface StreamEvent {
  type: 'response_done';
  data: {
    sessionId: string;
    traceId: string;  // Capture for feedback
  };
}

// Store trace ID for feedback
const [currentTraceId, setCurrentTraceId] = useState<string>();

// On stream completion
if (event.type === 'response_done') {
  setCurrentTraceId(event.data.traceId);
}
```

### User Feedback Submission
```typescript
const submitFeedback = async (isPositive: boolean, comment?: string) => {
  await fetch('/api/feedback', {
    method: 'POST',
    body: JSON.stringify({
      trace_id: currentTraceId,
      score: isPositive ? 1 : 0,
      comment,
      user_id: userId
    })
  });
};
```

## Trace Data Structure

### Trace Metadata
- `trace_id`: Unique identifier for the trace
- `user_id`: User identifier for grouping
- `session_id`: Session identifier for conversation tracking
- `agent`: Agent name (dr_off, dr_opa)
- `model`: Model used (gpt-4o-mini)
- `tags`: Classification tags (streaming/non-streaming)

### Span Hierarchy
```
Trace: dr_off_query_stream
├── Span: tool_call_schedule_get
│   └── Input: {query: "eye exam billing code"}
├── Span: tool_call_odb_get  
│   └── Input: {drug: "metformin"}
└── Output: {response, tool_calls, citations}
```

### Tool Call Tracking
Each tool call creates a span with:
- Name: `tool_call_{tool_name}`
- Input: Tool arguments
- Automatic duration tracking

## Error Handling

### Langfuse Initialization Failures
```python
try:
    self.langfuse = get_client()
    if not self.langfuse.auth_check():
        self.enable_langfuse = False
except Exception as e:
    logger.warning(f"Langfuse init failed: {e}")
    self.enable_langfuse = False
```

### Trace Creation Failures
- Tracing failures are logged but don't interrupt agent execution
- `trace_id` returns `None` if tracing is disabled
- Agent continues to function normally without tracing

### uvloop Compatibility
```python
# Check for uvloop before applying nest_asyncio
loop = asyncio.get_event_loop()
if not loop.__class__.__module__.startswith('uvloop'):
    nest_asyncio.apply()
```

## Performance Considerations

### Flushing Strategy
- **Streaming**: Events are sent as they occur
- **Non-streaming**: Explicit flush after completion
- **FastAPI**: Automatic flush on request completion

### Overhead Mitigation
- Tracing can be disabled via `LANGFUSE_ENABLED=false`
- Async operations prevent blocking main execution
- Batch operations where possible

## Monitoring & Debugging

### Langfuse Dashboard
Access traces at: https://us.cloud.langfuse.com
- Filter by user_id, session_id, or tags
- View trace waterfall diagrams
- Analyze tool call patterns
- Monitor user feedback scores

### Local Debugging
```python
# Enable debug logging
logger.debug(f"Created Langfuse trace: {trace_id}")

# Verify trace creation
if trace_id:
    logger.info(f"Trace URL: {self.langfuse.get_trace_url(trace_id)}")
```

## Best Practices

1. **Always include user_id and session_id** for proper grouping
2. **Use descriptive span names** for easy identification
3. **Include relevant metadata** in trace updates
4. **Flush events explicitly** in non-streaming contexts
5. **Handle failures gracefully** - tracing should never break the app
6. **Tag appropriately** for filtering and analysis

## Migration Notes

### From start_as_current_span to Direct Trace Creation
The initial implementation used context managers:
```python
# OLD - Didn't capture full execution
with self.langfuse.start_as_current_span(...) as span:
    result = Runner.run_streamed(...)  # Async generator
```

Current implementation uses direct trace creation:
```python
# NEW - Captures full execution
trace_id = self.langfuse.create_trace_id()
self.langfuse.update_current_trace(...)
span = self.langfuse.start_span(...)
# Process async generator
span.update(output=...)
span.end()
```

### Key Changes
1. Replaced `langfuse.trace()` (doesn't exist) with `create_trace_id()` + `update_current_trace()`
2. Use `start_span()` instead of non-existent `trace()` method
3. Explicit span lifecycle management with `update()` and `end()`
4. Tool calls create child spans with `start_span()`

## Testing

### Verification Steps
1. Start agents with `LANGFUSE_ENABLED=true`
2. Make queries through UI or API
3. Check Langfuse dashboard for traces
4. Verify trace contains:
   - Input query
   - Tool calls as spans
   - Output response
   - User/session IDs
5. Submit feedback and verify score appears in trace

### Common Issues
- **Missing trace details**: Ensure span.update() is called with output
- **No traces appearing**: Check auth with `langfuse.auth_check()`
- **uvloop warnings**: Normal in FastAPI, handled by conditional nest_asyncio

## Future Enhancements

1. **Custom Metrics**: Add performance metrics (latency, token usage)
2. **Error Tracking**: Enhanced error span creation with stack traces
3. **Batch Operations**: Implement batch trace updates for efficiency
4. **Sampling**: Add configurable trace sampling for high-volume scenarios
5. **Export**: Implement trace export for offline analysis