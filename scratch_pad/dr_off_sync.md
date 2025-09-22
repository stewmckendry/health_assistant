# Dr. OFF Implementation - Parallel Session Sync Pad

## 🚦 Current Status
- **Issue #**: 20
- **Branch**: feat/dr-off-agent (pending)
- **Started**: 2025-09-22

## 📊 Session Assignments

### Session 1: Data Ingestion & Storage Layer
**Owner**: [Session 1]
**Status**: Not Started

#### Tasks:
- [ ] Create SQLite database schema
- [ ] Implement `ingest_odb.py`
  - [ ] Parse ODB XML → SQL tables
  - [ ] Compute lowest-cost flags
  - [ ] Chunk & embed ODB PDF
- [ ] Implement `ingest_ohip.py`
  - [ ] Parse Schedule PDF → ohip_fees table
  - [ ] Chunk & embed Regulation 552
- [ ] Implement `ingest_adp.py`
  - [ ] Chunk & embed ADP manuals
  - [ ] Extract device rules → adp_device_rules table
- [ ] Initialize Chroma vector store

#### Files Created/Modified:
```
src/agents/clinical/dr_off/ingestion/
  ├── __init__.py
  ├── ingest_odb.py
  ├── ingest_ohip.py
  └── ingest_adp.py

data/processed/dr_off/
  ├── dr_off.db
  └── chroma/
```

---

### Session 2: MCP Tools & Query Interface
**Owner**: [Session 2]
**Status**: Not Started

#### Tasks:
- [ ] Implement MCP tool functions
  - [ ] `formulary_lookup()`
  - [ ] `interchangeability_context()`
  - [ ] `ohip_fee_lookup()`
  - [ ] `coverage_rule_lookup()`
  - [ ] `adp_device_lookup()`
  - [ ] `adp_forms()`
- [ ] Build query router/dispatcher
- [ ] Create structured Answer Card response format
- [ ] Implement tool registration

#### Files Created/Modified:
```
src/agents/clinical/dr_off/tools/
  ├── __init__.py
  ├── formulary_tools.py
  ├── ohip_tools.py
  ├── adp_tools.py
  └── router.py

src/agents/clinical/dr_off/
  └── response_models.py
```

---

### Session 3: OpenAI Agent & Web Integration
**Owner**: [Session 3]  
**Status**: Not Started

#### Tasks:
- [ ] Create Dr. OFF agent configuration YAML
  - [ ] System instructions for Ontario formulary expertise
  - [ ] Tool permissions and routing rules
  - [ ] Response formatting guidelines
- [ ] Implement Dr. OFF agent class using OpenAI Agents SDK
  - [ ] Extend base clinical agent pattern
  - [ ] Register MCP tools from Session 2
  - [ ] Implement structured output handling
- [ ] Integrate with web app
  - [ ] Add to clinical agents dropdown/selector
  - [ ] Create API endpoint `/api/agents/dr-off`
  - [ ] Add agent card to UI
- [ ] Create agent-specific prompts
  - [ ] Guardrails for formulary advice vs medical advice
  - [ ] Citation requirements
  - [ ] Fallback responses

#### Files Created/Modified:
```
configs/agents/dr_off.yaml

src/agents/clinical/dr_off/
  ├── __init__.py
  ├── agent.py (main OpenAI agent implementation)
  └── prompts.py

web/app/api/agents/dr-off/
  └── route.ts

web/app/components/agents/
  └── DrOffCard.tsx

tests/integration/dr_off/
  └── test_agent_integration.py
```

---

### Session 4: Evaluation & Testing Framework
**Owner**: [Session 4]
**Status**: Not Started

#### Tasks:
- [ ] Integrate with existing Langfuse setup
  - [ ] Create Dr. OFF specific traces
  - [ ] Define custom scoring functions
- [ ] Build golden test dataset
  - [ ] 20 ODB drug coverage queries
  - [ ] 20 OHIP billing code queries
  - [ ] 5 ADP device queries
- [ ] Implement evaluation runner
  - [ ] Automated golden test execution
  - [ ] Langfuse score tracking
  - [ ] Performance benchmarking
- [ ] Create test suites
  - [ ] Integration tests
  - [ ] E2E web tests
  - [ ] Performance tests (p95 < 1.5s)
- [ ] Set up monitoring dashboard in Langfuse

#### Files Created/Modified:
```
src/agents/clinical/dr_off/evaluation/
  ├── scores.py
  └── runner.py

data/evaluation/
  └── dr_off_golden_set.json

tests/integration/dr_off/
  └── test_dr_off_integration.py

tests/e2e/dr_off/
  └── test_web_interface.py

tests/performance/dr_off/
  └── test_latency.py
```

---

## 🔄 Sync Points

### Database Schema (Session 1 → Session 2)
```python
# Session 1 defines, Session 2 consumes
odb_drugs: din, ingredient, brand, strength, form, group_id, price, lowest_cost
interchangeable_groups: group_id, name, member_count
ohip_fees: code, description, amount, specialty, page_num
adp_device_rules: category, device, funding_pct, eligibility, replacement_interval
```

### MCP Tools Interface (Session 2 → Session 3)
```python
# Session 2 implements, Session 3 registers with agent
tools = [
    formulary_lookup,
    interchangeability_context,
    ohip_fee_lookup,
    coverage_rule_lookup,
    adp_device_lookup,
    adp_forms
]
```

### Response Model (Session 2 → Session 3)
```python
# Session 2 defines, Session 3 uses
class AnswerCard:
    decision: Literal["Yes", "No", "Conditional"]
    key_data: dict  # price, coverage_pct, fee_amount
    options: list  # DIN list, codes, device types
    citations: list[Citation]  # page/section anchors
```

### Agent Config (Session 3 → Web App)
```yaml
# Session 3 creates configs/agents/dr_off.yaml
name: Dr. OFF
description: Ontario Finance & Formulary Assistant
model: gpt-4o
tools:
  - formulary_lookup
  - ohip_fee_lookup
  - adp_device_lookup
system_prompt: |
  You are Dr. OFF, an AI assistant specializing in Ontario healthcare coverage...
```

### Vector Store Config (Session 1 → Session 2)
```python
# Session 1 creates, Session 2 queries (MCP tools use for RAG)
CHUNK_SIZE = 900-1200 tokens
CHUNK_OVERLAP = 20%
EMBEDDING_MODEL = "text-embedding-3-small"
```

---

## 📝 Notes & Decisions

### 2025-09-22
- Created issue #20 for Dr. OFF implementation
- Decomposed work into 4 parallel streams (added OpenAI agent integration)
- File structure follows existing agent pattern under `src/agents/clinical/`
- Agent will use OpenAI Agents SDK like other clinical agents in codebase

### Architecture Pattern
- Following existing clinical agent pattern found in codebase
- Agent config in YAML under `configs/agents/`
- Web integration through Next.js app routes
- Backend API endpoint for direct agent access
- MCP tools implement RAG pipeline (SQL + vector search)
- Langfuse for evaluation (already integrated)

### Data Sources
- **ODB**: https://www.ontario.ca/page/check-medication-coverage/
- **OHIP**: https://www.health.gov.on.ca/en/pro/programs/ohip/sob/
- **ADP**: https://www.ontario.ca/page/assistive-devices-program

---

## ⚠️ Blockers & Dependencies

| Blocker | Owner | Status | Resolution |
|---------|-------|--------|------------|
| Need ODB XML download URL | Session 1 | Open | |
| Need OHIP Schedule PDF link | Session 1 | Open | |
| MCP tools must be ready | Session 2 → 3 | Open | |
| Database schema finalized | Session 1 → 2,4 | Open | |

---

## 🎯 Success Metrics

- [ ] All unit tests passing (>90% coverage)
- [ ] Agent accessible via web UI
- [ ] E2E demo queries working with citations
- [ ] p95 latency < 1.5s (warm cache)
- [ ] p50 latency < 0.8s (warm cache)
- [ ] Golden test set accuracy > 95%
- [ ] Agent properly integrated in clinical agents dropdown