#!/bin/bash
# Railway startup script that runs MCP servers in HTTP mode and the main API

echo "Starting Railway deployment..."
echo "================================"

# Set environment variables for HTTP MCP mode
export RAILWAY_ENVIRONMENT=true
export USE_HTTP_MCP=true
export MCP_DR_OFF_PORT=8001
export MCP_DR_OPA_PORT=8002
export MCP_DR_OFF_URL=http://localhost:8001
export MCP_DR_OPA_URL=http://localhost:8002

# Start MCP servers in background
echo "Starting MCP servers in HTTP mode..."
python -m src.ai_agents.dr_off_agent.mcp.server_http &
MCP_OFF_PID=$!
echo "Dr. OFF MCP server started on port 8001 (PID: $MCP_OFF_PID)"

python -m src.ai_agents.dr_opa_agent.mcp.server_http &
MCP_OPA_PID=$!
echo "Dr. OPA MCP server started on port 8002 (PID: $MCP_OPA_PID)"

# Wait for MCP servers to be ready
echo "Waiting for MCP servers to be ready..."
sleep 5

# Start the main FastAPI server
echo "Starting main FastAPI server..."
uvicorn src.web.api.main:app --host 0.0.0.0 --port $PORT

# Cleanup on exit
trap "kill $MCP_OFF_PID $MCP_OPA_PID" EXIT