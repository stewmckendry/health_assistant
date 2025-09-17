# Streaming Response Documentation

## Overview

The Health Assistant implements streaming responses using Server-Sent Events (SSE) to provide real-time feedback to users. This dramatically improves perceived performance, showing the first text in under 1 second while background processing continues.

## Architecture

### Streaming Mixin

The streaming capability is implemented as a mixin class in `src/assistants/streaming_mixin.py`:

```python
class StreamingMixin:
    """Mixin to add streaming support to assistant classes."""
    
    @observe(name="llm_call_stream", as_type="generation", capture_input=True)
    def query_stream(self, query: str, ...) -> Iterator[Dict[str, Any]]:
        """Stream a query response from the Anthropic API."""
```

This mixin can be added to any assistant class to provide streaming capabilities.

### Event Types

The streaming system emits different event types during processing:

| Event Type | Description | Content |
|------------|-------------|---------|
| `start` | Streaming session started | Session metadata |
| `text` | Text chunk from LLM | Incremental text |
| `tool_use` | Tool invocation | Tool name and input |
| `citation` | Source citation found | URL and title |
| `complete` | Response complete | Full text, citations, metrics |
| `error` | Error occurred | Error message |

### Event Structure

Each event follows this structure:

```json
{
  "type": "text",
  "content": "The text chunk...",
  "metadata": {
    "timestamp": 0.123,
    "total_length": 150,
    "is_first_token": false
  }
}
```

## API Implementation

### Streaming Endpoint

```http
POST /chat/stream
```

The endpoint returns Server-Sent Events (SSE) with the following headers:
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `X-Accel-Buffering: no` (Disables Nginx buffering)

### SSE Format

Each event is sent in the SSE format:
```
data: {"type": "text", "content": "Influenza, commonly known as the flu..."}

data: {"type": "citation", "content": {"url": "https://cdc.gov/flu", "title": "CDC - Influenza"}}

data: {"type": "complete", "content": "...", "metadata": {...}}
```

### Client-Side Processing

The frontend processes SSE using the Fetch API:

```typescript
const response = await fetch('/chat/stream', {
  method: 'POST',
  body: JSON.stringify({ query, sessionId, mode })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const events = chunk.split('\n\n');
  
  for (const event of events) {
    if (event.startsWith('data: ')) {
      const data = JSON.parse(event.slice(6));
      handleStreamEvent(data);
    }
  }
}
```

## Performance Metrics

### Time to First Token (TTFT)

The streaming system tracks when the first text token is received:

```python
if first_token_time is None:
    first_token_time = current_time

yield {
    "type": "text",
    "content": text_chunk,
    "metadata": {
        "timestamp": current_time,
        "is_first_token": first_token_time == current_time
    }
}
```

Typical TTFT: **< 1 second**

### Total Processing Time

Complete response time including all web searches and citations:

| Operation | Time |
|-----------|------|
| First token | < 1 second |
| Web search | 10-15 seconds |
| Web fetches | 5-10 seconds |
| Total | 15-20 seconds |

## Streaming vs Non-Streaming Comparison

### User Experience

| Aspect | Non-Streaming | Streaming |
|--------|--------------|-----------|
| Feedback | 20-30 second wait | < 1 second to first text |
| Progress | No indication | Real-time text generation |
| Citations | All at end | Appear as found |
| Perceived Speed | Slow | Fast |

### Technical Differences

| Aspect | Non-Streaming | Streaming |
|--------|--------------|-----------|
| Response Type | JSON | Server-Sent Events |
| Memory Usage | Holds full response | Incremental processing |
| Error Handling | HTTP status codes | Error events |
| Retry Logic | Standard HTTP | Event stream reconnection |

## Guardrails Interaction

### Critical Design Decision

**Output guardrails are incompatible with streaming.** When output guardrails are enabled, the system automatically falls back to non-streaming mode.

**Rationale**: Output guardrails need the complete response to:
1. Check for diagnostic language
2. Verify medical disclaimers
3. Validate citation quality
4. Apply necessary modifications

**Implementation**:
```python
# In main.py
if settings.enable_output_guardrails:
    use_streaming = False  # Force non-streaming
```

### Input Guardrails

Input guardrails work with streaming since they process the query before the LLM call:
1. Check query for emergencies
2. Block if needed
3. Proceed with streaming if safe

## Langfuse Observability

### Streaming Observations

The streaming system records detailed metrics in Langfuse:

```python
langfuse.update_current_observation(
    model=self.model,
    input=messages,
    output=accumulated_text,
    metadata={
        "streaming": True,
        "time_to_first_token": 0.8,
        "total_time": 18.5,
        "citations_count": 3,
        "tool_calls_count": 1
    }
)
```

### Key Metrics Tracked

- **time_to_first_token**: User-perceived responsiveness
- **total_time**: End-to-end processing time
- **tool_calls**: Web searches and fetches performed
- **citations_count**: Number of sources found

## Implementation Details

### Anthropic SDK Streaming

The implementation uses Anthropic's streaming API:

```python
with self.client.messages.stream(**api_kwargs) as stream:
    for event in stream:
        if event.type == "content_block_delta":
            if hasattr(event.delta, 'text'):
                text_chunk = event.delta.text
                yield {"type": "text", "content": text_chunk}
```

### Citation Extraction

Citations are extracted from the final message after streaming completes:

```python
final_message = stream.get_final_message()

for block in final_message.content:
    if hasattr(block, 'citations') and block.citations:
        for citation in block.citations:
            yield {"type": "citation", "content": {...}}
```

### Error Handling

Errors during streaming are sent as error events:

```python
except Exception as e:
    yield {
        "type": "error",
        "content": str(e),
        "metadata": {"timestamp": perf_counter() - start_time}
    }
```

## Frontend Integration

### ChatInterface Component

The chat interface handles streaming responses:

1. **Visual Feedback**: Shows typing indicator
2. **Progressive Rendering**: Updates message as text arrives
3. **Citation Collection**: Displays sources as they're found
4. **Error Recovery**: Shows error messages inline

### Message Updates

Messages are updated progressively:

```typescript
// Start event
setMessages([...messages, { 
  role: 'assistant', 
  content: '', 
  streaming: true 
}]);

// Text events
setMessages(prev => {
  const last = prev[prev.length - 1];
  return [...prev.slice(0, -1), {
    ...last,
    content: last.content + event.content
  }];
});

// Complete event
setMessages(prev => {
  const last = prev[prev.length - 1];
  return [...prev.slice(0, -1), {
    ...last,
    streaming: false,
    citations: event.citations
  }];
});
```

## Best Practices

### When to Use Streaming

✅ **Use streaming when:**
- User experience is priority
- Output guardrails are disabled
- Real-time feedback is valuable
- Response length is significant

❌ **Don't use streaming when:**
- Output guardrails are required
- Batch processing multiple queries
- Response needs modification
- Client doesn't support SSE

### Performance Optimization

1. **Minimize Buffer Size**: Send events immediately
2. **Disable Proxy Buffering**: Set `X-Accel-Buffering: no`
3. **Keep Events Small**: Send incremental updates
4. **Handle Reconnection**: Implement retry logic

### Error Recovery

1. **Graceful Degradation**: Fall back to non-streaming
2. **Timeout Handling**: Set reasonable timeouts
3. **Partial Response**: Save progress periodically
4. **User Notification**: Show clear error messages

## Future Enhancements

Potential improvements to streaming:

1. **Partial Guardrails**: Apply safety checks to chunks
2. **Stream Compression**: Reduce bandwidth usage
3. **Parallel Streams**: Multiple assistants simultaneously
4. **Resume Support**: Continue interrupted streams
5. **Priority Queuing**: Manage multiple concurrent users
6. **WebSocket Upgrade**: Bidirectional communication
7. **Progress Indicators**: Show search/fetch progress
8. **Chunk Batching**: Optimize for network latency