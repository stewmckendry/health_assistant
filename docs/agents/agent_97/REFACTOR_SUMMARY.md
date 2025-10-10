# Agent 97 Refactor Summary

**Date**: October 9, 2025
**Objective**: Refactor Agent 97 from patient-focused to clinician-focused clinical evidence search

---

## 🎯 Mission Accomplished

Agent 97 has been successfully refactored from a patient education assistant to a **clinical evidence search tool for healthcare professionals**. The agent now provides evidence-based clinical guidance from 97 trusted medical sources, designed specifically for clinicians.

---

## 📋 Key Changes

### 1. **New Clinician Search MCP Server** ✅

**File**: `src/ai_agents/agent_97/mcp/clinician_search_server.py`

**Key Features**:
- Uses Claude API with `web_search` (max 2 uses) and `web_fetch` (max 5 uses)
- Supports **all 97 trusted medical domains** (no OpenAI 20-domain limit)
- Clinician-focused system instructions
- **No patient safety guardrails** (clinicians exercise clinical judgment)
- Configurable search parameters

**Tools Provided**:
- `clinician_search`: Search 97 trusted medical sources for clinical evidence
- `clinician_search_get_domains`: Retrieve list of trusted medical domains
- `clinician_search_health_check`: Check service health status

### 2. **New OpenAI Agent Implementation** ✅

**File**: `src/ai_agents/agent_97/openai_agent.py`

**Follows Dr. OFF/Dr. OPA Pattern**:
- `Agent97Agent` class with `get_agent()` method
- `query()` method for non-streaming queries
- `query_stream()` method for real-time streaming with progress events
- Langfuse tracing integration
- Session management with SQLite
- Full event handling (progress, reasoning, citations, tool calls)

### 3. **Orchestrator Integration** ✅

**File**: `src/ai_agents/diagnostic_orchestrator/orchestrator_agent.py`

**Changes**:
- Imports `Agent97Agent` wrapper (consistent with Dr. OPA/OFF)
- Initializes Agent 97 in `initialize()` method
- Removed duplicate `_create_agent_97()` method
- Updated to use `agent_97_wrapper.get_agent()` pattern
- Clinician-focused tool descriptions

### 4. **Web UI Updates** ✅

**File**: `web/config/agents.config.ts`

**New Framing**:
- **Tagline**: "Clinical Evidence Search - 97 Trusted Medical Sources"
- **Description**: "Evidence-based clinical guidance from trusted medical literature"
- **Mission**: Focus on healthcare clinicians, not patients
- **Capabilities**: Professional clinical features (diagnostic approaches, treatment protocols, etc.)
- **Starter Prompts**: Clinician-focused queries (hypertension guidelines, SGLT2 evidence, PE workup, etc.)

### 5. **Documentation Rewritten** ✅

**File**: `docs/agents/agent_97/readme.md`

**Comprehensive Updates**:
- Clinician audience throughout
- Architecture diagrams for new implementation
- Comparison table: Agent 97 vs Patient Assistant
- Configuration details (trusted domains, search limits, models)
- Integration examples with orchestrator
- Troubleshooting guide
- API endpoint documentation

### 6. **Test Suite Updated** ✅

**Files Updated**:
- `tests/agent_test_config.py`: Clinician-focused test queries, expected tools
- `scripts/test_mcp_tools_direct.py`: Added Agent 97 support for direct MCP testing
- `tests/quick_reference.md`: Added Agent 97 examples and commands
- `src/ai_agents/agent_97/__init__.py`: Added proper exports

**Test Coverage**:
- Agent-level tests with clinician queries ✅
- MCP tool direct tests ✅
- Health check tests ✅
- Domain retrieval tests ✅

### 7. **Streaming Progress Updates** ✅

**File**: `src/ai_agents/diagnostic_orchestrator/streaming_progress.py`

**Updates**:
- Updated tool descriptions from `agent_97_query` → `clinician_search`
- Added `clinician_search_get_domains` and `clinician_search_health_check`
- Updated user-friendly messages for clinical context
- Improved docstring examples

---

## 🔧 Technical Architecture

### Old Architecture (Patient-Focused)
```
OpenAI Agent (gpt-4o)
    └── MCP Server (agent_97_query tool)
        └── PatientAssistant (Claude)
            └── Web Search with guardrails
```

### New Architecture (Clinician-Focused)
```
OpenAI Agent (gpt-5-mini with reasoning)
    └── MCP Server (clinician_search tool)
        └── Claude API directly
            └── web_search (2 uses, 97 domains)
            └── web_fetch (5 uses, 97 domains)
            └── NO guardrails
```

---

## 📊 Key Differences: Agent 97 vs Patient Assistant

| Feature | Agent 97 (Clinicians) | Patient Assistant (Patients) |
|---------|----------------------|------------------------------|
| **Audience** | Healthcare clinicians (MDs, NPs, PAs) | Patients and general public |
| **Language** | Professional clinical terminology | Plain language explanations |
| **Safety Guardrails** | None (clinical judgment) | Input + output guardrails |
| **Disclaimers** | Professional only | Patient education disclaimers |
| **System Instructions** | Evidence-based clinical guidance | Educational information |
| **Web Search Implementation** | Claude (no domain limit) | Claude (97 domains) |
| **OpenAI Model** | gpt-5-mini (reasoning) | claude-3-5-sonnet |
| **MCP Tool** | `clinician_search` | `agent_97_query` |
| **Max Web Search** | 2 (configurable) | 1 |
| **Max Web Fetch** | 5 (configurable) | 5 |

---

## ✅ Test Results

### Agent-Level Tests
```bash
./scripts/quick_test.sh agent_97

Results:
✅ Success Rate: 100.0%
✅ Avg Time: 7.21s
✅ Confidence: 0.90
✅ Response: Professional clinical language
```

### MCP Tool Tests

**Health Check**:
```bash
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search_health_check

Results:
✅ Server: healthy
✅ Components: all healthy
✅ Trusted domains: 97
✅ Anthropic API: configured
```

**Domain Retrieval**:
```bash
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search_get_domains

Results:
✅ Total domains: 97
✅ Includes: ontario.ca, publichealthontario.ca, nejm.org, thelancet.com, jamanetwork.com, etc.
```

**Clinical Search**:
```bash
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search \
  --query "What is the latest evidence on SGLT2 inhibitors for heart failure with preserved ejection fraction?"

Results:
✅ Tool calls: 3 (clinician_search)
✅ Response time: 53.62s
✅ Response: "High-quality randomized evidence now supports SGLT2 inhibitors (empagliflozin, dapagliflozin) to reduce heart‑failure events in patients with HFmrEF/HFpEF..."
✅ Professional clinical language
```

---

## 🚀 Usage Examples

### Quick Test Commands

```bash
# Test Agent 97
./scripts/quick_test.sh agent_97

# Test single MCP tool
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search \
  --query "Current hypertension guidelines"

# Run all Agent 97 MCP tool tests
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search --run-all-tests

# Health check
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search_health_check

# Get trusted domains
python scripts/test_mcp_tools_direct.py --agent agent_97 --tool clinician_search_get_domains
```

### Programmatic Usage

```python
from src.ai_agents.agent_97.openai_agent import create_agent_97

# Create agent
agent = await create_agent_97()

# Non-streaming query
response = await agent.query(
    "What are the current evidence-based guidelines for managing hypertension in adults?"
)

# Streaming query with progress
async for event in agent.query_stream(
    "Latest evidence on SGLT2 inhibitors for heart failure?",
    session_id="session_123"
):
    if event['type'] == 'progress':
        print(f"Progress: {event['message']}")
    elif event['type'] == 'text':
        print(event['content'], end='', flush=True)
    elif event['type'] == 'citation':
        print(f"\nCitation: {event['content']['url']}")
```

### Orchestrator Integration

```python
from src.ai_agents.diagnostic_orchestrator.orchestrator_agent import create_diagnostic_orchestrator

# Create orchestrator (includes Agent 97)
orchestrator = await create_diagnostic_orchestrator()

# Agent 97 is automatically consulted for evidence-based guidance
response = await orchestrator.orchestrate(
    "What are the evidence-based treatment options for atrial fibrillation, and how are they covered in Ontario?"
)

# The orchestrator will:
# 1. Call Agent 97 for AFib clinical evidence
# 2. Call Dr. OPA for Ontario quality standards
# 3. Call Dr. OFF for OHIP billing and ODB coverage
# 4. Synthesize comprehensive Ontario-contextualized guidance
```

---

## 🔍 Configuration

### Trusted Domains
Agent 97 uses the same 97 trusted medical domains from `src/config/domains.yaml`:
- Medical journals (NEJM, Lancet, JAMA, BMJ, etc.)
- Clinical guidelines (NICE, AHA, ACC, ADA, etc.)
- Academic medical centers (Mayo, Hopkins, Cleveland Clinic, etc.)
- Health authorities (WHO, CDC, NIH, Health Canada, etc.)
- Canadian healthcare (Ontario Health, CPSO, etc.)

### Search Limits (Configurable)
```python
# In clinician_search tool call
{
    "max_web_search_uses": 2,  # Default 2 (Claude uses search more)
    "max_web_fetch_uses": 5     # Default 5
}
```

### Model Configuration
- **Primary model**: `gpt-5-mini` (reasoning-enabled)
- **Temperature**: 0.3 (lower for factual clinical information)
- **Max tokens**: 3000 (higher for detailed clinical guidance)

---

## 📝 Migration Notes

### Breaking Changes
1. **MCP Tool Name Changed**: `agent_97_query` → `clinician_search`
2. **No Guardrails**: Output is NOT filtered for patient safety (clinician audience)
3. **System Instructions**: Completely rewritten for clinical focus
4. **Response Style**: Professional medical terminology vs plain language

### Backward Compatibility
- **Patient Assistant still exists** at `src/assistants/patient.py` for patient-facing applications
- Agent 97 is now exclusively for clinicians
- Old MCP server at `src/ai_agents/agent_97/mcp/server.py` can be deprecated

---

## 🎉 Success Metrics

✅ **Architecture**: Consistent with Dr. OFF/Dr. OPA pattern
✅ **Testing**: All tests passing (agent + MCP tools)
✅ **Documentation**: Comprehensive clinician-focused docs
✅ **Web UI**: Updated for professional clinical framing
✅ **Orchestrator**: Integrated with new Agent 97
✅ **Streaming**: Progress events working correctly
✅ **No Domain Limits**: Claude supports all 97 domains (vs OpenAI's 20)

---

## 🚧 Future Enhancements

Potential improvements documented in `docs/agents/agent_97/readme.md`:
- [ ] Specialty-specific search filters
- [ ] Evidence grading (Level I, II, III)
- [ ] Clinical calculator integration
- [ ] Enhanced reasoning with chain-of-thought
- [ ] Institutional clinical guidelines support

---

## 📚 References

- **Main Documentation**: `docs/agents/agent_97/readme.md`
- **Agent Specification**: `docs/agents/agent_97/agent_spec.md`
- **Test Reference**: `tests/quick_reference.md`
- **MCP Server**: `src/ai_agents/agent_97/mcp/clinician_search_server.py`
- **OpenAI Agent**: `src/ai_agents/agent_97/openai_agent.py`
- **Orchestrator**: `src/ai_agents/diagnostic_orchestrator/orchestrator_agent.py`

---

**Refactor completed**: October 9, 2025
**All tests passing**: ✅
**Ready for production**: ✅
