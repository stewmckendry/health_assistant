# Query Processor Configuration

Simple guide for enabling/disabling LLM-powered query processors across all MCP tools.

## Quick Start

**One environment variable controls all tools:**

```bash
# Enable for all tools (ODB, Schedule, etc.)
export ENABLE_QUERY_PROCESSOR=true

# Disable for all tools
export ENABLE_QUERY_PROCESSOR=false
```

That's it! 🎉

## Testing It

```bash
# Test with it enabled
export ENABLE_QUERY_PROCESSOR=true
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "GLP-1 agonist"

# Test with it disabled
export ENABLE_QUERY_PROCESSOR=false
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "GLP-1 agonist"
```

## Advanced: Per-Tool Override (Optional)

If you need to disable one tool while keeping others enabled:

```bash
# Enable globally
export ENABLE_QUERY_PROCESSOR=true

# But disable just ODB
export ODB_QUERY_PROCESSOR=false

# Schedule still uses the global setting (enabled)
```

### Available Tool-Specific Overrides

- `ODB_QUERY_PROCESSOR` - Override for ODB (drug formulary)
- `SCHEDULE_QUERY_PROCESSOR` - Override for Schedule (OHIP billing codes)

**Note**: Only use overrides if you really need them. The global flag is simpler.

## Configuration Patterns

### Development (Testing)
```bash
# .env
ENABLE_QUERY_PROCESSOR=true
```

### Production (Disabled by default, safe rollout)
```bash
# .env
ENABLE_QUERY_PROCESSOR=false

# Enable on specific servers/environments when ready
```

### Production (Selective Rollout)
```bash
# .env
ENABLE_QUERY_PROCESSOR=true
ODB_QUERY_PROCESSOR=true       # Proven stable
SCHEDULE_QUERY_PROCESSOR=false  # Still testing
```

## What Gets Enabled?

When `ENABLE_QUERY_PROCESSOR=true`:

✅ **ODB Tool** - Natural language drug queries, clinical term expansion
✅ **Schedule Tool** - Natural language billing code queries

When disabled (default):
- Tools use legacy path (faster but less flexible)
- No LLM calls = no cost
- Simple drug/code lookups still work perfectly

## Performance Impact

| Mode | Latency | Cost/Query | Accuracy |
|------|---------|------------|----------|
| **Disabled** (legacy) | 0.5-2s | $0 | Good for simple queries |
| **Enabled** (LLM) | 5-10s | ~$0.001 | Excellent for complex queries |

## Checking Current Configuration

```python
# In code
from ai_agents.dr_off_agent.mcp.tools.odb import USE_QUERY_PROCESSOR
print(f"ODB query processor enabled: {USE_QUERY_PROCESSOR}")
```

```bash
# From command line
python3 -c "
import sys
sys.path.insert(0, 'src')
from ai_agents.dr_off_agent.mcp.tools.odb import USE_QUERY_PROCESSOR as odb
from ai_agents.dr_off_agent.mcp.tools.schedule import USE_QUERY_PROCESSOR as schedule
print(f'ODB: {odb}, Schedule: {schedule}')
"
```

## Troubleshooting

**Q: I set `ENABLE_QUERY_PROCESSOR=true` but it's not working**
- Check the env var is actually set: `echo $ENABLE_QUERY_PROCESSOR`
- Make sure you exported it: `export ENABLE_QUERY_PROCESSOR=true`
- Restart your Python process to pick up new env vars

**Q: Queries are slow**
- This is expected - LLM calls add 5-10s latency
- Disable if speed is more important than flexibility: `ENABLE_QUERY_PROCESSOR=false`

**Q: Want to test just one tool**
```bash
# Enable only ODB
export ENABLE_QUERY_PROCESSOR=false
export ODB_QUERY_PROCESSOR=true
```

## Rollback

Instant rollback if issues occur:

```bash
# Disable immediately
export ENABLE_QUERY_PROCESSOR=false

# Or in .env
ENABLE_QUERY_PROCESSOR=false
```

No code deployment needed - tools automatically fall back to legacy path.

## Future Tools

When adding query processor to new tools (ADP, etc.):

1. Use the same pattern:
```python
def _should_use_query_processor():
    tool_specific = os.getenv("ADP_QUERY_PROCESSOR")
    if tool_specific is not None:
        return tool_specific.lower() in ["true", "1", "yes"]

    global_setting = os.getenv("ENABLE_QUERY_PROCESSOR", "false")
    return global_setting.lower() in ["true", "1", "yes"]
```

2. Add tool-specific override to this list:
   - `ADP_QUERY_PROCESSOR`
   - `OHIP_QUERY_PROCESSOR`
   - etc.

3. Document it in this file.

That's it! Keep it simple. ✨
