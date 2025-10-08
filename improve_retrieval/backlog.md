# GitHub Issue Backlog

## Critical Review: What Actually Works (2025-10-06)

After testing Issues #2 (Hybrid Retrieval) and #3 (Cross-Encoder Reranking), **both approaches FAILED to improve performance**. Here's what we learned:

### ❌ **What DOESN'T Work:**

1. **Hybrid Retrieval (BM25 + Dense):**
   - **Why it failed:** Baseline Recall@50 already at 75-80% (not 40% as initially assumed)
   - Medical/policy queries are semantic ("hand hygiene protocols"), not keyword-based
   - Dense embeddings already capture semantic meaning well
   - RRF fusion **degraded ranking** (MRR dropped 32% for CPSO)
   - **Verdict:** Skip for specialized domains with good semantic chunking

2. **Cross-Encoder Reranking (General Models):**
   - **Why it failed:** bge-reranker-v2-m3 lacks medical domain understanding
   - Prioritizes keyword overlap over semantic intent
   - Example: Ranked "surgical procedures" higher than "general hand hygiene" for query about procedure rooms
   - MRR dropped 68%, nDCG@10 dropped 57%
   - **Verdict:** General cross-encoders degrade performance in specialized domains

### ✅ **What DOES Work:**

1. **Dense-only retrieval with domain-specific embeddings:**
   - text-embedding-3-small captures medical semantic relationships
   - MRR 0.533 (baseline) vs 0.169 (cross-encoder) - **3x better**
   - Works well for semantic queries common in medical/policy domains

2. **Current baseline is actually decent for Dr. OPA:**
   - Recall@50: 75-80% (finding most relevant docs)
   - MRR: 0.533 (best doc at rank ~2)
   - **Real bottleneck:** Answer synthesis quality, not retrieval

### 🎯 **Priority Analysis (Updated 2025-10-07):**

**✅ COMPLETED: Issue #6 (Parent/Child Chunking)**
- Fixed critical failures: CEP 0% recall, CPSO 10% faithfulness
- 75% fewer chunks (19,223 → 4,728) with richer context
- Automatic parent context enrichment + hierarchical citations
- **Status:** Ready for validation testing

**✅ COMPLETED: Issue #5 (Answer Planner + Self-Check Loop) - 2025-10-07**

**Implementation Status:** ✅ Complete (Option A: Prompt-Based) - **Awaiting Evaluation**

**Why This Was the Highest ROI:**

1. **Current Bottleneck is Answer Synthesis, Not Retrieval:**
   - Retrieval: 71% Recall@50, 0.503 MRR (decent)
   - **Coverage: 19%** → Agent misses 81% of required facts ❌
   - **Helpfulness: 25%** → Answers don't address user's specific question ❌
   - Problem: Tools return raw chunks; agent doesn't know what info is important

2. **Expected 3-4x Improvement:**
   - Intent-specific schemas guide complete fact extraction
   - Self-check loop ensures all required fields filled
   - Focused sub-queries retrieve missing information
   - Target: **Coverage 75%+, Helpfulness 70%+**

3. **Builds on Issue #6 Success:**
   - Parent/child chunks provide richer context
   - section_path enables precise citations
   - Agent now has better raw material to synthesize from

**What Was Implemented (Option A - Prompt-Based):**

1. **4-Step Structured Workflow** added to both agent system prompts:
   ```
   STEP 1: PLAN → Classify intent, identify required schema fields
   STEP 2: RETRIEVE → Call MCP tools, extract facts into schema
   STEP 3: SELF-CHECK → Verify completeness, make sub-queries for gaps
   STEP 4: SYNTHESIZE → Format answer only after ≥90% fields filled
   ```

2. **Intent-Specific Schemas:**
   - **Dr. OFF (5 schemas):** Billing, Drug Coverage, Device Funding, Eligibility, Documentation
   - **Dr. OPA (6 schemas):** CPSO Policy, IPAC Guidelines, Clinical Programs, Clinical Tools, Quality Standards, Choosing Wisely

3. **Web Search Integration:** Clear guidance for when to use `web_search` as fallback when MCP tools insufficient

4. **Mandatory Rules:** Enforced strict workflow compliance:
   - ✓ ALWAYS make ≥2 tool calls per query (initial + self-check)
   - ✓ ALWAYS fill ≥90% schema fields before synthesis
   - ✗ NEVER skip Self-Check step
   - ✗ NEVER hallucinate missing information

5. **Prompt Streamlining:** Removed ~600 lines of redundant sections to avoid agent confusion

**Why Option A (Not Option B Helper Tools):**
- ✅ Faster to implement and iterate (2-4 hours vs 8-12 hours)
- ✅ Leverages OpenAI Agents SDK native stateful reasoning
- ✅ Non-intrusive - no changes to existing MCP tools
- ✅ Easy to refine based on eval results
- 📝 Option B can be added later if metrics not met

**Files Modified:**
- `src/ai_agents/dr_off_agent/openai_agent.py` (lines 397-559)
- `src/ai_agents/dr_opa_agent/openai_agent.py` (lines 380-558)

**Files Created:**
- `test_issue5_implementation.py` - Quick test for ≥2 tool calls
- `improve_retrieval/ISSUE_5_IMPLEMENTATION_SUMMARY.md` - Full documentation

**Next Steps:**
- ⏳ Run quick test: `python test_issue5_implementation.py`
- ⏳ Run full evaluation on all 9 datasets (3 Dr. OFF + 6 Dr. OPA)
- ⏳ Validate Coverage ≥75%, Helpfulness ≥70%, Tool calls ≥2
- ⏳ If successful: Create completion report and move to next issue
- ⏳ If not: Refine prompts or implement Option B helper tools

**Alternative: Issue #4 (Intent Router)**
- Lower priority - current dense-only retrieval already works well
- Intent routing would help SQL-first for Billing/Drugs
- But answer synthesis quality is bigger bottleneck than retrieval strategy

---

## 1. Eval & Observability Baseline ✅ COMPLETED

**Title:** Add retrieval & answer evaluation harness + richer tracing
**Why:** Establish baseline to quantify improvements with each change.
**Status:** ✅ Complete (2025-10-06)

**What Was Implemented:**
- ✅ Created 9 gold datasets: 3 Dr. OFF (OHIP, ADP, ODB), 6 Dr. OPA (Choosing Wisely, CPSO, PHO IPAC, CEP, Quality Standards, OH Programs)
- ✅ Implemented eval framework: Recall@50, MRR, nDCG@10, Hit@10 (retrieval); Faithfulness, Helpfulness, Coverage (LLM-judge)
- ✅ Optimized evaluation: Keyword pre-filtering (70-90% reduction in LLM calls) + batch LLM eval (10 chunks/call)
- ✅ CLI working: `python eval/run.py --agent {dr_off|dr_opa} --set eval/gold/{path} --output results/{name}.json`
- ✅ All 9 baselines captured in `eval/results/baseline/` + summary in `eval/results/RESULTS.md`

**Baseline Results:**
- **Dr. OFF:** 87% Recall@50, 0.822 MRR, 0.963 nDCG@10, 97% Faithfulness, 33% Helpfulness, 24% Coverage
- **Dr. OPA:** 62% Recall@50, 0.335 MRR, 0.444 nDCG@10, 80% Faithfulness, 21% Helpfulness, 16% Coverage
- **Overall:** 71% Recall@50, 0.503 MRR, 0.635 nDCG@10, 86% Faithfulness, 25% Helpfulness, 19% Coverage

**Critical Issues Identified:**
1. **CPSO Policies:** 10% Faithfulness (agent hallucination despite 80% recall)
2. **CEP Tools:** 0% Recall (keyword filter mismatch)
3. **Low Coverage/Helpfulness:** Tools return raw chunks; agent needs structured schemas per intent

**Next Priority:** Issues #2 (Hybrid Retrieval) and #5 (Answer Planner) to address recall gaps and synthesis quality

---

## 2. Hybrid Retrieval (Dense + BM25) with RRF Fusion ⚠️ COMPLETED BUT NOT RECOMMENDED

**Title:** Implement hybrid retriever and RRF fusion endpoint
**Why:** Improve recall on codes/terms and semantics.
**Status:** ⚠️ Complete (2025-10-06) - **Did not improve performance, skip for now**

**What Was Implemented:**
- ✅ Added BM25 index using Whoosh (file-based, 1,439 documents indexed from 5 Dr. OPA collections)
- ✅ Implemented RRF fusion with c=60.0, provenance tracking (dense/sparse/both)
- ✅ Added `use_hybrid=True` parameter to all 6 Dr. OPA MCP tools
- ✅ Fixed critical bug: BM25 index was using sequential IDs instead of ChromaDB's actual document IDs (caused zero overlap)
- ✅ Added comprehensive logging for dense/sparse/RRF debugging

**Evaluation Results (vs Baseline):**
- **PHO IPAC:** 80% → 80% Recall@50 (0% improvement)
- **CPSO Policies:** 80% → 100% Recall@50 (+25%), but MRR: 0.800 → 0.545 (-32%) ⚠️ worse ranking
- **Quality Standards:** 75% → 75% Recall@50 (0% improvement)
- **Choosing Wisely:** 75% → 75% Recall@50 (0% improvement)
- **CEP Tools:** 0% → 25% Recall@50 (known keyword filter bug, unrelated to hybrid)

**Key Finding:**
Hybrid retrieval **did not help** because:
1. Baseline already had 75-80% Recall@50 (not 40% as handover suggested - baseline had empty ID bug)
2. Dr. OPA queries are semantic (e.g., "hand hygiene protocols") - dense embeddings handle these well
3. RRF fusion **degraded ranking quality** (MRR/nDCG) by diluting strong dense rankings
4. BM25 keyword matching doesn't add value for semantic medical queries with good chunking

**Recommendation:**
- **Skip hybrid search** - added complexity without benefit
- **Focus on Issue #3 (Cross-Encoder Reranking)** instead - improves ranking of already-retrieved docs
- The bottleneck is **ranking quality (MRR: 0.335, nDCG@10: 0.444)**, not recall

**Files:**
- Implementation: `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/bm25_client.py`, `rrf_fusion.py`
- Results: `eval/results/02_hybrid_search/`
- Documentation: `improve_retrieval/HYBRID_SEARCH_TECHNICAL_EXPLANATION.md`
- Unit tests: `tests/dr_opa_agent/test_rrf_fusion.py` (7 tests passing)

---

## 3. Cross-Encoder Reranker (Open-source) ❌ COMPLETED BUT FAILED

**Title:** Add local cross-encoder reranker (bge-reranker-v2-m3)
**Why:** Surface the exact clause; reduce "bookmark" answers. Expected to improve MRR/nDCG based on Issue #2 findings.
**Status:** ❌ Complete (2025-10-06) - **FAILED - Performance degraded significantly, DO NOT USE**

**What Was Implemented:**
- ✅ Implemented CrossEncoderReranker with bge-reranker-v2-m3
- ✅ Added lazy initialization to avoid model loading overhead
- ✅ Integrated into semantic_search.py pipeline (Step 3: CE reranking before filtering)
- ✅ Added unit tests with mocked model for CI/CD
- ✅ Pre-downloaded model (~1.2GB) to avoid timeout issues

**Evaluation Results (PHO IPAC, 5 queries):**
- **MRR:** 0.533 → 0.169 (**-68%**) ❌ Best doc moved from rank 2 to rank 6
- **nDCG@10:** 0.499 → 0.216 (**-57%**) ❌ Top-10 ranking quality degraded
- **Helpfulness:** 28% → 20% (-29%) ❌
- **Coverage:** 54.7% → 40.7% (-26%) ❌
- **Recall@50:** 80% → 80% (unchanged, as expected)

**Why It Failed - Root Cause Analysis:**

**Domain Mismatch:** bge-reranker-v2-m3 is a general-purpose cross-encoder trained on web/generic data. It lacks medical domain understanding:

**Example (Query: "What are hand hygiene requirements for procedure rooms?"):**
- **Baseline (Dense) Rank #1** ✅ CORRECT:
  - "4 Moments for Hand Hygiene", "When to clean hands", "Ontario's Just Clean Your Hands program"
  - Dense embeddings understood general procedure room hand hygiene guidance

- **Cross-Encoder Rank #1** ❌ WRONG:
  - "surgical hand rub", "surgical/invasive procedures", "operating rooms are cleaned"
  - Cross-encoder focused on keyword overlap ("procedure", "surgical", "hand") but missed semantic intent
  - **Key insight:** General model doesn't understand that "procedure rooms" ≠ "surgical/invasive procedures" in medical context

**Why Dense Embeddings Outperform:**
1. **Domain-specific training:** text-embedding-3-small captures medical semantic relationships through the corpus
2. **General cross-encoder:** Trained on web data, prioritizes keyword overlap over domain semantics
3. **Chunk size variability:** Chunks range 34-1,165 words; cross-encoder truncates at 512 tokens (~384 words), losing context

**Per-Query Impact:**
- Query 1 (hand hygiene): MRR 1.000 → 0.100 (perfect → rank 10)
- Query 2 (sterilization): MRR 1.000 → 0.333 (perfect → rank 3)
- Query 3 (mobile clinic): MRR 0.500 → 0.333 (rank 2 → rank 3)
- Query 4 (PPE): MRR 0.167 → 0.077 (rank 6 → rank 13)
- Query 5 (environmental cleaning): MRR 0.000 → 0.000 (both failed)

**Recommendation:**
- ❌ **DO NOT use cross-encoder reranking with general-purpose models** for specialized medical/policy domains
- ✅ **Stick with dense-only retrieval** (baseline) - domain-specific embeddings already perform well (MRR 0.533 vs CE 0.169)
- 🔮 **Future option:** Fine-tune a cross-encoder on medical domain data (requires labeled relevance judgments, out of current scope)

**Key Learning:**
General-purpose reranking models can **degrade performance** in specialized domains. Domain-specific dense embeddings trained on the corpus outperform generic cross-encoders for semantic matching.

**Files:**
- Implementation: `src/ai_agents/dr_opa_agent/dr_opa_mcp/retrieval/cross_encoder_reranker.py`
- Tests: `tests/dr_opa_agent/test_cross_encoder_reranker.py`
- Results: `eval/results/03_cross_encoder/dr_opa_pho_ipac.json`
- Pre-download script: `scripts/download_ce_model.py`

---

## 4. Intent Router (SQL-first for Billing/Drugs)

**Title:** Add intent classifier + routing policy for `retrieve()`  
**Why:** Ensure we hit SQL truth first when appropriate; constrain policy sources by intent.

**Scope:**
- Few-shot LLM or rules → intents: {Billing, Drugs, Devices, IPAC, Forms}.
- Router table:
    - Billing → SQL OHIP, then policy collections
    - Drugs → ODB SQL, then formulary policy
    - IPAC → PHO/CPSO/OH only (prefer PHO)
    - Forms → admin policies
- Expose as `retrieve_router(query)` that calls hybrid only on the chosen collections.

**Acceptance Criteria:**
- 90%+ of Billing/Drugs queries hit SQL before vector search (verified in logs).

---

## 5. Answer Planner + Self-Check Loop ✅ COMPLETED

**Title:** Add planner & self-check stages with schemas per intent
**Why:** Convert snippets into decision-ready answers.
**Status:** ✅ Complete (2025-10-07) - **Awaiting Evaluation**

**Context: How This Works with OpenAI Agents SDK**

Our AI agents (Dr. OFF and Dr. OPA) are implemented using the **OpenAI Agents SDK**. The agents:
1. Receive user queries via natural language
2. **Natively call MCP tools** (e.g., `search_ohip_schedule`, `search_cpso_policies`) to retrieve information
3. **Synthesize answers** from tool-returned chunks

**Current Problem:**
- Agent gets raw chunks from tools → doesn't know what facts are important
- No structured extraction → Coverage 19%, Helpfulness 25%
- No verification → agent doesn't check if answer is complete

**Solution: Multi-Step Agent Workflow (Implemented at Agent Level, NOT in Tools)**

### Implementation Strategy: Agent Prompt Engineering + New Coordinator Tools

**WHERE TO IMPLEMENT:**

1. **Agent System Prompt (Primary Implementation):**
   ```python
   # In: src/ai_agents/dr_off_agent/agent.py and dr_opa_agent/agent.py

   SYSTEM_PROMPT = """
   You are Dr. OFF, an expert medical billing assistant. When answering queries:

   STEP 1 - PLAN (Intent-Specific Schema):
   - Identify query intent: Billing | Coverage | Eligibility | Documentation
   - Load required fields for this intent:
     * Billing: [primary_codes, modifiers, conditions, frequency_limits, common_errors]
     * Coverage: [eligibility_criteria, excluded_populations, documentation_requirements]
     * ...

   STEP 2 - RETRIEVE:
   - Call tools to gather information: search_ohip_schedule(), search_adp(), search_odb()
   - Extract facts into schema fields

   STEP 3 - SELF-CHECK:
   - Review schema: Which required fields are empty?
   - For each gap:
     * Generate focused sub-query (e.g., "What are frequency limits for E083A?")
     * Call tool again with sub-query
     * Fill remaining fields

   STEP 4 - SYNTHESIZE:
   - Verify all required fields filled (or mark as "Not found in sources")
   - Format answer with clear sections per schema
   - Include citations with section_path for each fact

   IMPORTANT: Do NOT proceed to Step 4 until self-check passes (≥90% fields filled).
   """
   ```

2. **New MCP Tools for Schema Management (Optional Helper Tools):**
   ```python
   # In: src/ai_agents/dr_off_agent/mcp/tools/answer_planner.py (NEW FILE)

   @tool("get_answer_schema")
   def get_answer_schema(intent: str) -> dict:
       """Returns required fields schema for the given intent.

       This is a helper tool to guide the agent. The agent can also use
       schema patterns from its prompt without calling this tool.
       """
       SCHEMAS = {
           "billing": {
               "required_fields": [
                   "primary_codes",
                   "modifiers",
                   "billing_conditions",
                   "frequency_limits",
                   "common_errors"
               ],
               "format": {
                   "primary_codes": "List[{code, description, fee, conditions}]",
                   "modifiers": "List[{modifier, when_to_use}]",
                   ...
               }
           },
           "ipac": {
               "required_fields": [
                   "requirements_mandatory",
                   "recommendations_best_practice",
                   "setting_specifics",
                   "equipment_rooming",
                   "validation_checks"
               ],
               ...
           }
       }
       return SCHEMAS.get(intent, {})

   @tool("verify_answer_completeness")
   def verify_answer_completeness(
       intent: str,
       extracted_facts: dict
   ) -> dict:
       """Checks which required fields are missing and suggests sub-queries.

       Returns:
       {
           "completeness_score": 0.75,
           "missing_fields": ["frequency_limits", "common_errors"],
           "suggested_sub_queries": [
               "What are the frequency limits for OHIP code E083A?",
               "What are common billing errors for diabetic retinopathy procedures?"
           ]
       }
       """
       schema = SCHEMAS[intent]
       missing = []
       for field in schema["required_fields"]:
           if not extracted_facts.get(field):
               missing.append(field)

       # Generate sub-queries for missing fields
       sub_queries = generate_focused_queries(intent, missing, extracted_facts)

       return {
           "completeness_score": 1 - (len(missing) / len(schema["required_fields"])),
           "missing_fields": missing,
           "suggested_sub_queries": sub_queries
       }
   ```

3. **Existing Tools: NO CHANGES NEEDED**
   - `search_ohip_schedule()`, `search_cpso_policies()`, etc. remain unchanged
   - They continue to return `List[RetrievedItem]` with `text`, `section_path`, `relevance_score`
   - Parent/child enrichment already implemented at retrieval layer (transparent to agent)

**WHY THIS APPROACH:**

✅ **Separation of Concerns:**
- **Retrieval tools** (MCP) focus on finding relevant chunks (already working well with parent/child)
- **Agent** (OpenAI SDK) focuses on structured extraction and verification
- Schema logic in prompt → agent naturally follows multi-step workflow

✅ **Non-Intrusive:**
- Existing MCP tools don't change (no confusion for agent)
- New helper tools are optional (agent can work from prompt alone)
- If helper tools added, they're clearly named: `get_answer_schema()`, `verify_answer_completeness()`

✅ **OpenAI Agents SDK Native Features:**
- Agents can maintain state across steps (plan → retrieve → check → synthesize)
- Tool calls are native → agent decides when to call tools
- Iterative loops supported → agent can call tools multiple times based on self-check results

### Example Agent Workflow (Dr. OFF - Billing Query)

```
User: "How do I bill for diabetic retinopathy laser treatment?"

AGENT STEP 1 - PLAN:
  - Intent: Billing
  - Schema: {primary_codes, modifiers, conditions, frequency_limits, common_errors}

AGENT STEP 2 - RETRIEVE (First Pass):
  Tool Call: search_ohip_schedule(query="diabetic retinopathy laser treatment", top_k=5)
  Retrieved: 5 chunks about E083A, E083B, E083C
  Extracted:
    ✓ primary_codes: [E083A, E083B, E083C]
    ✓ conditions: [Type 1/2 diabetes, documented retinopathy]
    ✗ modifiers: (not found)
    ✗ frequency_limits: (not found)
    ✗ common_errors: (not found)

AGENT STEP 3 - SELF-CHECK:
  Completeness: 40% (2/5 fields filled)
  Missing: [modifiers, frequency_limits, common_errors]

  Sub-Query 1: "What are frequency limits for OHIP code E083A diabetic retinopathy?"
  Tool Call: search_ohip_schedule(query="E083A frequency limits", top_k=3)
  Retrieved: Chunks mentioning "Once per 6 months per eye"
  Extracted:
    ✓ frequency_limits: "E083A: max once per 6 months per eye"

  Sub-Query 2: "What are common billing errors for diabetic retinopathy codes?"
  Tool Call: search_ohip_schedule(query="diabetic retinopathy billing errors common mistakes", top_k=3)
  Retrieved: No specific results
  Extracted:
    ✗ common_errors: (not in knowledge base)

  Completeness: 60% (3/5 fields, modifiers N/A for this code)

AGENT STEP 4 - SYNTHESIZE:
  Answer:
  ---
  Billing Codes for Diabetic Retinopathy Laser Treatment:

  Primary Codes:
  - E083A: Laser photocoagulation ($245.00) [1]
  - E083B: Follow-up examination ($82.50) [2]
  - E083C: Extensive treatment ($490.00) [3]

  Conditions:
  - Patient must have Type 1 or Type 2 diabetes [1]
  - Documented diabetic retinopathy required [1]

  Frequency Limits:
  - E083A: Maximum once per 6 months per eye [4]
  - E083B: Within 3 months of E083A [2]

  Note: Common billing errors not found in available sources.

  Citations:
  [1] OHIP Schedule of Benefits > E > Ophthalmology > Retinal Procedures
  [2] OHIP Schedule of Benefits > E > Ophthalmology > Follow-up Codes
  [3] OHIP Schedule of Benefits > E > Ophthalmology > Complex Procedures
  [4] OHIP Schedule of Benefits > E > Ophthalmology > Frequency Limits
  ---
```

**Acceptance Criteria:**
- On gold set, Coverage increases to ≥75% (from 19%)
- Helpfulness increases to ≥70% (from 25%)
- All answers include schema-based structure (not free-form narrative)
- Citations include section_path for each fact
- Agent makes ≥2 tool calls per query (initial retrieval + self-check sub-queries)

---

## 6. Parent/Child Chunking + Metadata Enrichment ✅ COMPLETED

**Title:** Re-ingest with standardized chunking and enriched metadata
**Why:** Fix critical failures (CEP 0% recall, CPSO 10% faithfulness) + provide richer context for agent synthesis
**Status:** ✅ Complete (2025-10-07) - **Ready for validation testing**

**What Was Implemented:**

### All Collections Restructured (19,223 → 4,728 chunks, 75.4% reduction):

**Dr. OFF Collections:**
1. **OHIP Schedule** (6,983 → 379 chunks): Parent/child by subsection + specialty
2. **ADP** (610 → 214 chunks): Parent/child by document + part + section
3. **ODB Formulary** (10,815 → 3,885 chunks): Parent/child by therapeutic class + drug name

**Dr. OPA Collections:**
4. **CEP Tools** (Re-ingested with ingester_v2): Full content extraction + parent/child chunking
5. **CPSO Policies** (Re-ingested with ingester_v2): Complete policy text + proper metadata
6. **Choosing Wisely** (544 → 295 chunks): Parent/child by specialty + recommendation
7. **Quality Standards** (340 chunks): Metadata enrichment with section_path
8. **PHO IPAC** (132 chunks): Metadata enrichment with section_path

### Metadata Schema Standardization:
- ✅ `section_path`: Hierarchical breadcrumb (e.g., "OHIP Schedule > Surgery > Neurosurgery (04)")
- ✅ `section_title`: Current section/subsection title
- ✅ `chunk_type`: 'parent' | 'child' | 'flat'
- ✅ `parent_id`: Link to parent chunk (for children)
- ✅ `word_count`: Chunk word count
- ✅ `has_parent_context`: Runtime flag when child enriched with parent

### Parent Context Enrichment:
- ✅ Automatic enrichment: Child chunks fetch parent and prepend context
- ✅ Implemented in both Dr. OFF and Dr. OPA vector clients
- ✅ Format: `[PARENT CONTEXT - {title}]\n{parent_text}\n\n[DETAILED CONTENT]\n{child_text}`
- ✅ Transparent to agent - enrichment happens in retrieval layer

### Response Model Updates:
- ✅ Updated Citation model with `section_path` for hierarchical citations
- ✅ Updated RetrievedItem model with `section_path`, `chunk_type`, `has_parent_context`
- ✅ All MCP tools updated to use `section_path` in citations

### Critical Bug Fixes:
- ✅ Fixed embedding dimension issue: Restructure scripts now generate explicit 1536-dim OpenAI embeddings
- ✅ Scripts updated with `load_dotenv()` and direct OpenAI API calls
- ✅ Prevents ChromaDB from reusing corrupted 384-dim metadata

**Expected Impact:**
- **CEP Tools:** 0% → 75%+ Recall (proper chunking with full content)
- **CPSO Policies:** 10% → 95%+ Faithfulness (complete policy context reduces hallucination)
- **All Collections:** Better agent synthesis with parent/child context and hierarchical citations
- **Retrieval Speed:** 75% fewer chunks = faster search with same/better quality

**Files:**
- Restructure scripts: `scripts/restructure_*.py` (5 scripts for Dr. OFF + Dr. OPA)
- Ingester V2: `src/ai_agents/dr_opa_agent/ingestion/{cep,cpso}/ingester_v2.py`
- Vector clients: `src/ai_agents/dr_{off,opa}_agent/*/retrieval/vector_client.py`
- Response models: `src/ai_agents/dr_off_agent/mcp/models/response.py`
- Documentation: `improve_retrieval/PARENT_CHILD_CHUNK_GUIDE.md`, `ISSUE_6_COMPLETE_SUMMARY.md`
- Backups: `data/dr_{off,opa}_agent/backups/chroma_full_backup_20251007_*`

**Next Steps:**
- ⏳ Re-run evaluations on restructured collections
- ⏳ Validate Recall ≥75%, Faithfulness ≥95%
- ⏳ Upload to Railway production

**Note:** Synonym injection (aliases[], codes[]) deferred to Issue #7 after validating core parent/child improvements.

---

## 6b. Two-Tier Retrieval Architecture (CEP, CPSO, Quality Standards, Choosing Wisely) ✅ COMPLETED

**Title:** Implement LLM-based query triage and resource-scoped retrieval
**Why:** Address the "50 tools split into 500 chunks" problem - enable both broad discovery and deep specific queries
**Status:** ✅ Complete (2025-10-07) - **Awaiting Evaluation**

**Problem Statement:**

**Before Two-Tier Architecture:**
- CEP had 41 clinical tools split into 639 chunks with no tool-level disambiguation
- User asks "What CEP tools for chronic pain?" → System searched all 639 chunks
- Retrieved 7 chunks from wrong CORE Neck tool, 0 from correct CNCP tool (Issue #6 analysis)
- Similar issues with CPSO policies (44 policies), Quality Standards (17 standards), Choosing Wisely (40+ specialties)

**Root Cause:**
- Embedding similarity conflates related concepts ("chronic pain" vs "neck pain")
- No resource-level routing - system treats 50 separate tools as one monolithic corpus
- Cannot distinguish "discovery queries" (what tools exist?) from "specific queries" (diagnostic criteria?)

**Solution: Two-Tier Retrieval**

### Tier 1: LLM-Based Query Classification

**Implemented for 4 collections:**
1. **CEP Clinical Tools** (`src/ai_agents/dr_opa_agent/dr_opa_mcp/search/cep_triage.py`)
2. **CPSO Policies** (`src/ai_agents/dr_opa_agent/dr_opa_mcp/search/cpso_triage.py`)
3. **Quality Standards** (`src/ai_agents/dr_opa_agent/dr_opa_mcp/search/qs_triage.py`)
4. **Choosing Wisely** (`src/ai_agents/dr_opa_agent/dr_opa_mcp/search/choosing_wisely_triage.py`)

**Classification Output:**
```python
{
  "intent": "tool_discovery" | "specific_question",  # or "policy_discovery", "standard_discovery"
  "relevant_tools": ["management_of_chronic_non_cancer_pain", "opioid_tapering"],  # 1-3 tools max
  "scope": "single" | "multiple",
  "clinical_domain": "pain_management",
  "confidence": 0.95,
  "reasoning": "User asks what tools are available - CNCP tool is primary..."
}
```

**LLM Triage Implementation:**
- **Model:** gpt-4o-mini (fast, cheap, temperature=0.0)
- **Input:** User query + catalog summary (tool/policy metadata only, not full text)
- **Catalog Files:**
  - `cep_tool_catalog.json` (41 tools with metadata)
  - `cpso_policy_catalog.json` (44 policies)
  - `quality_standards_catalog.json` (17 standards)
  - `choosing_wisely_specialty_catalog.json` (40+ specialties)
- **Prompt Engineering:** Clear intent detection rules + few-shot examples
- **Caching:** Simple dict-based query cache for performance

### Tier 2: Resource-Scoped Retrieval

**Helper Modules (Pattern Consistent Across Collections):**
- `{cep,cpso,qs,choosing_wisely}_helpers.py` - Retrieval logic
  - `retrieve_{tool,policy,standard,specialty}_overviews()` - For discovery queries
  - `retrieve_detailed_{chunks,statements,recommendations}()` - For specific queries
  - `assemble_parent_child_context()` - Fetch parent for child chunks

**Retrieval Strategy:**

**Discovery Queries** (e.g., "What CEP tools for chronic pain?"):
1. Filter to `chunk_type='parent'` only (overviews)
2. Scope to identified tools (e.g., CNCP, Opioid Tapering)
3. Deduplicate to 1-2 chunks per tool
4. Return tool overviews sorted by relevance

**Specific Queries** (e.g., "What is CNCP assessment algorithm?"):
1. Include both parent and child chunks
2. Scope to identified tools (e.g., CNCP only)
3. Fetch parent context for child chunks (prepend to text)
4. Return detailed guidance sorted by relevance

**Metadata Filtering (ChromaDB where filters):**
```python
# Discovery mode - parent chunks only from relevant tools
where_filter = {
  "$and": [
    {"chunk_type": "parent"},
    {"$or": [
      {"source_url": "https://tools.cep.health/tool/management-of-chronic-non-cancer-pain/"},
      {"source_url": "https://tools.cep.health/tool/opioid-tapering/"}
    ]}
  ]
}

# Specific mode - all chunks from relevant tools
where_filter = {
  "$or": [
    {"source_url": "https://tools.cep.health/tool/management-of-chronic-non-cancer-pain/"}
  ]
}
```

**Tool Integration (Transparent to Agent):**

**Updated MCP Tools:**
- `opa_clinical_tools` (server.py lines 1237-1440)
- `opa_policy_check` (server.py lines 443-653)
- `opa_quality_standards` (server.py lines 1443-1713)
- `opa_choosing_wisely` (server.py lines 1718-2029)

**New Optional Filters:**
```python
# Manual override (bypass triage)
filters = {
  "tool_scope": ["management_of_chronic_non_cancer_pain"],  # List[str]
  "intent": "specific_question"  # Manual intent
}

# Auto-triage (default)
# Just call with natural query - tool handles everything
```

**Agent Instructions Updated:**
- Added "Two-Tier Retrieval" section to `openai_agent.py` (lines 471-477)
- Explains auto-classification and scoping
- No filter changes needed - tools handle automatically

**Triage Test Results (CEP - 4 queries):**
```
Query 1: "What CEP tools for chronic pain management?"
  Intent: tool_discovery ✅
  Tools: management_of_chronic_non_cancer_pain ✅

Query 2: "Diabetes screening algorithm BMI 32?"
  Intent: specific_question ✅
  Tools: type_2_diabetes_non_insulin_pharmacotherapy_2 ✅

Query 3: "Depression screening tools for elderly?"
  Intent: specific_question ✅
  Tools: anxiety_and_depression, managing_benzodiazepine_use_in_older_adults ✅

Query 4: "CV risk assessment tool?"
  Intent: tool_discovery ✅
  Tools: managing_patients_with_heart_failure_in_primary_care ✅

Final Accuracy: 100% Intent, 100% Tool Recall
```

**Key Implementation Details:**

1. **CEP Tool Catalog Generation:**
   - Script: `scripts/build_cep_tool_catalog.py`
   - Extracts 41 unique tools from 639 chunks
   - Metadata: tool_id, tool_name, clinical_domain, conditions, capabilities, chunk_count

2. **Parent-Child Context Assembly:**
   - Child chunks don't have parent context prepended during ingestion
   - Helpers fetch parent at retrieval time: `assemble_parent_child_context()`
   - Format: `[PARENT CONTEXT]\n{parent_text}\n\n[SPECIFIC DETAIL]\n{child_text}`

3. **Confidence Scoring:**
   - Weighted average: 40% triage confidence + 60% retrieval confidence
   - Added to response: `classification`, `triage_confidence`, `tools_searched`

4. **Prompt Fine-Tuning:**
   - Added explicit intent detection rules
   - Limited to 1-3 tools max (not 8+)
   - Domain-specific examples for each collection
   - Achieved 100% accuracy on test queries after 2 iterations

**Expected Impact:**

**CEP Tools:**
- **Before:** 0 chunks from CNCP tool (7 from wrong CORE Neck tool)
- **After:** Scoped to 1-3 relevant tools only → Expect Recall@50 improvement from 0% → 75%+

**CPSO Policies:**
- **Before:** All 44 policies searched → Agent gets confused by similar policy names
- **After:** Scoped to 2-4 relevant policies → Expect clearer, more focused results

**Quality Standards & Choosing Wisely:**
- Similar scoping benefits - fewer irrelevant results, better precision

**Files:**
- Triage: `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/{cep,cpso,qs,choosing_wisely}_triage.py`
- Helpers: `src/ai_agents/dr_opa_agent/dr_opa_mcp/search/{cep,cpso,qs,choosing_wisely}_helpers.py`
- Catalogs: `src/ai_agents/dr_opa_agent/dr_opa_mcp/{cep_tool,cpso_policy,quality_standards,choosing_wisely_specialty}_catalog.json`
- Server updates: `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py` (lines 443-2029)
- Agent instructions: `src/ai_agents/dr_opa_agent/openai_agent.py` (lines 463-495)
- Test script: `scripts/test_cep_triage.py`
- Documentation: `eval/chunk_inspection/TWO_TIER_RETRIEVAL_PROPOSAL.md`

**Next Steps:**
- ⏳ Re-run CEP evaluations and compare Recall@50, MRR before/after
- ⏳ Run CPSO, Quality Standards, Choosing Wisely evaluations
- ⏳ Validate triage accuracy ≥90% on gold datasets
- ⏳ Measure latency impact of LLM triage (~2-5s per query)

---

## 7. Agentic Multi-Query Expansion

**Title:** Add automatic sub-query generation & fusion  
**Why:** Catch synonyms/codes/facets the user didn’t type.

**Scope:**
- `expand_queries(query, intent)` → 3–6 sub-queries: lexical (codes/brands), semantic paraphrases, and facet filters (setting/population/device).
- Call `search_hybrid` for each; RRF-fuse across sub-queries; then rerank.

**Acceptance Criteria:**
- Recall@50 + Hit@10 improve notably on IPAC and Billing golds.

---

## 8. Authority & Recency Weighting

**Title:** Add authority/recency scoring to final rank  
**Why:** Prefer PHO/MOH/CPSO and fresh guidance for IPAC/policy.

**Scope:**
- Final score = α*ce_score + β*authority + γ*recency_decay.
- Calibrate per intent (IPAC gets higher β, γ).

**Acceptance Criteria:**
- In IPAC golds, ≥80% of Top-10 items are PHO/MOH/CPSO and ≤24 months old (when applicable).

---

## 9. Observability Dashboards & “Why this chunk?” Trace

**Title:** Add `retrieval_evidence.json` and simple dashboard  
**Why:** Make misses diagnosable.

**Scope:**
- Log: intent, expanded queries, dense/sparse ranks, RRF scores, CE scores, chosen Top-k, rejected-but-close items, SQL hits.
- Optional Streamlit/Plotly page to visualize distributions per release.

**Acceptance Criteria:**
- For any query, devs can see exactly how items were selected.

---

## 10. (Later) Graph Summaries for Policy-Landscape Questions

**Title:** Prototype KG + local expansion for IPAC topics  
**Why:** Better “how is public health handling X?” answers.

**Scope:**
- Extract entity triples during ETL (procedure/device/setting/authority + requires/prohibits/updated_by).
- `graph_expand(topic)` returns a stitched summary + citations to include alongside Top-k.

**Acceptance Criteria:**
- SME rates Helpfulness higher than baseline on at least 3 IPAC “landscape” queries.