#!/bin/bash

# Start Dr. OPA MCP Server
# Loads environment variables and starts the FastMCP server

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from project .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
    echo "Loaded environment variables from $PROJECT_ROOT/.env"
else
    echo "Warning: No .env file found at $PROJECT_ROOT/.env"
fi

# Activate virtual environment if it exists
if [ -d "$HOME/spacy_env" ]; then
    source "$HOME/spacy_env/bin/activate"
    echo "Activated virtual environment"
fi

# Set Python path to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Log startup
echo "Starting Dr. OPA MCP Server..."
echo "Project root: $PROJECT_ROOT"
echo "Python path: $PYTHONPATH"

# Change to project directory
cd "$PROJECT_ROOT"

# Run the MCP server
python -m src.agents.dr_opa_agent.mcp.server