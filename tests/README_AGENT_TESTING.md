# Agent Testing Framework

Comprehensive testing framework for all doctor agents (Dr. OPA, Dr. OFF, Agent 97, Chief).

## Overview

This framework provides three levels of testing:
1. **Agent-level testing** - Test complete agent with queries
2. **MCP tool testing** - Test individual MCP tools directly
3. **API endpoint testing** - Test HTTP API endpoints

## Prerequisites

**Activate virtual environment:**
```bash
source ~/spacy_env/bin/activate
```

The .env file is loaded automatically by all test scripts - no manual sourcing needed!

## Quick Start

### 1. Test All Agents (Default)

```bash
python scripts/test_agents.py
```

This runs the default test suite for all available agents.

### 2. Test Specific Agent

```bash
# Test Dr. OPA only
python scripts/test_agents.py --agent dr_opa

# Test Dr. OFF only
python scripts/test_agents.py --agent dr_off
```

### 3. Test MCP Tools Directly

```bash
# Test all Dr. OFF MCP tools
python scripts/test_agents.py --mode tools --agent dr_off

# Test specific tools
python scripts/test_agents.py --mode tools --agent dr_off --tools odb_get,adp_get

# Test single tool with custom query
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "atorvastatin"
```

### 4. Test API Endpoints

```bash
# Test Dr. OPA API endpoint
python scripts/test_agents.py --mode api --agent dr_opa

# Ensure your API server is running first:
# uvicorn src.web.api.main:app --reload --port 8001
```

### 5. Run Everything

```bash
python scripts/test_agents.py --mode all --agent all
```

## Test Scripts

### `scripts/test_agents.py`

Main test framework with comprehensive testing capabilities.

**Usage:**
```bash
# Basic usage
python scripts/test_agents.py --agent <agent> --mode <mode>

# Examples
python scripts/test_agents.py --agent dr_opa --mode agents
python scripts/test_agents.py --agent dr_off --mode tools
python scripts/test_agents.py --mode all
```

**Arguments:**
- `--agent`: Which agent to test (dr_opa, dr_off, agent_97, chief, all)
- `--mode`: Test mode (agents, tools, api, all)
- `--tools`: Comma-separated list of specific tools (for tools mode)
- `--queries`: Custom queries to test
- `--output`: Output file for results

**Output:**
- Console output with real-time progress
- JSON results saved to `eval/results/agent_tests/`
- Detailed summaries with metrics

### `scripts/test_mcp_tools_direct.py`

Direct MCP tool testing for debugging and validation.

**Usage:**
```bash
python scripts/test_mcp_tools_direct.py --agent <agent> --tool <tool> [options]
```

**Examples:**

```bash
# Dr. OFF - ODB Tool
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --query "atorvastatin coverage"

# Dr. OFF - ADP Tool with structured request
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool adp_get \
  --device "power wheelchair" \
  --category mobility \
  --patient-income 19000

# Dr. OPA - Policy Check
python scripts/test_mcp_tools_direct.py \
  --agent dr_opa \
  --tool opa_policy_check \
  --query "virtual care consent requirements"

# Run all predefined test cases for a tool
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --run-all-tests
```

**Arguments:**
- `--agent`: Agent name (dr_off, dr_opa)
- `--tool`: Tool name (e.g., odb_get, adp_get, schedule_get)
- `--query`: Query string
- `--k`: Number of results (default: 5)
- `--device`: Device name (for ADP)
- `--category`: Device category (for ADP)
- `--patient-income`: Patient income (for ADP CEP)
- `--drug`: Drug name (for ODB)
- `--din`: DIN number (for ODB)
- `--filters`: JSON string of additional filters
- `--run-all-tests`: Run all predefined test cases
- `--verbose`: Print detailed output

## Configuration

### `tests/agent_test_config.py`

Central configuration file containing:

1. **Agent Configurations** - Import paths and creation functions
2. **Default Test Queries** - Predefined test cases with expected tools
3. **MCP Tool Configurations** - Tool definitions and test requests
4. **API Endpoint Configurations** - API URLs and timeouts
5. **Evaluation Criteria** - Quality thresholds
6. **Performance Benchmarks** - Response time targets

**Customize Test Queries:**

```python
DEFAULT_TEST_QUERIES = {
    "dr_opa": [
        {
            "query": "Your custom query here",
            "expected_tools": ["opa_policy_check"]
        }
    ]
}
```

**Customize MCP Tool Tests:**

```python
MCP_TOOL_CONFIGS = {
    "dr_off": {
        "odb_get": {
            "test_requests": [
                {
                    "query": "custom drug query",
                    "k": 5,
                    "filters": {"drug": "metformin"}
                }
            ]
        }
    }
}
```

## Available Agents

### Dr. OPA (Ontario Practice Advisor)
- **Purpose**: Policy, clinical tools, quality standards
- **MCP Tools**:
  - `opa_policy_check` - CPSO policy lookups
  - `opa_clinical_tools` - CEP clinical decision tools
  - `opa_quality_standards` - Ontario Health quality standards
  - `opa_choosing_wisely` - Choosing Wisely recommendations
  - `opa_ipac_guidance` - IPAC guidance
  - `opa_program_lookup` - Ontario health program info

### Dr. OFF (Ontario Financial & Formulary)
- **Purpose**: OHIP billing, ODB formulary, ADP funding
- **MCP Tools**:
  - `schedule_get` - OHIP Schedule of Benefits
  - `odb_get` - Ontario Drug Benefit formulary
  - `adp_get` - Assistive Devices Program funding

### Agent 97
- **Purpose**: General medical knowledge
- **MCP Tools**: None (uses general LLM)

### Chief (Diagnostic Orchestrator)
- **Purpose**: Diagnostic reasoning and orchestration
- **MCP Tools**: Coordinates other agents

## Test Output

### Console Output
Real-time progress with:
- ✓/✗ Status indicators
- ⏱️ Response times
- 🔧 Tools used
- 📚 Citation counts
- 🎯 Confidence scores
- 📄 Response previews

### JSON Results
Saved to `eval/results/`:
- `agent_tests/` - Agent-level test results
- `mcp_tool_tests/` - MCP tool test results
- `api_tests/` - API endpoint test results

**Result Structure:**
```json
{
  "timestamp": "20251008_143022",
  "agent": "dr_off",
  "summary": {
    "total_tests": 6,
    "successful": 6,
    "failed": 0,
    "success_rate": 1.0,
    "avg_time_seconds": 2.34,
    "avg_confidence": 0.87
  },
  "results": [
    {
      "query": "...",
      "status": "success",
      "elapsed_seconds": 2.1,
      "tools_used": ["odb_get"],
      "confidence": 0.9,
      "response": "..."
    }
  ]
}
```

## Common Use Cases

### 1. Quick Validation After Code Changes

```bash
# Test the specific agent you changed
python scripts/test_agents.py --agent dr_off

# Test specific tools
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --run-all-tests
```

### 2. Debugging Retrieval Issues

```bash
# Test tool with verbose output
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --query "problem drug name" \
  --verbose
```

### 3. Performance Testing

```bash
# Run full suite and check avg_time_seconds
python scripts/test_agents.py --agent dr_opa
```

### 4. Custom Query Testing

```bash
# Test with your own queries
python scripts/test_agents.py \
  --agent dr_opa \
  --queries "What is the CPSO policy on X?" "How do I bill for Y?"
```

### 5. API Integration Testing

```bash
# Start API server first
uvicorn src.web.api.main:app --reload --port 8001

# Then test endpoints
python scripts/test_agents.py --mode api --agent dr_opa
```

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError` when running tests

**Solution:** Ensure you're in the project root and activate the virtual environment:
```bash
cd /path/to/health_assistant_retrieval_improvements
source /Users/liammckendry/spacy_env/bin/activate
python scripts/test_agents.py
```

### Database Not Found

**Problem:** `FileNotFoundError` for database files

**Solution:** Ensure databases are in the correct locations:
- Dr. OFF: `data/ohip.db`
- Dr. OPA: `data/dr_opa_agent/`

### API Connection Errors

**Problem:** Connection refused when testing API

**Solution:** Start the API server:
```bash
uvicorn src.web.api.main:app --reload --port 8001
```

### Tool Not Found

**Problem:** Tool not recognized in tests

**Solution:** Check `tests/agent_test_config.py` to ensure:
1. Tool is listed in `MCP_TOOL_CONFIGS`
2. Import path is correct
3. Function name matches the actual tool function

## Adding New Tests

### Add Test Query

Edit `tests/agent_test_config.py`:

```python
DEFAULT_TEST_QUERIES["dr_opa"].append({
    "query": "Your new test query",
    "expected_tools": ["opa_policy_check"]
})
```

### Add New Tool

1. Add to `MCP_TOOL_CONFIGS` in `tests/agent_test_config.py`:
```python
MCP_TOOL_CONFIGS["dr_opa"]["new_tool"] = {
    "import_path": "src.ai_agents.dr_opa_agent.dr_opa_mcp.server",
    "function_name": "new_tool_handler",
    "test_requests": [
        {"query": "test query", "k": 5, "filters": {}}
    ]
}
```

2. Run tests:
```bash
python scripts/test_agents.py --mode tools --agent dr_opa --tools new_tool
```

## Best Practices

1. **Run tests after every significant change**
   - Especially before committing code
   - After modifying retrieval logic
   - After updating prompts

2. **Use specific tool tests for debugging**
   - Start with `test_mcp_tools_direct.py` to isolate issues
   - Check provenance to see which retrieval path succeeded
   - Inspect citations to verify source quality

3. **Monitor performance trends**
   - Save test results regularly
   - Track avg_time_seconds and success_rate over time
   - Compare before/after metrics for optimizations

4. **Customize for your workflow**
   - Add queries that match your common use cases
   - Create tool-specific test suites for areas you work on
   - Set up automated testing in CI/CD if desired

## Example Workflows

### Testing Dr. OFF ODB Tool Changes

```bash
# 1. Test the tool directly with known query
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --query "atorvastatin" \
  --verbose

# 2. Run all ODB test cases
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --run-all-tests

# 3. Test full agent with ODB queries
python scripts/test_agents.py --agent dr_off
```

### Testing Dr. OPA Policy Tool

```bash
# 1. Test specific policy query
python scripts/test_mcp_tools_direct.py \
  --agent dr_opa \
  --tool opa_policy_check \
  --query "virtual care requirements"

# 2. Run full policy test suite
python scripts/test_agents.py \
  --agent dr_opa \
  --mode tools \
  --tools opa_policy_check

# 3. Test agent with various policy queries
python scripts/test_agents.py \
  --agent dr_opa \
  --queries "CPSO virtual care policy" "prescribing controlled substances"
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review test output for detailed error messages
3. Inspect saved JSON results for full details
4. Ensure configuration in `agent_test_config.py` is correct
