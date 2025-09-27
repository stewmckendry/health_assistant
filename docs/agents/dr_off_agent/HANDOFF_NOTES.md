# Dr. OFF Agent Implementation Handoff Notes

## Context for New Session
You're implementing Dr. OFF Agent by wrapping the existing Dr. OFF MCP server with OpenAI Agents SDK and integrating it into the agent web app.

## Current State

### What's Already Built
1. **Dr. OFF MCP Server** (`src/agents/dr_off_agent/mcp/server.py`)
   - Fully functional MCP server with 3 tools:
     - `schedule_get`: OHIP Schedule of Benefits lookup
     - `adp_get`: ADP (Assistive Devices Program) eligibility
     - `odb_get`: ODB (Ontario Drug Benefit) formulary
   - Server runs on port 8002
   - Startup script: `scripts/start_dr_off_mcp.sh`

2. **Response Models** (`src/agents/dr_off_agent/mcp/models/response.py`)
   - Pydantic models for structured responses
   - Natural language query support implemented in ADP tool

3. **Web App Infrastructure**
   - Agent selection UI exists at `/agents`
   - Dr. OFF Agent shows "Coming Soon" - needs implementation
   - AgentMessage component handles citations and tool calls
   - Streaming infrastructure in place (SSE)

## Critical Lessons Learned

### 1. MCP Server Module Path Issue ⚠️
**PROBLEM**: MCP server connection failures in Claude Code
**CAUSE**: Wrong module path in startup script
**SOLUTION**: 
```bash
# WRONG (causes connection failure):
python -m src.agents.dr_off_agent.mcp.server

# CORRECT:
python -m src.agents.dr_off_agent.dr_off_mcp.server
```
The actual directory is `dr_off_mcp`, not `mcp`!

### 2. Citation Standardization 
All Dr. OPA MCP tools now use standardized citation format. You should follow the same pattern for Dr. OFF:
- Create `src/agents/dr_off_agent/dr_off_mcp/utils/response_formatter.py`
- Standardize all tool responses to include top-level `citations` field
- Format: `{source, source_org, loc, url}`
- See Dr. OPA implementation for reference

### 3. Natural Language Query Support
ADP tool already supports natural language queries:
```python
# Both work:
{"query": "Can my patient get funding for a wheelchair?"}
{"device": {"category": "mobility", "type": "wheelchair"}}
```
Consider extending this pattern to other tools.

## Implementation Steps

### Step 1: Create OpenAI Agent Wrapper
Create `src/agents/dr_off_agent/openai_agent.py`:
```python
from agents import Agent
from agents.mcp.server import MCPServerStreamableHttp

class DrOffAgent:
    def __init__(self):
        self.mcp_server = MCPServerStreamableHttp(
            url="http://localhost:8002",
            name="dr-off-server"
        )
        
        self.agent = Agent(
            name="Dr. OFF",
            instructions="""You are Dr. OFF (Ontario Fee-for-Service), 
            an AI assistant specializing in Ontario healthcare billing, 
            drug coverage, and assistive devices...""",
            tools=[self.mcp_server]
        )
```

### Step 2: Create FastAPI Endpoint
Create `src/web/api/dr_off_endpoint.py`:
- Pattern match from `agent_97_endpoint.py` or Dr. OPA endpoint
- Transform streaming events for frontend
- Handle SSE streaming properly

### Step 3: Update Frontend
1. Update `web/lib/agents/registry.ts`:
   - Change `available: false` to `true` for Dr. OFF
   - Add endpoint URL

2. Create agent adapter in `web/lib/agents/adapters/`

### Step 4: Test MCP Connection
```bash
# Start MCP server first
bash scripts/start_dr_off_mcp.sh

# In another terminal, test with Claude Code MCP
mcp list  # Should show dr-off-agent
```

## Common Pitfalls to Avoid

1. **Don't forget to activate spacy_env**:
   ```bash
   source /Users/liammckendry/spacy_env/bin/activate
   ```

2. **Check MCP server is running before testing**:
   ```bash
   ps aux | grep dr_off_mcp
   ```

3. **Module import paths**: Use full paths from project root:
   ```python
   from src.agents.dr_off_agent.dr_off_mcp.models.response import ...
   ```

4. **Streaming response format**: Frontend expects specific SSE event types:
   - `response_start`
   - `text` (with delta field)
   - `tool_call_start`/`tool_call_done`
   - `citation`
   - `response_done`

5. **Port conflicts**: Ensure ports are available:
   - 8000: Main FastAPI backend
   - 8001: Dr. OPA MCP server  
   - 8002: Dr. OFF MCP server
   - 3000: Next.js frontend

## Testing Checklist

- [ ] MCP server starts without errors
- [ ] MCP tools callable via Claude Code
- [ ] OpenAI Agent wrapper initializes
- [ ] FastAPI endpoint streams responses
- [ ] Frontend displays Dr. OFF as available
- [ ] Chat interface works end-to-end
- [ ] Citations display correctly
- [ ] Tool calls show in UI
- [ ] Error handling works

## Reference Files

- **Working example**: `src/agents/dr_opa_agent/` (full MCP + OpenAI implementation)
- **Streaming endpoint**: `src/web/api/agent_97_endpoint.py`
- **Frontend adapter**: `web/lib/agents/adapters/agent97Adapter.ts`
- **Citation standardization**: `src/agents/dr_opa_agent/dr_opa_mcp/utils/response_formatter.py`

## Quick Start Commands

```bash
# Terminal 1: Start MCP server
source /Users/liammckendry/spacy_env/bin/activate
bash scripts/start_dr_off_mcp.sh

# Terminal 2: Start FastAPI backend
source /Users/liammckendry/spacy_env/bin/activate
python -m src.web.api.main

# Terminal 3: Start Next.js frontend
cd web
npm run dev

# Terminal 4: Test MCP tools
mcp list
mcp call dr-off-agent schedule_get '{"q": "A001", "top_k": 3}'
```

## Final Tips

1. Start with getting MCP server connection working first
2. Test each layer independently before integration
3. Use existing Dr. OPA or Agent 97 as reference implementations
4. Check browser console for SSE parsing errors
5. Monitor FastAPI logs for streaming issues

Good luck! The infrastructure is all there - you just need to wire it together properly.