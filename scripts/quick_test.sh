#!/bin/bash
#
# Quick Test Script for Doctor Agents
#
# Usage:
#   ./scripts/quick_test.sh dr_opa          # Test Dr. OPA agent
#   ./scripts/quick_test.sh dr_off odb      # Test Dr. OFF ODB tool
#   ./scripts/quick_test.sh all             # Test all agents
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Activate virtual environment
source /Users/liammckendry/spacy_env/bin/activate

# Note: .env is loaded automatically by the Python scripts

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Doctor Agent Quick Test${NC}"
echo -e "${BLUE}======================================${NC}\n"

AGENT=${1:-"all"}
TOOL=${2:-""}

case "$AGENT" in
    "dr_opa")
        echo -e "${GREEN}Testing Dr. OPA Agent...${NC}\n"
        python scripts/test_agents.py --agent dr_opa
        ;;

    "dr_off")
        if [ -z "$TOOL" ]; then
            echo -e "${GREEN}Testing Dr. OFF Agent...${NC}\n"
            python scripts/test_agents.py --agent dr_off
        else
            echo -e "${GREEN}Testing Dr. OFF Tool: ${TOOL}${NC}\n"
            python scripts/test_mcp_tools_direct.py --agent dr_off --tool "${TOOL}_get" --run-all-tests
        fi
        ;;

    "agent_97")
        echo -e "${GREEN}Testing Agent 97...${NC}\n"
        python scripts/test_agents.py --agent agent_97
        ;;

    "chief")
        echo -e "${GREEN}Testing Chief Agent...${NC}\n"
        python scripts/test_agents.py --agent chief
        ;;

    "all")
        echo -e "${GREEN}Testing All Agents...${NC}\n"
        python scripts/test_agents.py --agent all
        ;;

    "tools")
        echo -e "${GREEN}Testing All MCP Tools...${NC}\n"
        python scripts/test_agents.py --mode tools --agent all
        ;;

    "api")
        echo -e "${YELLOW}Note: Ensure API server is running first:${NC}"
        echo -e "${YELLOW}  uvicorn src.web.api.main:app --reload --port 8001${NC}\n"
        echo -e "${GREEN}Testing API Endpoints...${NC}\n"
        python scripts/test_agents.py --mode api --agent all
        ;;

    *)
        echo -e "${RED}Unknown option: $AGENT${NC}\n"
        echo "Usage:"
        echo "  ./scripts/quick_test.sh dr_opa          # Test Dr. OPA agent"
        echo "  ./scripts/quick_test.sh dr_off          # Test Dr. OFF agent"
        echo "  ./scripts/quick_test.sh dr_off odb      # Test Dr. OFF ODB tool"
        echo "  ./scripts/quick_test.sh dr_off adp      # Test Dr. OFF ADP tool"
        echo "  ./scripts/quick_test.sh agent_97        # Test Agent 97"
        echo "  ./scripts/quick_test.sh chief           # Test Chief"
        echo "  ./scripts/quick_test.sh all             # Test all agents"
        echo "  ./scripts/quick_test.sh tools           # Test all MCP tools"
        echo "  ./scripts/quick_test.sh api             # Test API endpoints"
        exit 1
        ;;
esac

echo -e "\n${GREEN}✓ Testing complete!${NC}"
echo -e "${BLUE}Results saved to eval/results/${NC}\n"
