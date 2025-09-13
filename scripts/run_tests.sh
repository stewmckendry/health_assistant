#!/bin/bash
# Script to run all tests and generate coverage report

echo "========================================="
echo "🧪 Health Assistant Test Suite"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create directories if they don't exist
mkdir -p logs
mkdir -p data/conversations
mkdir -p htmlcov

echo -e "\n${YELLOW}📋 Running Unit Tests...${NC}"
echo "========================================="
pytest tests/unit/ -v --tb=short

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Unit tests passed!${NC}"
else
    echo -e "${RED}❌ Unit tests failed!${NC}"
    exit 1
fi

echo -e "\n${YELLOW}📋 Running Integration Tests...${NC}"
echo "========================================="
if [ -d "tests/integration" ] && [ "$(ls -A tests/integration)" ]; then
    pytest tests/integration/ -v --tb=short
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Integration tests passed!${NC}"
    else
        echo -e "${RED}❌ Integration tests failed!${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  No integration tests found${NC}"
fi

echo -e "\n${YELLOW}📋 Running E2E Tests...${NC}"
echo "========================================="
if [ -d "tests/e2e" ] && [ "$(ls -A tests/e2e)" ]; then
    pytest tests/e2e/ -v --tb=short
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ E2E tests passed!${NC}"
    else
        echo -e "${RED}❌ E2E tests failed!${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  No E2E tests found${NC}"
fi

echo -e "\n${YELLOW}📊 Generating Coverage Report...${NC}"
echo "========================================="
pytest --cov=src --cov-report=html --cov-report=term tests/

echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}✨ All tests completed!${NC}"
echo -e "${GREEN}=========================================${NC}"

echo -e "\n📈 Coverage report available at: htmlcov/index.html"
echo -e "📝 Logs available at: logs/health_assistant.log"

# Display coverage summary
echo -e "\n${YELLOW}Coverage Summary:${NC}"
pytest --cov=src --cov-report=term-missing tests/unit/ --quiet | tail -n 20