# Clinical AI Agents Web App - Implementation Tasks

## Overview
Build a web application to access Ontario clinical AI agents (Dr OPA, Agent 97, Dr OFF) with streaming responses, multi-turn conversations, tool call visibility, and citation extraction.

## Architecture Design
- **Frontend**: Next.js 14 with App Router, React, TypeScript
- **UI Components**: Existing design system from Health Assistant
- **Backend Integration**: OpenAI Agents SDK with SQLiteSession for multi-turn
- **Streaming**: Native OpenAI SDK RunResultStreaming with SSE
- **State Management**: React hooks + Context API for agent sessions
- **Tool Visibility**: Real-time display of MCP tool calls
- **Citations**: Extract from agent responses and deduplicate

## Phase 1: Setup and Structure [Priority: High]

### 1.1 Create Folder Structure
- [ ] Create `web/app/agents/` directory for new agent UI page
- [ ] Create `web/components/agents/` for agent-specific components
- [ ] Create `web/app/api/agents/` for agent API routes
- [ ] Create `docs/agents/agent_web_app/` for documentation
- [ ] Create `tests/agent_web_app/` for tests
- [ ] Create `scripts/agent_web_app/` for utility scripts

### 1.2 Setup Agent Configuration
- [ ] Create `web/config/agents.config.ts` with agent metadata
  - Agent ID, name, description, status (active/coming-soon)
  - Mission statement, tools list, knowledge sources
  - API endpoint configuration
  - Icon and color theme
- [ ] Create `web/types/agents.ts` for TypeScript types
  - AgentInfo, AgentResponse, ToolCall, Citation interfaces
  - Conversation and Session types

## Phase 2: Frontend Components [Priority: High]

### 2.1 Agent List Component
- [ ] Create `AgentList.tsx` component
  - Grid/list view of available agents
  - Visual indicator for active vs coming-soon
  - Agent cards with icon, name, brief description
  - Click to view details or start chat

### 2.2 Agent Detail Card
- [ ] Create `AgentDetailCard.tsx` modal/popup component
  - Full agent description and mission
  - List of available tools with descriptions
  - Knowledge sources and trusted domains
  - "Start Conversation" button
  - Status indicator (Alpha/Beta/Production)

### 2.3 Agent Chat Interface
- [ ] Create `AgentChatInterface.tsx` main chat component
  - Reuse existing ChatInterface design patterns
  - Add agent name/icon in header
  - Session management for multi-turn conversations
  - Message history with role indicators

### 2.4 Tool Call Display Component
- [ ] Create `ToolCallDisplay.tsx` for showing tool usage
  - Collapsible panel showing tool calls in progress
  - Tool name, arguments, and status
  - Timestamp and duration
  - Success/error indicators

### 2.5 Citation Component
- [ ] Create `CitationList.tsx` for extracted citations
  - Deduplicated list of sources
  - Clickable links to original sources
  - Domain favicon display
  - Trust indicator for 97 domains

### 2.6 Streaming Message Component
- [ ] Create `StreamingMessage.tsx` for real-time responses
  - Progressive text rendering
  - Loading indicators for tool calls
  - Smooth animation for new content

## Phase 3: Backend API Routes [Priority: High]

### 3.1 Agent Management Routes
- [ ] Create `GET /api/agents` - List all configured agents
- [ ] Create `GET /api/agents/[agentId]` - Get agent details
- [ ] Create `GET /api/agents/[agentId]/health` - Check agent availability

### 3.2 Conversation Routes (Using OpenAI SDK)
- [ ] Create `POST /api/agents/[agentId]/conversations` - Start new conversation
  - Initialize SQLiteSession for context persistence
  - Return session ID for tracking
- [ ] Create `POST /api/agents/[agentId]/conversations/[sessionId]/messages` - Send message
  - Use Agent.run() with session for context
  - Return tool calls and response
- [ ] Create `GET /api/agents/[agentId]/conversations/[sessionId]/history` - Get history

### 3.3 Streaming Route (Native SDK Support)
- [ ] Create `POST /api/agents/[agentId]/stream` - Stream response
  - Use Runner.run_streamed() from SDK
  - Return SSE stream with StreamEvents
  - Include RawResponsesStreamEvent for real-time text
  - Include tool call events

### 3.4 Tool Call Monitoring
- [ ] Create WebSocket or SSE endpoint for tool call updates
  - Real-time tool execution status
  - Arguments and results
  - Timing information

## Phase 4: Agent Integration [Priority: High]

### 4.1 Dr OPA Agent Integration
- [ ] Update `dr_opa_agent/openai_agent.py` for web compatibility
  - Add session management using SQLiteSession
  - Implement streaming with RunResultStreaming
  - Ensure tool call extraction works
- [ ] Create agent adapter in web app
  - Map agent responses to UI format
  - Extract citations from response

### 4.2 Agent 97 Integration
- [ ] Update `agent_97/openai_agent.py` for web compatibility
  - Add SQLiteSession support
  - Implement streaming responses
  - Ensure guardrails work in web context
- [ ] Create agent adapter
  - Handle emergency detection responses
  - Extract and format citations

### 4.3 Dr OFF Agent Preparation
- [ ] Create placeholder configuration
  - Coming soon status
  - Preview of capabilities
  - Expected launch date

## Phase 5: Core Features [Priority: High]

### 5.1 Streaming Responses
- [ ] Implement SSE client in frontend
  - Handle StreamEvent types from SDK
  - Progressive rendering of text
  - Error recovery and reconnection
- [ ] Add streaming control UI
  - Pause/resume streaming
  - Cancel current request

### 5.2 Multi-turn Conversations
- [ ] Implement session persistence
  - Use SQLiteSession from OpenAI SDK
  - Store session ID in React context
  - Auto-save conversation state
- [ ] Add conversation history UI
  - Scrollable message history
  - Clear conversation option
  - Export conversation feature

### 5.3 Tool Call Visibility
- [ ] Parse tool calls from agent response
  - Extract from result.history items
  - Format for display
- [ ] Real-time tool execution display
  - Show when tools are called
  - Display arguments passed
  - Show results/errors

### 5.4 Citation Extraction
- [ ] Implement citation parser
  - Regex for URLs in responses
  - Extract markdown links
  - Parse source references
- [ ] Deduplication logic
  - Group by domain
  - Remove duplicate URLs
  - Maintain citation order

## Phase 6: UI/UX Enhancements [Priority: Medium]

### 6.1 Consistent Design System
- [ ] Apply existing Health Assistant styles
  - Use same color palette
  - Consistent button styles
  - Matching card components
  - Same font hierarchy

### 6.2 Disclaimers and Warnings
- [ ] Add prototype disclaimer banner
  - "Prerelease for interested parties"
  - "Not ready for production"
  - "Educational purposes only"
- [ ] Agent-specific disclaimers
  - Medical education disclaimer for Agent 97
  - Clinical guidance disclaimer for Dr OPA

### 6.3 Loading States
- [ ] Skeleton loaders for agent list
- [ ] Typing indicators during response
- [ ] Tool execution progress bars
- [ ] Connection status indicators

### 6.4 Error Handling
- [ ] User-friendly error messages
- [ ] Retry mechanisms
- [ ] Fallback UI states
- [ ] Error boundaries for components

## Phase 7: Testing [Priority: High]

### 7.1 Unit Tests
- [ ] Test agent configuration loading
- [ ] Test citation extraction logic
- [ ] Test deduplication algorithm
- [ ] Test session management

### 7.2 Integration Tests
- [ ] Test agent API endpoints
- [ ] Test streaming response handling
- [ ] Test multi-turn conversation flow
- [ ] Test tool call extraction

### 7.3 E2E Tests
- [ ] Test complete user journey
  - Select agent → View details → Start chat
  - Send message → See tools → Get response
  - Continue conversation → See citations
- [ ] Test error scenarios
- [ ] Test streaming interruption

### 7.4 Agent-specific Tests
- [ ] Test Dr OPA specific features
- [ ] Test Agent 97 guardrails
- [ ] Test emergency detection

## Phase 8: Documentation [Priority: Medium]

### 8.1 Technical Documentation
- [ ] API documentation with examples
- [ ] Component documentation
- [ ] Integration guide for new agents
- [ ] Architecture diagrams

### 8.2 User Documentation
- [ ] User guide for clinical agents
- [ ] FAQ section
- [ ] Troubleshooting guide
- [ ] Best practices for queries

### 8.3 Developer Documentation
- [ ] Setup instructions
- [ ] Configuration guide
- [ ] Adding new agents guide
- [ ] Deployment instructions

## Phase 9: Performance & Optimization [Priority: Low]

### 9.1 Performance
- [ ] Implement response caching
- [ ] Optimize bundle size
- [ ] Lazy load agent components
- [ ] Optimize streaming performance

### 9.2 Monitoring
- [ ] Add analytics tracking
- [ ] Error logging
- [ ] Performance metrics
- [ ] Usage statistics

## Phase 10: Future Enhancements [Priority: Low]

### 10.1 Additional Features
- [ ] Voice input/output
- [ ] Conversation export (PDF/JSON)
- [ ] Favorite agents
- [ ] Conversation search
- [ ] Agent comparison mode

### 10.2 Mobile Optimization
- [ ] Responsive design refinements
- [ ] Touch-optimized controls
- [ ] Mobile-specific layouts

## Current Status
- **Phase 1-4**: Ready to begin implementation
- **Phase 5-6**: Core functionality, high priority
- **Phase 7-8**: Essential for production readiness
- **Phase 9-10**: Future improvements

## Next Steps
1. Create folder structure (Phase 1.1)
2. Set up agent configuration (Phase 1.2)
3. Build AgentList component (Phase 2.1)
4. Implement basic API routes (Phase 3.1)
5. Test with Dr OPA agent first

## Success Criteria
- [ ] Users can view list of available agents
- [ ] Users can see agent details before starting
- [ ] Chat interface works with streaming responses
- [ ] Multi-turn conversations maintain context
- [ ] Tool calls are visible during execution
- [ ] Citations are extracted and clickable
- [ ] UI matches Health Assistant design
- [ ] All safety disclaimers are present
- [ ] Dr OPA and Agent 97 work correctly
- [ ] Tests pass with >80% coverage