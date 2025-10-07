#!/bin/bash

# Test Ontario Health Quality Standards MCP tools via Railway API

RAILWAY_URL="https://healthassistant-production-3613.up.railway.app"

echo "=================================================="
echo "TESTING QUALITY STANDARDS MCP TOOLS VIA RAILWAY"
echo "=================================================="

# Test 1: Search for diabetes quality standards
echo -e "\n🧪 Test 1: Search diabetes quality standards"
curl -X POST "$RAILWAY_URL/api/dr-opa/mcp/opa_quality_standards" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "diabetes",
    "retrieve_all_statements": false,
    "statement_type": "all",
    "top_k": 5
  }' 2>/dev/null | jq '.standard_title, .total_statements, .confidence' || echo "Test 1 failed"

# Test 2: Get all statements for depression
echo -e "\n🧪 Test 2: Get all depression quality statements"
curl -X POST "$RAILWAY_URL/api/dr-opa/mcp/opa_quality_standards" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "major depression",
    "retrieve_all_statements": true,
    "statement_type": "all",
    "top_k": 20
  }' 2>/dev/null | jq '.standard_title, .total_statements, (.statements | length)' || echo "Test 2 failed"

# Test 3: Search hip fracture quality indicators  
echo -e "\n🧪 Test 3: Search hip fracture quality indicators"
curl -X POST "$RAILWAY_URL/api/dr-opa/mcp/opa_quality_standards" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "hip fracture",
    "retrieve_all_statements": false,
    "statement_type": "statement",
    "top_k": 10
  }' 2>/dev/null | jq '.total_statements, .statements[0].title' || echo "Test 3 failed"

# Test 4: Test general search with quality standards source
echo -e "\n🧪 Test 4: General search including quality standards"
curl -X POST "$RAILWAY_URL/api/dr-opa/mcp/opa_search_sections" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "diabetes management",
    "sources": ["quality_standards"],
    "top_k": 5
  }' 2>/dev/null | jq '(.sections | length), .provenance' || echo "Test 4 failed"

# Test 5: Check citation URLs are correct
echo -e "\n🧪 Test 5: Verify citation URLs"
curl -X POST "$RAILWAY_URL/api/dr-opa/mcp/opa_quality_standards" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "alcohol use disorder",
    "retrieve_all_statements": false,
    "statement_type": "overview",
    "top_k": 3
  }' 2>/dev/null | jq '.citations[0].url' || echo "Test 5 failed"

echo -e "\n=================================================="
echo "TESTING COMPLETE"
echo "=================================================="