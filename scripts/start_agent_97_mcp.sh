#!/bin/bash

# Agent 97 MCP Server Startup Script
# Starts the MCP server for Agent 97 medical education assistant

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Header
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}     Agent 97 MCP Server Launcher        ${NC}"
echo -e "${BLUE}  Medical Education from 97 Sources      ${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Get the script directory (project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}Project root:${NC} $PROJECT_ROOT"

# Change to project root
cd "$PROJECT_ROOT" || exit 1

# Check for required environment variables
echo -e "\n${YELLOW}Checking environment...${NC}"

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}ERROR: ANTHROPIC_API_KEY not set${NC}"
    echo "Please set your Anthropic API key:"
    echo "  export ANTHROPIC_API_KEY='your-key-here'"
    exit 1
else
    echo -e "${GREEN}✓${NC} ANTHROPIC_API_KEY configured"
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}WARNING: OPENAI_API_KEY not set${NC}"
    echo "This is only needed if running the OpenAI agent directly"
else
    echo -e "${GREEN}✓${NC} OPENAI_API_KEY configured"
fi

# Check if virtual environment exists
if [ -d "$HOME/spacy_env" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment found at ~/spacy_env"
    source "$HOME/spacy_env/bin/activate"
elif [ -d "venv" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment found"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment found"
    source .venv/bin/activate
else
    echo -e "${YELLOW}No virtual environment found${NC}"
    echo "Consider using: source ~/spacy_env/bin/activate"
fi

# Check for required Python packages
echo -e "\n${YELLOW}Checking dependencies...${NC}"

python -c "import fastmcp" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: fastmcp not installed${NC}"
    echo "Install with: pip install fastmcp"
    exit 1
else
    echo -e "${GREEN}✓${NC} fastmcp installed"
fi

python -c "import anthropic" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: anthropic not installed${NC}"
    echo "Install with: pip install anthropic"
    exit 1
else
    echo -e "${GREEN}✓${NC} anthropic installed"
fi

python -c "import yaml" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: pyyaml not installed${NC}"
    echo "Install with: pip install pyyaml"
    exit 1
else
    echo -e "${GREEN}✓${NC} pyyaml installed"
fi

# Create logs directory if it doesn't exist
mkdir -p logs/agent_97

# Display startup information
echo -e "\n${BLUE}Starting Agent 97 MCP Server...${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "Server: ${GREEN}agent-97-server${NC}"
echo -e "Transport: ${GREEN}STDIO${NC}"
echo -e "Features:"
echo -e "  • ${GREEN}97 trusted medical sources${NC}"
echo -e "  • ${GREEN}Comprehensive safety guardrails${NC}"
echo -e "  • ${GREEN}Automatic citation extraction${NC}"
echo -e "  • ${GREEN}Emergency detection & routing${NC}"
echo -e ""
echo -e "Available MCP Tools:"
echo -e "  • ${BLUE}agent_97_query${NC} - Process medical queries"
echo -e "  • ${BLUE}agent_97_query_stream${NC} - Stream responses"
echo -e "  • ${BLUE}agent_97_get_trusted_domains${NC} - List sources"
echo -e "  • ${BLUE}agent_97_health_check${NC} - System status"
echo -e "  • ${BLUE}agent_97_get_disclaimers${NC} - Get disclaimers"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e ""
echo -e "${YELLOW}Logs will be saved to: logs/agent_97/${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo -e ""

# Start the MCP server
python -m src.agents.agent_97.mcp.server

# Exit message
echo -e "\n${YELLOW}Agent 97 MCP Server stopped${NC}"