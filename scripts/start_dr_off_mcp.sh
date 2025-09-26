#!/bin/bash

# Start Dr. OFF MCP Server
# Loads environment variables and starts the FastMCP server

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables from project .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    # Use set -a to export all variables, handle quoted values properly
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
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
echo "Starting Dr. OFF MCP Server..."
echo "Project root: $PROJECT_ROOT"
echo "Python path: $PYTHONPATH"

# Change to project directory
cd "$PROJECT_ROOT"

# Run the MCP server
python -m src.agents.dr_off_agent.mcp.server