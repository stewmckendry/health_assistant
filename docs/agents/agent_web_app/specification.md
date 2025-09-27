# Agent Web App Specification

## Overview

The Agent Web App is a Next.js-based interface for interacting with Ontario clinical AI agents. It provides a unified platform for healthcare clinicians to access specialized AI assistants including Dr. OPA (Ontario Practice Advice) and Agent 97 (Medical Education), with support for streaming responses, multi-turn conversations, and comprehensive citation tracking.

## Architecture

### Technology Stack

- **Frontend**: Next.js 15 with App Router
- **UI Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS with custom components
- **Backend**: FastAPI (port 8000) + Next.js API Routes (port 3000)
- **Agent Integration**: OpenAI Agents SDK with MCP (Model Context Protocol)
- **State Management**: React State and session persistence
- **Real-time Updates**: Server-Sent Events (SSE) with ReadableStream

### Project Structure

```
web/
├── app/
│   ├── agents/
│   │   ├── page.tsx                 # Main agents interface
│   │   └── [agentId]/
│   │       └── page.tsx             # Individual agent chat page
│   └── api/
│       └── agents/
│           ├── [agentId]/
│           │   ├── query/
│           │   │   └── route.ts     # Agent query endpoint
│           │   └── stream/
│           │       └── route.ts     # Streaming endpoint
│           └── sessions/
│               └── route.ts         # Session management
├── components/
│   ├── agents/
│   │   ├── AgentChatInterface.tsx   # Main chat component
│   │   ├── AgentMessage.tsx        # Message with inline citations/tools
│   │   ├── AgentGrid.tsx           # Agent selection grid
│   │   ├── AgentCard.tsx           # Individual agent cards
│   │   ├── ChatMessage.tsx         # Message components
│   │   ├── CitationList.tsx        # Citation display
│   │   ├── ToolCallDisplay.tsx     # Tool execution status
│   │   └── StreamingIndicator.tsx  # Real-time indicators
│   └── ui/                         # Shared UI components
├── lib/
│   ├── agents/
│   │   ├── client.ts              # Agent API client
│   │   ├── session.ts             # Session management
│   │   ├── trusted-domains.ts     # Domain validation
│   │   └── adapters/
│   │       ├── dr-opa.ts          # Dr. OPA adapter
│   │       └── agent-97.ts        # Agent 97 adapter
│   └── utils/                     # Utility functions
├── config/
│   └── agents.config.ts           # Agent configurations
└── types/
    ├── citations.ts               # Citation type definitions
    └── agents.ts                  # Agent type definitions
```

## Core Features

### 1. Agent Selection Interface

**Location**: `/web/app/agents/page.tsx`

- **Grid Layout**: Displays available agents in responsive card format
- **Agent Cards**: Show mission, tools, knowledge sources, and availability
- **Status Indicators**: Real-time health status from MCP servers
- **Filtering**: Filter by agent type, status, or capabilities

**Agent Configuration**: `/web/config/agents.config.ts`

```typescript
interface AgentConfig {
  id: string;
  name: string;
  description: string;
  mission: string;
  tools: string[];
  knowledgeSources: string[];
  capabilities: string[];
  status: 'available' | 'coming_soon';
  adapter: string;
  mcp_command: string[];
}
```

### 2. Chat Interface

**Location**: `/web/components/agents/AgentChatInterface.tsx`

**Features:**
- **Multi-turn Conversations**: Persistent context via SQLite sessions
- **Streaming Responses**: Real-time response updates via SSE
- **Tool Call Visibility**: Live display of MCP tool executions
- **Citation Tracking**: Comprehensive source attribution
- **Message History**: Full conversation persistence
- **Error Handling**: Graceful degradation and retry mechanisms

**Key Components:**

#### Message Flow
1. User input → `handleSendMessage()`
2. Create/retrieve session → Session management
3. Send to agent API → `/api/agents/[agentId]/query`
4. Stream response → SSE endpoint
5. Update UI components → Real-time updates

#### Session Management
- **SQLite Database**: Persistent conversation storage
- **Session IDs**: UUID-based session identification
- **Context Preservation**: Multi-turn conversation memory
- **User Association**: Optional user identification

### 3. Citation System

**Location**: `/web/components/agents/CitationList.tsx`

**Architecture:**
- **Standardized Format**: Unified citation schema across agents
- **Trust Validation**: 97 trusted medical domains verification
- **Deduplication**: URL and title-based duplicate removal
- **Real-time Updates**: Citations appear during streaming
- **Source Grouping**: Group citations by domain/organization
- **Inline Display**: Citations shown directly with relevant messages
- **Expandable View**: Show first 3 citations, expand for more

**Citation Schema**: `/web/types/citations.ts`

```typescript
interface Citation {
  id: string;
  title: string;
  source: string;
  source_type: SourceType;
  url: string;
  domain: string;
  is_trusted: boolean;
  access_date: string;
  snippet?: string;
  relevance_score: number;
}
```

### 4. Tool Call Visualization

**Location**: `/web/components/agents/ToolCallDisplay.tsx`

**Features:**
- **Real-time Status**: Live updates during tool execution
- **Execution Details**: Tool names, parameters, and results
- **Error Handling**: Display tool failures and retries
- **Performance Metrics**: Execution timing and success rates
- **Inline Display**: Tool calls shown with the message that triggered them
- **Status Icons**: Visual indicators (executing, completed, failed)

### 5. Streaming Implementation

**API Endpoint**: `/web/app/api/agents/[agentId]/stream/route.ts`

**Technology**: Server-Sent Events (SSE)

**Event Types:**
```typescript
type StreamEvent = 
  | { type: 'message'; data: { content: string; } }
  | { type: 'tool_call'; data: { name: string; status: string; } }
  | { type: 'citation'; data: Citation }
  | { type: 'complete'; data: { session_id: string; } }
  | { type: 'error'; data: { error: string; } };
```

## Agent Integration

### 1. Agent Adapters

**Pattern**: Adapter pattern for consistent interface

**Base Interface**: `/web/lib/agents/client.ts`

```typescript
interface AgentAdapter {
  query(input: string, sessionId?: string): Promise<AgentResponse>;
  stream(input: string, sessionId?: string): AsyncIterableIterator<StreamEvent>;
  getStatus(): Promise<AgentStatus>;
}
```

### 2. Dr. OPA Integration

**Adapter**: `/web/lib/agents/adapters/dr-opa.ts`

**Features:**
- **MCP Tools**: Policy check, program lookup, IPAC guidance
- **Citation Extraction**: Structured citations from MCP responses
- **Context Awareness**: Ontario-specific healthcare context

**MCP Command**: `python -m src.agents.dr_opa_agent.openai_agent`

### 3. Agent 97 Integration

**Implementation**: Direct PatientAssistant usage via dedicated endpoint

**Features:**
- **97 Trusted Sources**: Comprehensive medical domain validation
- **Educational Content**: Plain language medical explanations
- **Safety Guardrails**: Built-in content safety mechanisms
- **Inline Citations**: Citations and tool calls displayed with each message

**Architecture:**
- **Endpoint**: `src/web/api/agent_97_endpoint.py`
- **Core Implementation**: `src/assistants/patient.py` (PatientAssistant)
- **Streaming**: Native SSE support with event transformation
- **Frontend Component**: `AgentMessage.tsx` with inline citations/tools

## API Specifications

### Query Endpoint

**Route**: `POST /api/agents/[agentId]/query`

**Request:**
```typescript
{
  message: string;
  session_id?: string;
  context?: Record<string, any>;
}
```

**Response:**
```typescript
{
  response: string;
  citations: Citation[];
  highlights: Highlight[];
  tool_calls: ToolCall[];
  confidence: number;
  session_id: string;
}
```

### Stream Endpoint

**Route**: `GET /api/agents/[agentId]/stream`

**Query Parameters:**
- `message`: string (required)
- `session_id`: string (optional)

**Response**: Server-Sent Events stream

### Backend Integration

**FastAPI Server**: `src/web/api/main.py`
- Runs on port 8000 alongside Next.js frontend
- Provides streaming endpoints for all agents
- Handles CORS for cross-origin requests

**Agent Streaming Endpoints**:
- `POST /api/agents/dr-opa/stream` - Dr. OPA streaming responses
- `POST /api/agents/agent-97/stream` - Agent 97 streaming via PatientAssistant
- `POST /api/agents/agent-97/query` - Agent 97 non-streaming endpoint
- `POST /api/agents/triage/stream` - Triage agent streaming (when available)

**Integration Pattern**:
1. Next.js frontend calls its own API routes
2. Next.js API routes proxy to FastAPI backend on port 8000
3. FastAPI handles agent communication and streaming
4. Responses stream back through Next.js to frontend

## User Experience

### 1. Agent Selection Flow

1. **Landing Page**: Display agent grid with status indicators
2. **Agent Cards**: Show mission, capabilities, and availability
3. **Selection**: Click to enter chat interface
4. **Health Check**: Verify agent availability before enabling

### 2. Chat Interaction Flow

1. **Session Creation**: Initialize conversation context
2. **Message Input**: Rich text input with validation
3. **Streaming Response**: Real-time response generation
4. **Citation Display**: Live citation updates during streaming
5. **Tool Visibility**: Show MCP tool executions in progress
6. **History**: Persistent conversation history

### 3. Citation Experience

1. **Real-time Appearance**: Citations appear during response streaming
2. **Trust Indicators**: Visual cues for trusted vs. external sources
3. **Source Details**: Expandable citation information
4. **External Links**: Direct navigation to source materials
5. **Grouping**: Organize citations by domain/organization

## Technical Implementation Details

### 1. Session Management

**Storage**: SQLite database for conversation persistence

**Schema:**
```sql
CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  user_id TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  citations TEXT, -- JSON array
  tool_calls TEXT, -- JSON array
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

### 2. Citation Processing Pipeline

1. **Agent Response**: Receive structured citations from agent
   - Dr. OPA MCP tools now return standardized citations at the top level
   - All citations include: source, source_org, loc, and url fields
   - Automatic extraction from nested response structures
2. **Domain Validation**: Check against trusted domains list
3. **Deduplication**: Remove duplicate URLs and titles
   - Dr. OPA MCP server now performs deduplication using unique citation keys
   - Key format: `{source}_{source_org}_{loc}`
4. **Standardization**: Convert to unified citation format
   - Handled by response_formatter utility in dr_opa_mcp/utils/
   - Ensures consistent citation structure across all MCP tools
5. **UI Update**: Stream citations to frontend components

### 3. Error Handling Strategy

**Levels:**
- **Agent Errors**: Handle MCP server failures gracefully
- **Network Errors**: Implement retry with exponential backoff
- **Parsing Errors**: Fallback to text-only responses
- **UI Errors**: Error boundaries with user-friendly messages

**Fallbacks:**
- **Agent Offline**: Show cached responses or contact information
- **Citation Failure**: Display response without citations
- **Streaming Failure**: Fall back to synchronous responses

### 4. Performance Optimizations

**Current Implementation** (v1):
- **Component Optimization**: React.memo for citation lists
- **Debounced Input**: 300ms debounce for search/filter
- **Lazy Loading**: Dynamic imports for agent adapters
- **Error Boundaries**: Prevent UI crashes

**Future Enhancements** (v2):
- **Response Caching**: Cache common queries
- **Citation Prefetch**: Preload citation metadata
- **Connection Pooling**: Reuse MCP connections
- **CDN Integration**: Static asset optimization

## Security Considerations

### 1. Input Validation

- **Message Sanitization**: XSS prevention
- **Parameter Validation**: Type and range checking
- **Rate Limiting**: Prevent abuse and resource exhaustion

### 2. Citation Security

- **URL Validation**: Verify citation URLs are safe
- **Domain Whitelist**: Only trusted domains for auto-navigation
- **Content Filtering**: Remove potentially harmful content

### 3. Session Security

- **Session IDs**: UUID v4 for unpredictable identifiers
- **Data Encryption**: Encrypt sensitive session data
- **Access Control**: User-based session isolation

## Deployment Architecture

### Development Environment

```bash
# Prerequisites
node >= 18.0.0
python >= 3.11
anthropic-api-key
openai-api-key

# Setup
cd web/
npm install
npm run dev

# Agent servers (separate terminals)
python -m src.agents.dr_opa_agent.openai_agent
python -m src.agents.agent_97.openai_agent
```

### Production Considerations

**Scalability:**
- **Load Balancing**: Multiple Next.js instances
- **Agent Scaling**: Multiple MCP server instances
- **Database**: PostgreSQL for production sessions
- **Monitoring**: Health checks and performance metrics

**Reliability:**
- **Circuit Breakers**: Prevent cascade failures
- **Graceful Degradation**: Fallback responses
- **Health Monitoring**: Agent availability tracking
- **Logging**: Comprehensive request/response logging

## Testing Strategy

### 1. Unit Tests

- **Components**: Jest + React Testing Library
- **Utilities**: Citation processing, domain validation
- **Adapters**: Agent integration logic

### 2. Integration Tests

- **API Routes**: End-to-end request/response cycles
- **Agent Communication**: MCP server integration
- **Session Management**: Database operations

### 3. User Acceptance Tests

- **Chat Flow**: Complete conversation scenarios
- **Citation Display**: Accurate source attribution
- **Error Handling**: Graceful failure scenarios

## Monitoring and Analytics

### 1. Performance Metrics

- **Response Times**: Agent query latency
- **Success Rates**: Query completion rates
- **Citation Accuracy**: Trusted source percentages
- **User Engagement**: Session duration and message counts

### 2. Health Monitoring

- **Agent Status**: MCP server health checks
- **Database Health**: Session storage performance  
- **API Availability**: Endpoint uptime monitoring
- **Error Rates**: Exception tracking and alerting

## Future Enhancements

### Phase 2 Features

- **Agent Comparison**: Side-by-side response comparison
- **Citation Export**: Export citations to reference managers
- **Advanced Filtering**: Filter by agent capabilities
- **User Preferences**: Personalized agent recommendations

### Phase 3 Features

- **Voice Interface**: Speech-to-text integration
- **Mobile App**: React Native implementation
- **Collaboration**: Multi-user conversations
- **Analytics Dashboard**: Usage analytics and insights

## Conclusion

The Agent Web App provides a comprehensive platform for clinical AI interaction with robust citation tracking, real-time streaming, and multi-agent support. The architecture emphasizes reliability, user experience, and extensibility while maintaining strict separation between presentation and agent logic through the MCP adapter pattern.

The standardized citation system ensures transparency and trust across all agents, while the streaming implementation provides responsive user interactions. The modular design allows for easy addition of new agents and features while maintaining consistent user experience patterns.