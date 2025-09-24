#!/bin/bash
# Test MCP server with mcp-cli commands

cd src/agents/ontario_orchestrator/mcp
source ~/spacy_env/bin/activate

# Test 1: List tools
echo "==================================="
echo "TEST 1: Listing available tools"
echo "==================================="
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | python server.py 2>/dev/null | python -m json.tool | head -100

echo ""
echo "==================================="
echo "TEST 2: Call schedule.get tool"
echo "==================================="
echo '{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "schedule.get", "arguments": {"q": "C124 discharge billing", "codes": ["C124"], "top_k": 3}}}' | python server.py 2>/dev/null | python -m json.tool | head -150

echo ""
echo "==================================="
echo "TEST 3: Call odb.get tool"
echo "==================================="
echo '{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "odb.get", "arguments": {"drug": "metformin", "check_alternatives": true, "top_k": 3}}}' | python server.py 2>/dev/null | python -m json.tool | head -150