# Agent Testing Framework - Summary

## What Was Built

A comprehensive, reusable testing framework for all doctor agents that eliminates the need to rebuild test scripts every session.

## Key Features

### 1. Three Testing Levels

✅ **Agent Testing** - Test complete agents with queries
✅ **MCP Tool Testing** - Test individual MCP tools directly
✅ **API Testing** - Test HTTP API endpoints

### 2. Unified Configuration

All test configurations in one place (`tests/agent_test_config.py`):
- Agent definitions
- Test queries with expected tools
- MCP tool configurations
- API endpoint URLs
- Performance benchmarks

### 3. Flexible Execution

Multiple ways to run tests:
- Full test suites
- Single agent/tool
- Custom queries
- Pre-configured test sets

## Files Created

```
scripts/
├── test_agents.py              # Main test framework
├── test_mcp_tools_direct.py    # Direct MCP tool testing
└── quick_test.sh               # Quick test helper script

tests/
├── agent_test_config.py        # Centralized test configuration
├── README_AGENT_TESTING.md     # Comprehensive documentation
└── AGENT_TESTING_SUMMARY.md    # This file
```

## Quick Start Commands

**First, activate virtual environment:**
```bash
source ~/spacy_env/bin/activate
```

**Then run tests (.env loads automatically):**

### Test Everything
```bash
./scripts/quick_test.sh all
```

### Test Specific Agent
```bash
./scripts/quick_test.sh dr_opa
./scripts/quick_test.sh dr_off
```

### Test Specific Tool
```bash
./scripts/quick_test.sh dr_off odb
./scripts/quick_test.sh dr_off adp
```

### Test All MCP Tools
```bash
./scripts/quick_test.sh tools
```

### Test with Custom Query
```bash
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --query "metformin coverage"
```

## What This Solves

### Before (Problems)
❌ Every Claude Code session rebuilds test scripts from scratch
❌ Tests hit bugs repeatedly
❌ No consistent test coverage
❌ Hard to test specific tools in isolation
❌ No saved test history

### After (Solutions)
✅ Reusable test framework ready to run
✅ Pre-configured test cases for common scenarios
✅ Consistent, repeatable testing
✅ Easy to test tools directly for debugging
✅ Automated result saving with timestamps

## Supported Agents & Tools

### Dr. OPA (Ontario Practice Advisor)
**MCP Tools:**
- `opa_policy_check` - CPSO policies
- `opa_clinical_tools` - CEP clinical tools
- `opa_quality_standards` - Quality standards
- `opa_choosing_wisely` - Choosing Wisely recommendations
- `opa_ipac_guidance` - IPAC guidance
- `opa_program_lookup` - Ontario health programs

**Example Test:**
```bash
python scripts/test_mcp_tools_direct.py \
  --agent dr_opa \
  --tool opa_policy_check \
  --query "virtual care consent"
```

### Dr. OFF (Ontario Financial & Formulary)
**MCP Tools:**
- `schedule_get` - OHIP billing codes
- `odb_get` - Drug formulary
- `adp_get` - Device funding

**Example Tests:**
```bash
# ODB - Drug coverage
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --query "atorvastatin"

# ADP - Device funding
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool adp_get \
  --device "power wheelchair" \
  --category mobility \
  --patient-income 19000

# OHIP - Billing codes
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool schedule_get \
  --query "house call"
```

### Agent 97
General medical knowledge agent (no MCP tools)

### Chief
Diagnostic orchestrator (coordinates other agents)

## Test Output

### Console Output
- Real-time progress with status indicators
- Response times and performance metrics
- Tool usage and confidence scores
- Citation counts
- Response previews

### Saved Results
All results automatically saved to:
```
eval/results/
├── agent_tests/         # Agent-level tests
├── mcp_tool_tests/      # MCP tool tests
└── api_tests/           # API endpoint tests
```

**Example result:**
```json
{
  "timestamp": "20251008_124501",
  "agent": "dr_off",
  "summary": {
    "total_tests": 6,
    "successful": 6,
    "success_rate": 1.0,
    "avg_time_seconds": 2.1,
    "avg_confidence": 0.89
  },
  "results": [...]
}
```

## Common Workflows

### 1. Quick Validation
```bash
# After making code changes
./scripts/quick_test.sh dr_off
```

### 2. Debug Retrieval Issue
```bash
# Test specific tool with verbose output
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --query "problem drug" \
  --verbose
```

### 3. Run All Pre-configured Tests
```bash
# Test all pre-configured test cases for a tool
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --run-all-tests
```

### 4. Test Custom Queries
```bash
python scripts/test_agents.py \
  --agent dr_opa \
  --queries "CPSO policy X" "How to bill Y"
```

## Adding New Tests

### Add Test Query
Edit `tests/agent_test_config.py`:
```python
DEFAULT_TEST_QUERIES["dr_opa"].append({
    "query": "New test query",
    "expected_tools": ["opa_policy_check"]
})
```

### Add Tool Test Case
Edit `tests/agent_test_config.py`:
```python
MCP_TOOL_CONFIGS["dr_off"]["odb_get"]["test_requests"].append({
    "query": "new drug query",
    "k": 5,
    "filters": {}
})
```

## Performance Benchmarks

Built-in benchmarks in `agent_test_config.py`:
- Dr. OPA: < 10s response time
- Dr. OFF: < 8s response time
- 95% success rate target

## Next Steps

1. **Run baseline tests** to establish current performance:
   ```bash
   ./scripts/quick_test.sh all
   ```

2. **Add project-specific test cases** to `agent_test_config.py`

3. **Use for debugging** when issues arise:
   ```bash
   python scripts/test_mcp_tools_direct.py --agent <agent> --tool <tool> --verbose
   ```

4. **Track improvements** over time by comparing saved results

## Key Benefits

1. ⚡ **Fast** - Pre-configured, ready to run
2. 🔧 **Flexible** - Test agents, tools, or APIs
3. 📊 **Comprehensive** - Automatic metrics and summaries
4. 💾 **Persistent** - All results saved with timestamps
5. 🐛 **Debuggable** - Verbose mode for detailed inspection
6. 🔄 **Reusable** - No need to rebuild every session
7. 📝 **Documented** - Clear examples and usage instructions

## Documentation

- **README_AGENT_TESTING.md** - Full documentation with examples
- **agent_test_config.py** - Configuration reference
- **This file** - Quick summary

## Verified Working

✅ MCP tool testing confirmed working with Dr. OFF ODB tool
✅ Successfully retrieved atorvastatin coverage data
✅ Provenance tracking working (SQL + vector)
✅ Citations included
✅ Response time: ~1.5s
✅ Confidence score: 0.99

## Support

For issues:
1. Check `tests/README_AGENT_TESTING.md` for detailed docs
2. Review test output for error messages
3. Inspect saved JSON results
4. Verify configuration in `agent_test_config.py`
