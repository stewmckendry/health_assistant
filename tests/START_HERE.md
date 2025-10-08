# Agent Testing Framework - Start Here

## 🚀 Get Started in 2 Steps

### 1. Activate Virtual Environment (Required)
```bash
source ~/spacy_env/bin/activate
```

### 2. Run a Test
```bash
# Quick test
./scripts/quick_test.sh dr_off odb

# Or direct tool test
python scripts/test_mcp_tools_direct.py --agent dr_off --tool odb_get --query "metformin"
```

**That's it!** The .env loads automatically from repo root - no manual sourcing needed.

---

## 📚 Full Documentation

See **`tests/QUICK_REFERENCE.md`** for all commands and examples.

---

## 💡 What This Framework Does

✅ Tests agents (Dr. OPA, Dr. OFF, Agent 97, Chief)
✅ Tests MCP tools directly (odb_get, adp_get, schedule_get, etc.)
✅ Auto-loads .env from repo root
✅ Saves all results to `eval/results/`
✅ Configurable test suites in `tests/agent_test_config.py`

---

**Need help?** Check `tests/QUICK_REFERENCE.md`
