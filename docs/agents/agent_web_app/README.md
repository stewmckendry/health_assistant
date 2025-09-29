# Clinical AI Agents Web Application

## Overview

A unified web interface for accessing Ontario-specific clinical AI agents, providing healthcare professionals with intelligent assistance powered by trusted medical sources and regulatory guidance.

## Available Agents

### 🩺 Dr. OPA (Ontario Practice Advice)
**Status**: Active  
**Purpose**: Provides Ontario-specific primary care and practice guidance  
**Knowledge Base**: 
- CPSO policies and regulatory requirements
- Ontario Health clinical programs
- PHO infection control guidance
- CEP clinical decision tools

### 🎯 Agent 97  
**Status**: Active  
**Purpose**: Medical education assistant with 97 trusted sources  
**Knowledge Base**:
- 97 vetted medical domains
- Canadian healthcare authorities
- Global medical journals
- Evidence-based resources

### 💊 Dr. OFF (Ontario Finance & Formulary)
**Status**: Coming Soon  
**Purpose**: Ontario drug formulary and billing guidance  
**Knowledge Base**:
- ODB formulary
- OHIP billing codes
- ADP eligibility
- Drug coverage criteria

## Key Features

### 🔄 Streaming Responses
- Real-time response generation using OpenAI Agents SDK
- Progressive text rendering with RunResultStreaming
- Server-sent events (SSE) for efficient streaming
- Interrupt and resume capabilities

### 💬 Multi-turn Conversations  
- Session persistence using SQLiteSession
- Automatic context retention across messages
- Conversation history management
- Export and save conversations

### 🛠️ Tool Call Visibility
- Real-time display of MCP tool execution
- Tool arguments and results shown
- Timing and status indicators
- Collapsible tool call panels

### 📚 Citation Management
- Automatic extraction from agent responses
- Deduplication of sources
- Clickable links to trusted domains
- Source credibility indicators

## Architecture

```
┌─────────────────────────────────────────────┐
│                   Frontend                   │
│         Next.js 14 + React + TypeScript      │
├─────────────────────────────────────────────┤
│                    Pages                     │
│  /agents - Main agent selection interface    │
├─────────────────────────────────────────────┤
│                  Components                  │
│  AgentList | AgentChat | ToolDisplay | Cites│
├─────────────────────────────────────────────┤
│                  API Routes                  │
│   /api/agents/[agent]/stream (SSE)          │
│   /api/agents/[agent]/conversations         │
├─────────────────────────────────────────────┤
│              Agent Integration               │
│         OpenAI Agents SDK + MCP              │
├─────────────────────────────────────────────┤
│                   Agents                     │
│    Dr. OPA | Agent 97 | Dr. OFF (soon)      │
└─────────────────────────────────────────────┘
```

## Usage

### Accessing the Clinical Agents Interface

1. Navigate to the Health Assistant web app
2. Click on "Clinical Agents" in the header
3. Select an agent from the available list
4. Review agent capabilities in the detail card
5. Start a conversation

### Starting a Conversation

```typescript
// User clicks on an agent
const startConversation = async (agentId: string) => {
  const response = await fetch(`/api/agents/${agentId}/conversations`, {
    method: 'POST'
  });
  const { sessionId } = await response.json();
  // Navigate to chat interface with session
};
```

### Sending Messages with Streaming

```typescript
// Send message and handle streaming response
const sendMessage = async (query: string) => {
  const eventSource = new EventSource(
    `/api/agents/${agentId}/stream?sessionId=${sessionId}&query=${query}`
  );
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle different event types
    if (data.type === 'text') {
      appendToMessage(data.content);
    } else if (data.type === 'tool_call') {
      displayToolCall(data.tool);
    } else if (data.type === 'citation') {
      addCitation(data.source);
    }
  };
};
```

## Component Structure

### AgentList Component
Displays available agents in a grid layout with:
- Agent name and icon
- Brief description
- Status indicator (Active/Coming Soon)
- Click to view details or start chat

### AgentChatInterface Component
Main chat interface featuring:
- Agent header with name and status
- Message history with role indicators
- Streaming message display
- Tool call visibility panel
- Citation list at bottom

### ToolCallDisplay Component
Shows real-time tool execution:
- Tool name and icon
- Input arguments
- Execution status
- Results or errors
- Timing information

### CitationList Component
Manages extracted citations:
- Deduplicated source list
- Domain favicons
- Trust level indicators
- Direct links to sources

## API Endpoints

### Agent Management
- `GET /api/agents` - List all agents
- `GET /api/agents/[agentId]` - Get agent details
- `GET /api/agents/[agentId]/health` - Check availability

### Conversations
- `POST /api/agents/[agentId]/conversations` - Start session
- `POST /api/agents/[agentId]/conversations/[sessionId]/messages` - Send message
- `GET /api/agents/[agentId]/conversations/[sessionId]/history` - Get history

### Streaming
- `GET /api/agents/[agentId]/stream` - SSE streaming endpoint

## Safety & Disclaimers

### Required Disclaimers
- "Prerelease for interested parties - Not ready for production"
- "For educational and informational purposes only"
- "Not a substitute for professional medical advice"
- "Always consult qualified healthcare providers"

### Agent-Specific Warnings
- **Dr. OPA**: "Regulatory guidance - verify with official sources"
- **Agent 97**: "Medical education only - no diagnosis provided"
- **Dr. OFF**: "Coverage details subject to change - verify eligibility"

## Configuration

### Agent Configuration File
```typescript
// web/config/agents.config.ts
export const AGENTS_CONFIG = {
  'dr-opa': {
    id: 'dr-opa',
    name: 'Dr. OPA',
    description: 'Ontario Practice Advice',
    status: 'active',
    icon: '🩺',
    endpoint: '/api/agents/dr-opa',
    tools: ['opa_policy_check', 'opa_program_lookup', ...],
    knowledgeSources: ['CPSO', 'Ontario Health', ...]
  },
  // ... other agents
};
```

### Environment Variables
```bash
# Required
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
AGENT_SESSION_TIMEOUT=1800  # 30 minutes
MAX_CONVERSATION_LENGTH=50  # messages
STREAMING_CHUNK_SIZE=1024
```

## Testing

### Unit Tests
```bash
npm run test:unit
# Tests components, utilities, parsers
```

### Integration Tests
```bash
npm run test:integration  
# Tests API routes, agent communication
```

### E2E Tests
```bash
npm run test:e2e
# Tests complete user journeys
```

## Development

### Running Locally
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Access at http://localhost:3000/agents
```

### Adding a New Agent

1. Create agent configuration in `agents.config.ts`
2. Add API route in `/api/agents/[newAgent]/`
3. Update agent adapter for response formatting
4. Add agent-specific tests
5. Update documentation

## Monitoring

### Key Metrics
- Response time (p95 < 3s)
- Streaming latency (< 100ms)
- Tool call success rate (> 95%)
- Citation extraction accuracy (> 90%)
- Session persistence reliability

### Error Handling
- Graceful fallbacks for agent failures
- Retry logic for network issues
- User-friendly error messages
- Error boundary components

## Security Considerations

- No PHI storage in sessions
- API key rotation schedule
- Rate limiting per session
- Input sanitization
- XSS prevention in citations

## Future Enhancements

- Voice input/output support
- Mobile-optimized interface
- Agent comparison mode
- Conversation analytics
- Bulk query processing
- Integration with EHR systems

## Support

For issues or questions:
- Check [troubleshooting guide](./troubleshooting.md)
- Review [API documentation](./api-docs.md)
- Contact development team

## License

Part of the Ontario Health AI Assistant Suite - See LICENSE file for details.