# Agent Testing - Quick Reference Card

## ⚙️ Setup (First Time Only)

```bash
source ~/spacy_env/bin/activate
```

Then run any test command. The .env is loaded automatically!

## 🚀 Most Common Commands

### Test All Agents
```bash
./scripts/quick_test.sh all
```

### Test Single Agent
```bash
./scripts/quick_test.sh dr_opa     # Dr. OPA
./scripts/quick_test.sh dr_off     # Dr. OFF
./scripts/quick_test.sh agent_97   # Agent 97
```

### Test Single Tool (Fast Debugging)
```bash
# Dr. OFF - ODB (Drug coverage)
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "atorvastatin"

# Dr. OFF - ADP (Device funding)
python scripts/test_mcp_tools_direct.py --agent dr_off --tool adp_get --device "wheelchair" --category mobility

# Dr. OFF - Schedule (OHIP billing)
python scripts/test_mcp_tools_direct.py --agent dr_off --tool schedule_get --query "house call"

# Dr. OPA - Policy
python scripts/test_mcp_tools_direct.py --agent dr_opa --tool opa_policy_check --query "virtual care"

# Agent 97 - Clinician Search
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search --query "hypertension guidelines"
```

### Run All Tool Tests
```bash
./scripts/quick_test.sh dr_off odb    # All ODB tests
./scripts/quick_test.sh dr_off adp    # All ADP tests
./scripts/quick_test.sh tools         # All MCP tools

# Run all Agent 97 tool tests
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search --run-all-tests
```

## 📋 Test Modes

| Mode | Command | What It Tests |
|------|---------|---------------|
| **Agent** | `--mode agents` | Full agent with queries |
| **Tools** | `--mode tools` | MCP tools directly |
| **API** | `--mode api` | HTTP endpoints |
| **All** | `--mode all` | Everything |

## 🎯 Dr. OFF Tools

### ODB (Drug Formulary)
```bash
# Basic query
--agent dr_off --tool odb_get --query "metformin"

# With DIN
--agent dr_off --tool odb_get --din "02243144"

# Check LU criteria
--agent dr_off --tool odb_get --query "biologic rheumatoid arthritis"
```

### ADP (Device Funding)
```bash
# Basic query
--agent dr_off --tool adp_get --device "hearing aid" --category hearing_devices

# With patient income (CEP check)
--agent dr_off --tool adp_get --device "wheelchair" --patient-income 19000

# Natural language
--agent dr_off --tool adp_get --query "Does my patient qualify for scooter funding?"
```

### Schedule (OHIP Billing)
```bash
# Basic query
--agent dr_off --tool schedule_get --query "complete physical"

# Specialty-specific
--agent dr_off --tool schedule_get --query "surgical assist" --filters '{"specialty":"surgery"}'
```

## 🎯 Dr. OPA Tools

### Policy Check
```bash
--agent dr_opa --tool opa_policy_check --query "virtual care consent"
```

### Clinical Tools
```bash
--agent dr_opa --tool opa_clinical_tools --query "hypertension management"
```

## 🎯 Agent 97 Tools

### Clinician Search
```bash
# Basic search
--agent agent_97 --tool clinician_search --query "hypertension guidelines"

# With custom limits
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search \
  --query "SGLT2 inhibitors heart failure evidence" \
  --max-web-search-uses 2 --max-web-fetch-uses 3
```

### Get Trusted Domains
```bash
# List all 97 domains
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search_get_domains

# With categories
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search_get_domains \
  --include-categories
```

### Health Check
```bash
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search_health_check
```

### Quality Standards
```bash
--agent dr_opa --tool opa_quality_standards --query "diabetes care"
```

### Choosing Wisely
```bash
--agent dr_opa --tool opa_choosing_wisely --query "unnecessary imaging low back pain"
```

## 🔍 Output Interpretation

### Success Indicators
- ✓ = Test passed
- ⏱️ = Response time
- 🔧 = Tools used
- 📚 = Citations found
- 🎯 = Confidence score
- 📊 = Data sources (sql/vector)

### Good Results
- Confidence > 0.7
- Citations > 0
- Response time < 10s
- Provenance includes both sql and vector

### Warning Signs
- Confidence < 0.5
- No citations
- Empty provenance
- Error messages

## 📁 Where Results Are Saved

```
eval/results/
├── agent_tests/         # Full agent tests
├── mcp_tool_tests/      # Individual tool tests
└── api_tests/           # API endpoint tests
```

Files named: `{agent}_{tool}_{timestamp}.json`

## ⚡ Speed Testing

| Test Type | Typical Time |
|-----------|--------------|
| Single tool | 1-3s |
| Agent query | 5-10s |
| Full suite | 1-2min |
| All agents | 5-10min |

## 🐛 Debugging Workflow

1. **Test fails** → Check console output
2. **Tool issue** → Test tool directly with `--verbose`
3. **Data issue** → Check provenance (sql vs vector)
4. **Citation issue** → Inspect saved JSON
5. **Performance** → Check response times

## 💡 Pro Tips

### Quick Smoke Test
```bash
./scripts/quick_test.sh dr_off odb
```

### Verbose Debugging
```bash
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --query "problem" \
  --verbose
```

### All Pre-configured Tests
```bash
python scripts/test_mcp_tools_direct.py \
  --agent dr_off \
  --tool odb_get \
  --run-all-tests
```

### Custom Queries
```bash
python scripts/test_agents.py \
  --agent dr_opa \
  --queries "Query 1" "Query 2" "Query 3"
```

## 📊 Metrics to Watch

| Metric | Good | Warning | Bad |
|--------|------|---------|-----|
| Success Rate | >95% | 80-95% | <80% |
| Avg Confidence | >0.8 | 0.6-0.8 | <0.6 |
| Avg Time | <5s | 5-10s | >10s |
| Citations | >2 | 1-2 | 0 |

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| `tests/agent_test_config.py` | Test definitions |
| `scripts/test_agents.py` | Main framework |
| `scripts/test_mcp_tools_direct.py` | Tool testing |
| `scripts/quick_test.sh` | Quick helper |

## 📚 Full Documentation

- **README_AGENT_TESTING.md** - Comprehensive guide
- **AGENT_TESTING_SUMMARY.md** - Overview and examples
- **QUICK_REFERENCE.md** - This file

---

## Emergency Cheat Sheet

```bash
# Test everything
./scripts/quick_test.sh all

# Debug Dr. OFF ODB
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "drug" --verbose

# Debug Dr. OFF ADP
python scripts/test_mcp_tools_direct.py --agent dr_off --tool adp_get --device "device" --verbose

# Test Dr. OPA
./scripts/quick_test.sh dr_opa

# Run specific tool suite
./scripts/quick_test.sh dr_off odb
```

**Need Help?** Check `tests/README_AGENT_TESTING.md`
