# Streaming Progress Updates - Design & Implementation

## Overview

Real-time progress updates provide user visibility during the 20-80 second agent orchestration process. Instead of showing a generic "thinking..." message, users see detailed progress like "🏥 Dr. OPA is checking CPSO policies for: virtual care requirements" or "🤔 Dr. OFF reasoning: Synthesizing billing codes...".

## Architecture

### Event Flow

```
Agent Query → OpenAI Agents SDK → StreamingProgressTracker → Progress Events → Web UI
                  ↓
            stream_events()
                  ↓
         RunItemStreamEvent
         AgentUpdatedStreamEvent
         ResponseTextDeltaEvent
                  ↓
         Progress Translation
                  ↓
         {type: 'progress', message: '...', event_type: '...'}
                  ↓
         FastAPI SSE Stream
                  ↓
         Web UI Display
```

### Components

1. **Agent Implementations** (`Dr. OPA`, `Dr. OFF`, `The Chief`)
   - Use OpenAI Agents SDK `Runner.run_streamed()`
   - Process `stream_events()` for both progress and data
   - Emit progress events alongside existing text/tool/citation events

2. **StreamingProgressTracker** (`src/ai_agents/diagnostic_orchestrator/streaming_progress.py`)
   - Converts SDK events into user-friendly messages
   - Maps tool names to descriptions
   - Extracts query parameters from tool arguments
   - Provides agent-specific emojis

3. **Web UI** (`web/components/agents/AgentChatInterface.tsx`)
   - Handles `progress` event type in stream event handler
   - Displays progress prominently below input box
   - Updates in real-time as events arrive

## Progress Event Types

### 1. Analysis Started
**Emitted:** At the beginning of agent execution
**Example:** `🔍 Analyzing your clinical query...`

```python
yield {
    'type': 'progress',
    'message': "🔍 Analyzing your query...",
    'event_type': "analysis_started",
    'agent_name': "Dr. OPA"
}
```

### 2. Agent Switched
**Emitted:** When orchestrator switches to a different agent
**Example:** `🏥 Consulting Dr. OPA for Ontario clinical pathways and quality standards...`

```python
if isinstance(event, AgentUpdatedStreamEvent):
    agent_name = event.new_agent.name
    emoji = tracker.get_agent_emoji(agent_name)
    yield {
        'type': 'progress',
        'message': f"{emoji} {agent_name} activated...",
        'event_type': 'agent_switched',
        'agent_name': agent_name
    }
```

**Agent Emojis:**
- The Chief: 🎯
- Dr. OPA: 🏥
- Dr. OFF: 💰
- Agent 97: 👨‍⚕️

### 3. Tool Called
**Emitted:** When agent calls an MCP tool or function
**Example:** `💰 Dr. OFF is searching OHIP billing codes for: "virtual care visits OHIP billing codes"`

```python
if event.name == "tool_called":
    tool_name = event.item.raw_item.name
    tool_desc = tracker.get_tool_description(tool_name)
    query = tracker.get_query_from_arguments(event.item.raw_item.arguments)

    yield {
        'type': 'progress',
        'message': f"{emoji} Dr. OFF is {tool_desc} for: \"{query}\"",
        'event_type': 'tool_called',
        'agent_name': tracker.current_agent,
        'tool_name': tool_name,
        'details': {'query': query}
    }
```

**Tool Descriptions:**
- `opa_policy_check` → "checking CPSO policies"
- `opa_quality_standards` → "reviewing Ontario Health quality standards"
- `schedule_get` → "searching OHIP billing codes"
- `odb_get` → "checking ODB drug formulary coverage"
- `agent_97_query` → "searching 97 trusted medical sources"

### 4. Tool Output
**Emitted:** When tool returns results
**Example:** `✅ Dr. OPA retrieved 5 results`

```python
if event.name == "tool_output":
    result_count = None
    if hasattr(event.item, 'output'):
        output = event.item.output
        if isinstance(output, dict) and 'items' in output:
            result_count = len(output['items'])

    message = f"✅ {agent} retrieved {result_count} results" if result_count else f"✅ {agent} completed search"

    yield {
        'type': 'progress',
        'message': message,
        'event_type': 'tool_output',
        'agent_name': tracker.current_agent,
        'details': {'result_count': result_count}
    }
```

### 5. Reasoning
**Emitted:** When reasoning model outputs thinking summary (with `reasoning: {"summary": "auto"}`)
**Example:** `🤔 Dr. OFF reasoning: Synthesizing billing codes...`

```python
if event.name == "reasoning_item_created":
    reasoning_item = event.item.raw_item
    if hasattr(reasoning_item, 'summary') and reasoning_item.summary:
        summaries = [s.text for s in reasoning_item.summary if hasattr(s, 'text') and s.text]
        reasoning_text = " ".join(summaries)

        if reasoning_text:  # Only emit if non-empty
            yield {
                'type': 'progress',
                'message': f"🤔 {agent} reasoning: {reasoning_text[:100]}...",
                'event_type': 'reasoning',
                'agent_name': tracker.current_agent,
                'details': {'reasoning': reasoning_text}
            }
```

### 6. Synthesis Started
**Emitted:** When agent begins final response synthesis
**Example:** `✍️ The Chief is synthesizing insights from all specialists...`

```python
if event.name == "message_output_created":
    yield {
        'type': 'progress',
        'message': "✍️ The Chief is synthesizing insights from all specialists...",
        'event_type': 'synthesis_started',
        'agent_name': "The Chief"
    }
```

## Implementation Pattern

### Agent `query_stream()` Method

All agents follow this pattern:

```python
async def query_stream(self, user_input: str, session_id: str = None):
    # Initialize tracker
    from src.ai_agents.diagnostic_orchestrator.streaming_progress import StreamingProgressTracker
    from agents.stream_events import AgentUpdatedStreamEvent, RunItemStreamEvent
    tracker = StreamingProgressTracker()

    # Emit initial progress
    yield {
        'type': 'progress',
        'message': "🔍 Analyzing your query...",
        'event_type': "analysis_started",
        'agent_name': "Dr. OPA"
    }

    # Stream events - process for BOTH progress and data
    async for event in result.stream_events():
        # FIRST: Emit progress update
        if isinstance(event, AgentUpdatedStreamEvent):
            # ... emit agent_switched progress
        elif isinstance(event, RunItemStreamEvent):
            if event.name == "tool_called":
                # ... emit tool_called progress
            elif event.name == "tool_output":
                # ... emit tool_output progress
            elif event.name == "reasoning_item_created":
                # ... emit reasoning progress
            elif event.name == "message_output_created":
                # ... emit synthesis_started progress

        # THEN: Process same event for existing data extraction
        if event.type == "raw_response_event":
            # ... handle text deltas
        elif event.type == "run_item_stream_event":
            # ... handle tool calls, citations, etc.
```

### Web UI Event Handler

```typescript
const handleStreamEvent = (event: any, messageId: string) => {
  switch (event.type) {
    case 'progress':
      // Update progress message state
      const progressMsg = event.message || event.content || '';
      setProgressMessage(progressMsg);
      console.log('Progress:', progressMsg, event);
      break;

    case 'text':
      // Handle text deltas...
      break;

    case 'tool_call':
      // Handle tool calls...
      break;

    case 'citation':
      // Handle citations...
      break;

    case 'complete':
      // Clear progress when done
      setProgressMessage('');
      break;
  }
};
```

### Web UI Display

```tsx
{isStreaming && (
  <div className="flex items-center justify-center gap-2 mt-2 sm:mt-3 max-w-4xl mx-auto">
    <div className="flex items-center gap-2 px-3 sm:px-4 py-2 sm:py-2.5 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg sm:rounded-xl border border-blue-200 shadow-sm">
      <div className="flex gap-0.5 sm:gap-1">
        <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
        <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
        <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 bg-blue-500 rounded-full animate-bounce"></span>
      </div>
      <span className="text-xs sm:text-sm text-blue-700 font-medium">
        {progressMessage || `${agent.name} is thinking...`}
      </span>
    </div>
  </div>
)}
```

## Model Configuration

All agents use **gpt-5-mini** with **reasoning: {"summary": "auto"}** for consistent behavior:

```python
from agents import ModelSettings

agent = Agent(
    name="Dr. OPA",
    instructions=system_instructions,
    model="gpt-5-mini",
    model_settings=ModelSettings(reasoning={"summary": "auto"}),
    mcp_servers=[server],
    tools=[web_search_tool]
)
```

**Why gpt-5-mini with reasoning?**
- ✅ Fast reasoning model suitable for multi-step tasks
- ✅ Emits reasoning summaries that can be shown to users
- ✅ Successfully calls MCP tools (o4-mini had issues)
- ✅ Lower cost than gpt-4o/gpt-5
- ✅ `summary: "auto"` provides concise reasoning updates

**Why not o4-mini?**
- ❌ Had issues calling MCP tools reliably in testing
- ❌ Interleaved empty reasoning items with tool calls
- ⚠️ May work but gpt-5-mini proven more reliable

## Agent Coverage

| Agent | Progress Events | Model | Status |
|-------|----------------|-------|--------|
| **The Chief** | ✅ Yes | gpt-5-mini + reasoning:auto | ✅ Complete |
| **Dr. OPA** | ✅ Yes | gpt-5-mini + reasoning:auto | ✅ Complete |
| **Dr. OFF** | ✅ Yes | gpt-5-mini + reasoning:auto | ✅ Complete |
| **Agent 97** | ✅ Via orchestrator | gpt-5-mini + reasoning:auto | ✅ Complete |

## Testing

### CLI Testing

```bash
# Test Dr. OPA progress
python scripts/test_streaming_progress_real.py

# Expected output:
# [1] analysis_started: 🔍 Analyzing your clinical query...
# [2] agent_switched: 🏥 Consulting Dr. OPA...
# [3] tool_called: 🏥 Dr. OPA is checking CPSO policies for: "CPSO virtual care..."
# [4] tool_output: ✅ Dr. OPA completed search
# [5] synthesis_started: ✍️ The Chief is synthesizing insights...
```

### Web UI Testing

1. Start dev server: `cd web && npm run dev`
2. Navigate to agent chat (e.g., `/agents/dr-opa`)
3. Send a query
4. Observe progress updates below input box in real-time

## Files Modified

### Agent Implementations
- `src/ai_agents/dr_opa_agent/openai_agent.py` - Added progress to `query_stream()`
- `src/ai_agents/dr_off_agent/openai_agent.py` - Added progress to `query_stream()`
- `src/ai_agents/diagnostic_orchestrator/orchestrator_agent.py` - Already had progress from prior work

### Progress Tracker
- `src/ai_agents/diagnostic_orchestrator/streaming_progress.py` - Core progress translation logic

### Web UI
- `web/components/agents/AgentChatInterface.tsx` - Progress event handling and display

### Tests
- `scripts/test_streaming_progress_real.py` - CLI test for progress events

## Future Enhancements

### Potential Improvements

1. **Progress History**
   - Store progress events in message metadata
   - Allow users to expand/collapse progress timeline
   - Show total time per step

2. **Estimated Time Remaining**
   - Track average time per event type
   - Show progress bar with ETA
   - "Usually takes 45 seconds..."

3. **Progress Animations**
   - Animated transitions between progress states
   - Tool-specific icons/animations
   - Visual timeline

4. **Detailed Progress View**
   - Collapsible accordion with all progress steps
   - Show tool arguments and results
   - Display reasoning chain of thought

5. **Progress Notifications**
   - Browser notifications for long-running queries
   - Sound alerts on completion
   - Desktop notifications

## Troubleshooting

### Progress Not Appearing

**Symptoms:** Only seeing "Agent is thinking..." without detailed progress

**Check:**
1. Verify agent is using `gpt-5-mini` with `reasoning: {"summary": "auto"}`
2. Check if `RunItemStreamEvent` import is correct
3. Verify progress event emission in agent's `query_stream()`
4. Check browser console for progress events being received
5. Ensure web UI has `progressMessage` state

### Empty Reasoning Items

**Symptoms:** Reasoning progress events are empty or not showing

**Cause:** Reasoning summaries may be empty during early processing

**Solution:** Code already skips empty reasoning items:
```python
if not reasoning_text:
    continue  # Skip empty reasoning
```

### Tool Calls Not Showing

**Symptoms:** Tool progress not appearing, only generic "thinking..."

**Check:**
1. Verify model is correctly calling MCP tools (check OpenAI trace)
2. Ensure `event.name == "tool_called"` condition is matching
3. Check if `event.item.raw_item.name` exists
4. Verify tool descriptions are mapped in `StreamingProgressTracker`

## References

- [OpenAI Agents SDK Documentation](https://github.com/openai/openai-agents-python)
- [Streaming Events Guide](https://github.com/openai/openai-agents-python/blob/main/docs/streaming.md)
- [gpt-5-mini Model Card](https://platform.openai.com/docs/models/gpt-5-mini)
- [Project Streaming Architecture](../streaming_architecture.md)

---

**Last Updated:** 2025-10-09
**Author:** Claude Code
**Status:** ✅ Production Ready
