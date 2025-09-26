# Agent 97 Implementation Documentation

## Current Architecture

Agent 97 is a medical education assistant that provides plain language explanations of medical terms and health topics to patients. As of the latest implementation, Agent 97 uses the PatientAssistant directly without any OpenAI wrapper.

## Implementation Overview

### Core Components

1. **PatientAssistant** (`src/assistants/patient.py`)
   - Main implementation providing medical information with citations
   - Uses Anthropic Claude API with web tools
   - Implements comprehensive safety guardrails
   - Returns structured responses with citations and tool calls

2. **Dedicated Endpoint** (`src/web/api/agent_97_endpoint.py`)
   - Provides `/agents/agent-97/stream` and `/agents/agent-97/query` endpoints
   - Transforms PatientAssistant streaming events to frontend format
   - Handles event types: text, tool_use, citation, complete
   - Manages session IDs and deduplicates citations

3. **Frontend Integration** (`web/components/agents/`)
   - **AgentChatInterface.tsx**: Main chat component handling SSE streaming
   - **AgentMessage.tsx**: Message display with inline citations and tool calls
   - **InlineCitations**: Expandable citation display (shows 3, click for all)
   - **InlineToolCalls**: Collapsible tool execution status display

### Data Flow

```
User Input → Frontend (AgentChatInterface) 
    → API Route (/api/agents/agent-97/stream)
    → FastAPI Backend (port 8000)
    → agent_97_endpoint.py
    → PatientAssistant.query_stream()
    → Anthropic Claude API
    → Stream events back through chain
    → Frontend displays with inline citations/tools
```

### Event Transformation

The agent_97_endpoint transforms PatientAssistant events for the frontend:

```python
# PatientAssistant Event Types
- type: 'start' → Sent as 'response_start'
- type: 'tool_use' → Transformed to 'tool_call_start' with status
- type: 'text' → Forwarded as 'text' with delta
- type: 'citation' → Enriched with domain, trusted status
- type: 'complete' → Sent as 'response_done'
```

### Key Features

1. **Streaming Response**: Real-time SSE-based response streaming
2. **Inline Citations**: Citations appear with the message that references them
3. **Tool Visibility**: Tool calls displayed with status indicators
4. **Citation Deduplication**: Prevents duplicate citations by URL
5. **Trust Validation**: Marks citations from 97 trusted medical domains
6. **Plain Language**: Focuses on explaining medical terms simply

## Configuration

### Trusted Domains
Agent 97 validates citations against 97 trusted medical domains configured in:
- `src/config/domains.yaml` - Full list of trusted sources

### API Integration
- Uses PatientAssistant's built-in Anthropic Claude integration
- Web tools enabled for search and fetch capabilities
- Streaming enabled for responsive user experience

## Frontend Components

### AgentMessage Component
New unified message component providing:
- Inline citation display with expand/collapse
- Tool call visualization with status icons
- Markdown rendering for formatted responses
- Timestamp and streaming indicators

### Citation Display
- Shows first 3 citations by default
- "Show all N" button for expansion
- Domain display with trusted badges
- External link icons for navigation

### Tool Call Display
- Collapsible section for tool details
- Status icons (executing, completed, failed)
- Tool names displayed in monospace font

## Removed Components

The following components were removed during cleanup:
- `/src/agents/agent_97/openai_agent.py` - Old OpenAI wrapper (no longer needed)
- `/src/web/api/agent_97_streaming_endpoint.py` - Duplicate endpoint
- `/scripts/test_agent_97.py` - Test script for old wrapper
- Right panel with Reasoning/Citations tabs (replaced with inline display)

## Testing

To test Agent 97:

1. Start the FastAPI backend:
```bash
source /Users/liammckendry/spacy_env/bin/activate
python -m src.web.api.main
```

2. Start the Next.js frontend:
```bash
cd web
npm run dev
```

3. Navigate to http://localhost:3000/agents
4. Select Agent 97
5. Test queries like:
   - "What are the symptoms of the flu?"
   - "Explain diabetes in simple terms"
   - "What does hypertension mean?"

## Future Enhancements

1. **Voice Input**: Add speech-to-text for accessibility
2. **Language Support**: Multi-language medical explanations
3. **Visual Aids**: Include medical diagrams and illustrations
4. **Personalization**: Tailor explanations to user's health literacy level
5. **Export**: Allow users to save/print explanations

## Troubleshooting

### Common Issues

1. **Citations not appearing**: Check that PatientAssistant is returning citations in the expected format
2. **Tool calls stuck in "executing"**: Ensure complete event properly marks tools as completed
3. **Streaming not working**: Verify SSE headers are correct and no buffering middleware interferes

### Debug Points

- Check browser console for SSE event parsing errors
- Monitor FastAPI logs for streaming event generation
- Verify PatientAssistant is properly initialized with web tools
- Ensure ANTHROPIC_API_KEY is set in environment