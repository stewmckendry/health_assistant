#!/bin/bash

# Test quality standards MCP tool via Dr. OPA endpoint

RAILWAY_URL="https://healthassistant-production-3613.up.railway.app"
ENDPOINT="/agents/dr-opa/stream"

echo "Testing quality standards search through Dr. OPA agent..."
echo "Query: What are the quality standards for diabetes care?"
echo ""

curl -X POST "${RAILWAY_URL}${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "sessionId": "test-quality-standards-'$(date +%s)'",
    "query": "What are the quality standards for diabetes care in Ontario?",
    "stream": true
  }'

echo ""
echo ""
echo "Testing specific standard retrieval..."
echo "Query: Tell me all the quality statements for diabetes management"
echo ""

curl -X POST "${RAILWAY_URL}${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "sessionId": "test-quality-statements-'$(date +%s)'",
    "query": "What are all the quality statements for diabetes management from Ontario Health?",
    "stream": true
  }'