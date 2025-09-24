# 🆕 Task 2: MCP Tools & Query Interface (Developer Version)

## 🎯 Objectives
- Provide a small, consistent set of MCP tools that let agents answer clinician questions across OHIP Schedule, ADP, and (soon) ODB — with precision, explainability, and citations.
- Use dual-path retrieval: SQL for exact data plus vector retrieval for context, always in parallel.
- Deliver single, composable responses with confidence, provenance, and citations.
- Expose only 5 tools to keep the agent's choice surface simple.

---

## 🛠️ Final Tool Set (5 Tools)

| Tool | Purpose | Notes |
|------|---------|-------|
| `coverage.answer` | Orchestrator – primary entry point for clinician Q&A. Routes internally to schedule/adp/odb as needed, merges results, returns single determination + citations. | Prevents tool-choice confusion. |
| `schedule.get` | Deterministic + vector retrieval for OHIP fees, limits, documentation, preamble commentary. | Always runs vector search alongside SQL and merges results. |
| `adp.get` | Eligibility, exclusions, funding rules, CEP routing. | Covers both Communication Aids and Mobility manuals. |
| `odb.get` | Drug benefit search + LU/EA criteria. | Wire to ODB tables as ingestion matures. |
| `source.passages` | Return exact text chunks used for any decision (for UI "show source"). | Simple pass-through to Chroma. |

---

## 🔄 Dual-Path Retrieval (Always-On)

Each domain tool (`schedule.get`, `adp.get`, `odb.get`) must:

1. **Run SQL and vector retrieval in parallel** (async with timeouts).
2. **Merge results**:
   - SQL → trusted numeric data (fees, DINs, LU codes).
   - Vector → narrative context, eligibility criteria, documentation requirements.
3. **Return**:
   - `provenance`: `["sql","vector"]` (both attempted)
   - `confidence` (composite score; lower if conflicts found)
   - `citations[]` (from vector passages even when SQL hits)
   - `conflicts[]` when SQL vs. vector evidence differ
4. **Never silently omit vector results** — they are critical for context, guardrails, and citations.

---

## 📑 Schemas (Key Fields)

### coverage.answer

**Request:**
```json
{
  "intent": "billing|device|drug",
  "patient": { 
    "age": 72, 
    "setting": "acute|community|ltc", 
    "plan": "ODB|private|none" 
  },
  "question": "free text",
  "hints": { 
    "codes": ["C124"], 
    "device": {"category":"mobility","type":"power_scooter"}, 
    "drug": "empagliflozin" 
  }
}
```

**Response:**
```json
{
  "decision": "billable|eligible|covered|needs_more_info",
  "summary": "One-paragraph clinician-facing answer.",
  "provenance_summary": "sql+vector",
  "confidence": 0.91,
  "highlights": [
    {
      "point": "C124 requires discharge documentation...", 
      "citations": [{"source":"schedule.pdf","loc":"GP—C124"}]
    },
    {
      "point": "Scooter must be a basic mobility need; not car substitute.", 
      "citations": [{"source":"mobility-manual","loc":"410.01"}]
    }
  ],
  "conflicts": [],
  "followups": [{"ask":"Was length of stay <48h?"}],
  "trace": [
    {"tool":"schedule.get","args":{...}}, 
    {"tool":"adp.get","args":{...}}
  ]
}
```

### schedule.get

**Request:**
```json
{
  "q": "day of discharge MRP",
  "codes": ["C124"],
  "include": ["codes","fee","limits","documentation","commentary"],
  "top_k": 6
}
```

**Response:** Must include `provenance`, `confidence`, `items[]`, and `citations[]` even when SQL succeeds.

### adp.get

**Request:**
```json
{
  "device": {"category":"mobility|comm_aids","type":"power_scooter"},
  "check": ["eligibility","exclusions","funding","cep"],
  "use_case": {
    "daily": true,
    "location": "home+entry_exit",
    "independent_transfer": true
  }
}
```

**Response:** Includes structured sections (eligibility, exclusions, funding, cep) + citations + provenance.

---

## 🧠 Agent Experience (Developer Guidance)
- **Single entry point:** Agents call `coverage.answer` 80%+ of the time.
- **Internal routing:** The server decides which domain tools to call.
- **Always return citations** so the agent can quote or link directly.
- **Confidence scoring:** Combine SQL (base 0.9) + vector corroboration (+0.03 per matching passage, −0.1 on conflict).
- **Surface conflicts explicitly** rather than discarding evidence.

---

## ⚙️ Build Steps (FastMCP)

### 1) Server
- Use FastAPI + FastMCP.
- Create `server.py` that registers all 5 tools.
- Each domain tool:
  - Runs `asyncio.gather(sql_query(), vector_query())`
  - Synthesizes combined response
  - Includes provenance, confidence, citations, conflicts
- Implement timeouts (SQL 300–500 ms, vector ≤ 1 s).

### 2) Client
- Implement a `CoverageClient.ask(question, context)` wrapper that calls `coverage.answer`.
- Display citations inline for trust.
- Show confidence badge; highlight if `conflicts[]` not empty.

### 3) Logging & Observability
- Log per-call: latency (SQL/Vector separately), top-k used, conflicts found.
- Use Langfuse or OpenTelemetry spans for tool calls.

### 4) Testing
- Golden QA set (C124, scooter eligibility, repairs/batteries not funded, CEP routing, LU drug).
- Verify:
  - SQL + vector both hit → `provenance=["sql","vector"]`
  - Vector-only still returns coherent answer + citations
  - Conflicts surface correctly

---

## 🆕 Key Changes vs. Original Task 2
1. **Tool list trimmed to 5** (router + 3 domain tools + passage fetcher).
2. **Dual-path retrieval is mandatory** (vector search always runs).
3. **Schemas updated** with provenance, confidence, conflicts, citations[].
4. **Conflicts surfaced** (don't silently prefer SQL).
5. **Parallel execution & timeouts** for speed.
6. **Deterministic before generative** for structured fields, but vector still provides context/citations even on SQL hit.
7. **Golden eval set added** to ensure quality and regression protection.

---

## 📁 Implementation Files (FastMCP Structure)

```python
# src/agents/ontario_orchestrator/mcp/
├── server.py              # FastMCP server with 5 tools
├── tools/
│   ├── coverage.py        # coverage.answer orchestrator
│   ├── schedule.py        # schedule.get dual-path
│   ├── adp.py            # adp.get dual-path  
│   ├── odb.py            # odb.get dual-path
│   └── source.py         # source.passages fetcher
├── models/
│   ├── request.py        # Pydantic request schemas
│   └── response.py       # Pydantic response schemas
├── retrieval/
│   ├── sql_client.py     # SQL query wrapper with timeout
│   ├── vector_client.py  # Chroma wrapper with timeout
│   └── merger.py         # Result synthesis logic
└── utils/
    ├── confidence.py     # Confidence scoring
    └── conflicts.py      # Conflict detection
```

---

## 📊 Database Dependencies

From Session 1 ingestion:
- **SQLite DB:** `data/processed/dr_off/dr_off.db`
  - `odb_drugs` (8,401 records)
  - `odb_interchangeable_groups` (2,369 records)
  - `ohip_fee_schedule` (4,166 fee codes)
  - `adp_funding_rule` (50 records)
  - `adp_exclusion` (27 records)
- **Chroma Collections:**
  - `odb_documents` (49 chunks)
  - `ohip_chunks` (36 embeddings)
  - `adp_v1` (199 embeddings)

---

## 🚀 Quick Start for Developer

```bash
# 1. Install FastMCP
pip install fastmcp

# 2. Set up server
cd src/agents/ontario_orchestrator/mcp
python server.py

# 3. Test with CLI
mcp test coverage.answer '{"question":"Can I bill C124?", "hints":{"codes":["C124"]}}'

# 4. Run golden tests
pytest tests/golden_qa.py
```