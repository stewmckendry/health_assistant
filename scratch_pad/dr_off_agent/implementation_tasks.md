# Dr. OFF Agent Implementation Task List

## Overview
Integrate Dr. OFF (Ontario Finance & Formulary) Agent into the Ontario Clinical AI Agents registry by wrapping the existing MCP server with OpenAI Agents SDK and implementing frontend/backend integration.

## Critical Notes from Handoff
- ⚠️ **Module Path**: Use `src.ai_agents.dr_off_agent.dr_off_mcp.server` NOT `src.ai_agents.dr_off_agent.mcp.server`
- The actual MCP server directory is `dr_off_mcp` not `mcp`
- Dr. OFF MCP server runs on port 8002
- Always activate spacy_env: `source /Users/liammckendry/spacy_env/bin/activate`

## Phase 1: MCP Server Preparation ✅
- [x] Review existing MCP server structure
- [x] Verify correct module path in startup script
- [ ] Fix startup script module path (change mcp to dr_off_mcp)
- [ ] Create response formatter utility for standardized citations
- [ ] Update MCP tools to use standardized citation format

## Phase 2: OpenAI Agent Wrapper
- [ ] Create `src/agents/dr_off_agent/openai_agent.py`
- [ ] Implement DrOffAgent class with MCP integration
- [ ] Define comprehensive system instructions
- [ ] Add citation extraction logic
- [ ] Implement streaming query method
- [ ] Add error handling and fallback responses

## Phase 3: Backend Integration
- [ ] Create `src/web/api/dr_off_endpoint.py`
- [ ] Implement streaming endpoint for Dr. OFF
- [ ] Add session management
- [ ] Transform MCP responses to frontend format
- [ ] Register endpoint in main.py

## Phase 4: Frontend Updates
- [ ] Update `web/config/agents.config.ts` - change status to 'active'
- [ ] Verify agent card displays correctly
- [ ] Test chat interface routing
- [ ] Verify streaming works end-to-end
- [ ] Check citation display

## Phase 5: Citation Standardization
- [ ] Create `src/agents/dr_off_agent/dr_off_mcp/utils/response_formatter.py`
- [ ] Update schedule_get tool to return standardized citations
- [ ] Update adp_get tool to return standardized citations
- [ ] Update odb_get tool to return standardized citations
- [ ] Test citation extraction in OpenAI agent

## Phase 6: Testing & Documentation
- [ ] Test MCP server connection
- [ ] Test OpenAI agent initialization
- [ ] Test streaming responses
- [ ] Test citation extraction
- [ ] Test error handling
- [ ] Update agent specification docs
- [ ] Update web app specification
- [ ] Create README for Dr. OFF agent

## Implementation Order

### Step 1: Fix MCP Server Module Path
1. Update `scripts/start_dr_off_mcp.sh`
2. Test MCP server starts correctly
3. Verify tools are accessible

### Step 2: Create Citation Formatter
1. Copy pattern from Dr. OPA
2. Standardize citation format
3. Update all MCP tools

### Step 3: Create OpenAI Agent Wrapper
1. Copy template from Dr. OPA
2. Customize for Dr. OFF tools
3. Implement system instructions

### Step 4: Create Backend Endpoint
1. Copy pattern from dr_opa_endpoint.py
2. Register in main.py
3. Test streaming

### Step 5: Update Frontend
1. Change status to 'active' in config
2. Test agent selection
3. Verify chat interface

### Step 6: End-to-End Testing
1. Start all services
2. Test complete flow
3. Fix any issues

## Files to Create/Modify

### New Files
- `src/agents/dr_off_agent/openai_agent.py`
- `src/agents/dr_off_agent/dr_off_mcp/utils/response_formatter.py`
- `src/web/api/dr_off_endpoint.py`
- `docs/agents/dr_off_agent/agent_spec.md`

### Modify Existing
- `scripts/start_dr_off_mcp.sh` (fix module path)
- `src/agents/dr_off_agent/mcp/server.py` (if needed for citations)
- `src/agents/dr_off_agent/mcp/tools/*.py` (add citation formatting)
- `src/web/api/main.py` (register Dr. OFF endpoint)
- `web/config/agents.config.ts` (activate Dr. OFF)
- `docs/agents/agent_web_app/specification.md` (add Dr. OFF details)

## Testing Checklist
- [ ] MCP server starts without errors
- [ ] `mcp list` shows dr-off-agent
- [ ] `mcp call dr-off-agent schedule_get '{"q": "A001"}'` works
- [ ] OpenAI agent initializes
- [ ] FastAPI endpoint streams responses
- [ ] Frontend shows Dr. OFF as available
- [ ] Chat interface loads for Dr. OFF
- [ ] Messages stream properly
- [ ] Citations display correctly
- [ ] Tool calls show in UI
- [ ] Error handling works

## Success Criteria
1. Dr. OFF Agent appears as "active" in web app
2. Users can select and chat with Dr. OFF
3. Responses stream in real-time
4. Citations from ODB, OHIP, and ADP display correctly
5. Tool calls are visible during execution
6. Natural language queries work for all tools
7. Error messages are helpful and actionable