# Agent 97 - Implementation Tasks

## Overview
Agent 97 is an OpenAI Agents SDK-based agent that provides medical education assistance using 97 trusted medical sources. It's based on the existing health assistant implementation that uses Claude with web_search and web_fetch tools.

## Design Decision: Wrap Existing Health Assistant in MCP Server

After analyzing the codebase, I recommend **Option 1: Wrapping the existing health assistant** for the following reasons:

### Advantages:
1. **Reuse Existing Implementation**: The health assistant already has:
   - Comprehensive guardrails (input/output checking)
   - Citation management and deduplication
   - 97 trusted domains configuration
   - Multi-turn conversation support
   - Streaming capabilities
   - Session logging

2. **Faster Development**: Less code to rewrite, can focus on integration

3. **Proven Functionality**: The health assistant is already tested and working

4. **Consistent with Dr. OPA Pattern**: Dr. OPA also wraps existing functionality in an MCP server

### Architecture:
```
OpenAI Agent (agent_97) 
    ↓
MCP Server (STDIO transport)
    ↓
PatientAssistant class
    ↓
Anthropic Claude API (with web tools)
```

## Implementation Tasks

### Phase 1: Setup and Structure ✅
- [x] Analyze Dr. OPA implementation pattern
- [x] Understand health assistant implementation
- [x] Research design options
- [x] Create tasks.md with recommendations

### Phase 2: Create Project Structure
- [ ] Create folder structure:
  - [ ] src/agents/agent_97/
  - [ ] src/agents/agent_97/mcp/
  - [ ] tests/agent_97/
  - [ ] docs/agents/agent_97/
  - [ ] scripts/agent_97/

### Phase 3: MCP Server Implementation
- [ ] Create MCP server wrapper for health assistant
  - [ ] Create src/agents/agent_97/mcp/server.py
  - [ ] Define MCP tools:
    - [ ] agent_97.query - Main query tool
    - [ ] agent_97.query_stream - Streaming query tool  
    - [ ] agent_97.get_trusted_domains - Return list of 97 domains
    - [ ] agent_97.health_check - Server health check
  - [ ] Implement tool handlers that call PatientAssistant
  - [ ] Add proper error handling and logging

### Phase 4: OpenAI Agent Implementation
- [ ] Create src/agents/agent_97/openai_agent.py
  - [ ] Follow Dr. OPA pattern for agent setup
  - [ ] Configure MCP server connection (STDIO)
  - [ ] Define system instructions for medical education
  - [ ] Implement query method with MCP tool calls
  - [ ] Add session and error handling

### Phase 5: Documentation
- [ ] Create docs/agents/agent_97/agent_spec.md
  - [ ] Agent overview and purpose
  - [ ] MCP tools specification
  - [ ] System instructions
  - [ ] Usage examples
- [ ] Create docs/agents/agent_97/readme.md
  - [ ] Quick start guide
  - [ ] Installation instructions
  - [ ] Configuration details
- [ ] Create docs/agents/agent_97/mcp_tools_spec.md
  - [ ] Detailed tool descriptions
  - [ ] Request/response schemas
  - [ ] Error conditions

### Phase 6: Testing
- [ ] Create tests/agent_97/test_mcp_server.py
  - [ ] Test each MCP tool independently
  - [ ] Test error conditions
  - [ ] Test streaming functionality
- [ ] Create tests/agent_97/test_openai_agent.py
  - [ ] Test agent initialization
  - [ ] Test query processing
  - [ ] Test tool routing
- [ ] Create tests/agent_97/test_integration.py
  - [ ] End-to-end test scenarios
  - [ ] Test with sample medical questions
  - [ ] Verify citations and guardrails work

### Phase 7: Scripts and Utilities
- [ ] Create scripts/start_agent_97_mcp.sh
- [ ] Create scripts/test_agent_97.py
- [ ] Create scripts/agent_97/demo.py

### Phase 8: Integration Testing
- [ ] Test Agent 97 with various medical queries
- [ ] Verify all 97 domains are accessible
- [ ] Test guardrails (emergency detection, etc.)
- [ ] Test citation extraction
- [ ] Test multi-turn conversations
- [ ] Test streaming responses

## Key Implementation Details

### MCP Tool Specifications

#### agent_97.query
- **Purpose**: Process medical education queries
- **Input**: 
  - query (string): User's medical question
  - session_id (string, optional): Session identifier
  - guardrail_mode (string, optional): "llm", "regex", or "hybrid"
- **Output**: 
  - content: Educational response with disclaimers
  - citations: List of sources used
  - guardrails_applied: Boolean
  - trace_id: Tracking identifier

#### agent_97.query_stream  
- **Purpose**: Stream responses for better UX
- **Input**: Same as query
- **Output**: Stream of events (text, citations, tool_use, complete)

#### agent_97.get_trusted_domains
- **Purpose**: Return list of 97 trusted medical domains
- **Output**: Array of domain strings with categories

#### agent_97.health_check
- **Purpose**: Verify server and dependencies are working
- **Output**: Status object with component health

### System Instructions Template

```
You are Agent 97, a medical education AI assistant that provides reliable health information from 97 trusted medical sources.

CORE PRINCIPLES:
1. Provide educational information only - never diagnose or prescribe
2. Always cite sources from the 97 trusted domains
3. Apply appropriate medical disclaimers
4. Detect and handle emergencies appropriately
5. Use clear, accessible language for patients

TRUSTED SOURCES:
You have access to information from 97 carefully vetted medical domains including:
- Major medical institutions (Mayo Clinic, Johns Hopkins, etc.)
- Government health authorities (CDC, NIH, WHO, etc.)
- Medical journals (NEJM, Lancet, JAMA, etc.)
- Canadian health authorities (Ontario Health, CPSO, etc.)

Use the agent_97.query tool to process medical questions with built-in safety guardrails.
```

## Testing Scenarios

1. **Basic Medical Query**: "What are the symptoms of diabetes?"
2. **Emergency Detection**: "I'm having chest pain and can't breathe"
3. **Mental Health Crisis**: "I want to hurt myself"
4. **Drug Information**: "What are the side effects of metformin?"
5. **Multi-turn Conversation**: Follow-up questions about a topic
6. **Citation Verification**: Ensure sources are from the 97 domains

## Success Criteria

- [ ] Agent responds to medical queries with educational information
- [ ] All responses include appropriate disclaimers
- [ ] Citations are properly extracted and displayed
- [ ] Emergency content triggers appropriate redirects
- [ ] Streaming works for real-time response display
- [ ] Integration with OpenAI Agents SDK is stable
- [ ] All 97 trusted domains are accessible
- [ ] Guardrails (input and output) function correctly

## Notes

- The MCP server will run in STDIO mode like Dr. OPA
- We'll use FastMCP for the server implementation
- The agent will be compatible with the existing OpenAI Agents framework
- Session logging will be preserved from the health assistant
- We'll maintain backward compatibility with the health assistant's features

## Next Steps

1. Start with Phase 2: Create the folder structure
2. Implement the MCP server wrapper (Phase 3)
3. Create the OpenAI agent (Phase 4)
4. Document everything (Phase 5)
5. Test thoroughly (Phase 6-8)