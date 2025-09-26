# Dr. OFF MCP Tools Specification

## Implementation Status

| Tool | Session | Status | Files Created |
|------|---------|--------|---------------|
| coverage.answer | 2A | ✅ Complete | `tools/coverage.py` (780 lines) |
| schedule.get | 2B | ✅ Complete* | `tools/schedule.py` (400 lines) |
| adp.get | 2B | ✅ Complete* | `tools/adp.py` (450 lines) |
| odb.get | 2C | ✅ Complete* | `tools/odb.py` (650 lines) |
| source.passages | 2C | ✅ Complete | `tools/source.py` (200 lines) |
| **Shared Utilities** | | | |
| SQL Client | 2B | ✅ Complete | `retrieval/sql_client.py` (300 lines) |
| Vector Client | 2B | ✅ Fixed 2025-09-25 | `retrieval/vector_client.py` (280 lines) |
| Confidence Scorer | 2A | ✅ Complete | `utils/confidence.py` |
| Conflict Detector | 2A | ✅ Complete | `utils/conflicts.py` |

*Fixed 2025-09-25: VectorClient now uses correct OpenAI embedding model (`text-embedding-3-small`) matching the ChromaDB collections

## Overview

The Dr. OFF MCP (Model Context Protocol) server provides 5 specialized tools for Ontario healthcare coverage queries. Each tool implements **dual-path retrieval**, always running SQL and vector searches in parallel to ensure accuracy, provide citations, and detect conflicts.

**Server Location**: `src/agents/ontario_orchestrator/mcp/server.py`  
**Base URL**: `http://localhost:8000` (when running)  
**Protocol**: FastMCP

---

## Tool 1: coverage.answer

### Purpose
Main orchestrator tool that routes clinical questions to appropriate domain tools and synthesizes comprehensive answers.

### Clinical Use Cases
- **Complex multi-part questions**: "My 75yo patient is being discharged after 3 days. Can I bill C124 as MRP? Also needs a walker - what's covered?"
- **Ambiguous queries needing clarification**: "Which discharge codes apply for a Thursday discharge?"
- **Coverage determinations across domains**: Billing + devices, drugs + alternatives

### Request Schema
```python
{
    "question": str,           # Required: Free-text clinical question
    "hints": {                 # Optional: Extracted entities
        "codes": [str],        # OHIP fee codes (e.g., ["C124", "C122"])
        "device": {
            "category": "mobility|comm_aids",
            "type": str        # e.g., "walker", "power_wheelchair"
        },
        "drug": str            # Drug name or ingredient
    },
    "patient": {               # Optional: Patient context
        "age": int,
        "setting": "acute|community|ltc",
        "plan": "ODB|private|none",
        "income": float        # For CEP eligibility
    }
}
```

### Response Schema
```python
{
    "decision": "billable|eligible|covered|needs_more_info",
    "summary": str,            # One-paragraph clinician-facing answer
    "provenance_summary": str, # e.g., "sql+vector"
    "confidence": float,       # 0.0-1.0 confidence score
    "highlights": [
        {
            "point": str,      # Key finding
            "citations": [
                {
                    "source": str,     # Document name
                    "loc": str,        # Location (section/code)
                    "page": int        # Optional page number
                }
            ]
        }
    ],
    "conflicts": [             # Detected conflicts between sources
        {
            "field": str,
            "sql_value": Any,
            "vector_value": Any,
            "resolution": str
        }
    ],
    "followups": [             # Questions needing clarification
        {
            "ask": str,
            "reason": str
        }
    ],
    "trace": [                 # Tools called during processing
        {
            "tool": str,
            "args": dict,
            "duration_ms": int,
            "error": str       # If tool failed
        }
    ]
}
```

### Algorithm
1. **Intent Classification**: Analyzes question to determine intent (billing/device/drug)
   - Checks hints first (if codes → billing, if device → device, if drug → drug)
   - Keywords analysis with scoring for each category
   - Highest scoring category wins

2. **Query Routing**: Routes to appropriate domain tools
   - Billing → schedule.get
   - Device → adp.get  
   - Drug → odb.get
   - Can call multiple tools if question spans domains

3. **Parallel Execution**: Uses `asyncio.gather()` to run tools concurrently

4. **Response Synthesis**:
   - Aggregates confidence scores (weighted average)
   - Merges highlights from all tools
   - Detects and reports conflicts
   - Generates unified summary
   - Creates follow-up questions if confidence < 0.7

5. **Confidence Scoring**:
   - Aggregates individual tool confidences
   - Applies tool-specific weights (all tools weighted 1.0)

---

## Tool 2: schedule.get

### Purpose
OHIP Schedule of Benefits lookup with dual-path retrieval for billing codes, fees, and requirements.

### Clinical Use Cases
- **Fee code lookups**: "What's the fee for C124?"
- **Billing requirements**: "Can I bill consultation in ER as internist?"
- **Service limits**: "How many psychotherapy sessions can I bill per patient?"
- **Virtual care codes**: "Which codes are valid for virtual follow-ups?"
- **Premium calculations**: "What premiums apply for house calls to elderly patients?"

### Request Schema
```python
{
    "q": str,                  # Required: Query text
    "codes": [str],            # Optional: Specific fee codes to lookup
    "include": [               # Fields to include (default all)
        "codes",
        "fee", 
        "limits",
        "documentation",
        "commentary"
    ],
    "top_k": int               # Number of results (default 6, max 20)
}
```

### Response Schema
```python
{
    "provenance": ["sql", "vector"],  # Data sources used
    "confidence": float,               # 0.0-1.0
    "items": [
        {
            "code": str,               # Fee code (e.g., "C124")
            "description": str,        # Service description
            "fee": float,             # Dollar amount
            "requirements": str,       # Billing requirements
            "limits": str,            # Service limits/restrictions
            "page_num": int           # Page in schedule PDF
        }
    ],
    "citations": [
        {
            "source": str,
            "loc": str,
            "page": int
        }
    ],
    "conflicts": [...]                # Any SQL/vector conflicts
}
```

### Algorithm
**[IMPLEMENTED - FIXED EMBEDDING MODEL 2025-09-25]**

1. **Parallel Retrieval**:
   - SQL: Query `ohip_fee_schedule` table using `sql_client.query_schedule_fees()`
   - Vector: Search `ohip_documents` collection using OpenAI `text-embedding-3-small` model
   - Both run simultaneously with `asyncio.gather()` with error handling
   - SQL timeout: 500ms, Vector timeout: 1000ms
   - Vector uses cosine similarity for semantic matching

2. **Result Processing**:
   - Process SQL results first (structured data takes priority)
   - For each SQL code, find enriching vector context
   - Extract codes from vector text using regex patterns (e.g., `[A-Z]\d{3}`, `GP\d{2}`)
   - Create ScheduleItem objects with merged data

3. **Result Enrichment**:
   - SQL provides: fee amounts, codes, descriptions, page numbers
   - Vector provides: requirements, documentation needs, service limits
   - Enrichment process:
     - Extract requirements from vector text mentioning the code
     - Extract service limits from vector passages
     - Append vector-only codes not found in SQL

4. **Conflict Detection**:
   - Uses `ConflictDetector.detect_schedule_conflicts()`
   - Checks for fee amount discrepancies
   - Flags conflicting requirements or limits

5. **Confidence Calculation**:
   - Uses `ConfidenceScorer.calculate()`
   - Base 0.9 for SQL hits
   - +0.03 per corroborating vector passage (max +0.09)
   - -0.1 if conflicts detected
   - Lower confidence (0.6 base) if only vector evidence

---

## Tool 3: adp.get

### Purpose
ADP (Assistive Devices Program) eligibility, funding rules, and CEP (Chronic Equipment Program) determination.

### Clinical Use Cases
- **Device funding**: "What percentage does ADP cover for a power wheelchair?"
- **CEP eligibility**: "Patient income $19,000, are they CEP eligible?"
- **Exclusions check**: "Are scooter batteries covered under ADP?"
- **Repair coverage**: "3-year-old scooter needs motor repair - what's covered?"
- **Documentation needs**: "What forms are needed for AAC device funding?"
- **Natural language queries**: "Can my patient get funding for a CPAP?"

### Request Schema

**Option A: Natural Language (Recommended for LLMs)**
```python
{
    "query": str,              # Natural language question
    "patient_income": float    # Optional: Annual income for CEP check
}
```

Examples:
- `{"query": "Can my patient get funding for a CPAP?", "patient_income": 35000}`
- `{"query": "Is a power wheelchair covered for low income patients?"}`
- `{"query": "Does ADP cover hearing aids?"}`

**Option B: Structured Format**
```python
{
    "device": {                        # Required
        "category": str,               # One of 11 ADP categories:
                                      # mobility, comm_aids, hearing_devices,
                                      # visual_aids, respiratory, insulin_pump,
                                      # glucose_monitoring, prosthesis,
                                      # maxillofacial, grants, core_manual
        "type": str                    # Device type
                                      # e.g., "walker", "power wheelchair"
                                      # or "Can I get funding for a wheelchair?"
    },
    "check": [                         # What to check (default all)
        "eligibility",
        "exclusions", 
        "funding",
        "cep"
    ],
    "use_case": {                      # Optional: Usage details
        "daily": bool,
        "location": str,               # e.g., "home+entry_exit"
        "independent_transfer": bool
    },
    "patient_income": float            # For CEP eligibility check
}
```

**NEW: Natural Language Support** (2025-09-25)
- Device type field now accepts natural language queries
- Automatic parameter extraction using regex + LLM fallback
- Examples:
  - "Can I get funding for a power wheelchair?"
  - "Is my patient with $20000 income eligible for a walker?"
  - "Does ADP cover scooter batteries?"

### Response Schema
```python
{
    "provenance": ["sql", "vector"],
    "confidence": float,
    "summary": str,                    # LLM-friendly one-line answer
    "interpretation_notes": {          # Helps LLMs understand response
        "null_values": "null means 'not determined from query'",
        "confidence": "0.99 = high, 0.8+ = good",
        "cep": "CEP eliminates patient cost for low-income"
    },
    "context": str,                    # Policy snippets & funding rules
    "eligibility": {
        "basic_mobility": bool|null,   # null = not determined
        "ontario_resident": bool|null,
        "valid_prescription": bool|null,
        "other_criteria": dict
    },
    "exclusions": [str],              
    "funding": {
        "client_share_percent": float, # Typically 25% unless CEP
        "adp_contribution": float,      # Typically 75%
        "max_contribution": float|null,
        "repair_coverage": str          # Often "Not covered"
    },
    "cep": {
        "income_threshold": float,     # $28k single, $39k family
        "eligible": bool,
        "client_share": float          # 0% if eligible
    }|null,
    "citations": [...],                
    "conflicts": [...]
}
```

### Algorithm
**[ENHANCED 2025-09-26: Natural Language Support + Planned LLM Answer Synthesis]**

1. **Natural Language Processing** (IMPLEMENTED):
   - Accepts either `query` string or structured `device` object
   - Processes through `ADPDeviceExtractor` class
   - Regex extraction for common patterns
   - **LLM fallback when regex returns no category** (GPT-3.5-turbo)
   - Supports all 11 ADP device categories with flexible aliasing
   - Extracts: device_type, category, use_case, income, check_types

2. **Parallel Retrieval**:
   - SQL queries run in nested parallel:
     - `sql_client.query_adp_funding()` for funding rules
     - `sql_client.query_adp_exclusions()` for exclusion rules
   - Vector: `vector_client.search_adp()` with enhanced query
     - Now searches 610 chunks (migrated from adp_v1 collection)
     - Uses rich metadata: policy_uid, funding_count, exclusion_count
   - All run simultaneously with `asyncio.gather()` with exception handling
   - SQL timeout: 500ms, Vector timeout: 1000ms

3. **LLM Reranking** (NEW):
   - Vector results reranked using GPT-3.5-turbo
   - Prioritizes exact device matches, relevant policies
   - Returns top 8 results after reranking

4. **Enhanced Eligibility Assessment**:
   - Metadata-aware filtering using topics JSON field
   - Prioritizes results with "eligibility" or "requirements" topics
   - Check exclusions first - if device explicitly excluded, return ineligible
   - Extract criteria from vector results:
     - Basic mobility need vs. car substitute
     - Ontario residency requirements
     - Prescription requirements
   - Special handling for outdoor-only use (car substitute flag)

5. **Enhanced Exclusion Detection**:
   - Metadata-aware filtering for exclusion_count > 0
   - SQL provides structured exclusion rules
   - Enhanced exclusion messages with policy references
   - Common exclusions with context:
     - "Batteries not covered (adp:core_manual:400.5)"
     - "Repairs not covered (adp:mobility_manual:Section 8.2)"
   - Device-specific exclusion matching
   - Deduplication of exclusion messages

6. **Enhanced Funding Determination**:
   - Metadata filtering for funding_count > 0
   - SQL provides percentage splits (client_share_percent, adp_share_percent)
   - Default: 75% ADP, 25% client
   - Vector provides funding context with dollar amounts
   - Enhanced conflict tracking with funding notes
   - SQL takes precedence for numeric values

7. **CEP Routing** (if requested):
   - Hardcoded thresholds: $28,000 single, $39,000 family
   - Check patient_income against threshold
   - If eligible:
     - Set client_share to 0%
     - Flag CEP coverage of remaining 25%
   - Extract updated thresholds from vector if mentioned

8. **Context Building** (NEW):
   - Builds human-readable context from search results
   - Includes top 3 policy snippets with references
   - Shows funding rules from SQL
   - Lists relevant exclusions
   - Similar to ODB tool's context field

9. **Enhanced Citations**:
   - Uses rich metadata: policy_uid, section_id, page_num
   - Meaningful source names: "ADP Mobility Manual" vs "adp-manual"
   - Section-specific references: "adp:mobility_manual:Section 4.2"

10. **Confidence Scoring**:
   - Uses shared `ConfidenceScorer.calculate()`
   - Base 0.9 for SQL funding match
   - +0.03 per corroborating vector passage
   - -0.1 for conflicts between SQL and vector
   - Lower base (0.6) if vector-only evidence

11. **LLM Answer Synthesis** (PLANNED):
   - After dual-path retrieval completes, pass results to GPT-3.5-turbo
   - Synthesize direct answer to original question
   - Include: funding data, eligibility, CEP info, citations
   - Generate confidence assessment based on data completeness
   - Return as primary `answer` field with supporting evidence

---

## Tool 4: odb.get

### Purpose
ODB (Ontario Drug Benefit) formulary lookup with coverage determination, interchangeable alternatives, and Limited Use criteria.

### Clinical Use Cases
- **Coverage checks**: "Is Ozempic covered for diabetes?"
- **Generic alternatives**: "What's the cheapest statin that's covered?"
- **Limited Use criteria**: "What are the LU requirements for Jardiance?"
- **Interchangeability**: "Is there a generic for Januvia?"
- **Cost comparisons**: "How much would patient save with generic sitagliptin?"

### Request Schema

**Simple Format (from existing model):**
```python
{
    "drug": str,                      # Required: Name, brand, or ingredient
    "check_alternatives": bool,       # Check interchangeables (default true)
    "include_lu": bool,               # Include LU criteria (default true)
    "top_k": int                      # Max alternatives to return (default 5)
}
```

**Enhanced Format (for comprehensive queries):**
```python
{
    "q": str,                         # Required: Query text
    "drug": str,                      # Optional: Drug name or brand
    "din": str,                       # Optional: Specific DIN
    "ingredient": str,                # Optional: Active ingredient
    "strength": str,                  # Optional: Drug strength
    "drug_class": str,                # Optional: e.g., "statin", "glp1 agonist"
    "check": [                        # What to check (default: coverage, interchangeable, lowest_cost)
        "coverage",
        "interchangeable",
        "lowest_cost",
        "lu_criteria",
        "documentation",
        "alternatives",
        "interchangeable_group",
        "price_comparison",
        "all_strengths"
    ],
    "condition": str,                 # Optional: Medical condition for LU evaluation
    "include_brand": bool,            # Include brand names (default true)
    "exclude_lu": bool,               # Exclude LU drugs (default false)
    "top_k": int                      # Number of results (default 5, max 10)
}
```

### Response Schema
```python
{
    "provenance": ["sql", "vector"],  # Always both attempted
    "confidence": float,               # 0.0-1.0
    "coverage": {
        "covered": bool,               # True if on formulary
        "din": str,                    # Drug Identification Number
        "brand_name": str,
        "generic_name": str,
        "strength": str,
        "lu_required": bool,           # Requires Limited Use code
        "lu_criteria": str             # Extracted requirements
    },
    "interchangeable": [               # All drugs in same group
        {
            "din": str,
            "brand": str,
            "price": float,            # Unit price
            "lowest_cost": bool        # Flagged as cheapest
        }
    ],
    "lowest_cost": {                   # Cheapest option details
        "din": str,
        "brand": str,
        "price": float,
        "savings": float               # vs requested drug
    },
    "citations": [                     # From vector search
        {
            "source": str,             # e.g., "odb_drugs_batch_7000"
            "loc": str,                # DIN-based reference: "DIN: 02443937 - Jardiance (EMPAGLIFLOZIN)"
            "page": int                # null for drug embeddings (XML source)
        }
    ],
    "conflicts": [                     # SQL/vector disagreements
        {
            "field": str,              # Usually "coverage"
            "sql_value": Any,
            "vector_value": Any,
            "resolution": str          # How resolved
        }
    ],
    "context": [                       # NEW: Relevant text from vector embeddings
        str                            # Text snippets from semantic search
    ]
}
```

**Additional Response Fields (in enhanced mode):**
- `alternatives`: List of covered alternatives if requested drug not covered
- `price_comparison`: Detailed brand vs generic pricing breakdown
- `needs_more_info`: True if insufficient data to determine coverage

### Recent Enhancements (2025-01-25)

#### Context Content from Vector Embeddings
- **Problem**: Vector search results only provided citations without actual content
- **Solution**: Added `context` field with relevant text snippets from embeddings
- **Benefits**: Provides 1500-4000 chars of clinical context for LLM decision-making

#### Intelligent Context Scaling
- **Hybrid searches**: 3 snippets × 500 chars = ~1500 chars context  
- **Vector-only searches**: 5 snippets × 800 chars = ~4000 chars context
- **Drug embeddings**: Full structured text (not truncated)
- **Policy chunks**: Truncated with "..." indicator

#### Enhanced Citations
- **Drug-specific format**: `"DIN: 02443937 - Jardiance (EMPAGLIFLOZIN)"`
- **Explains null pages**: Drug embeddings from XML don't have page numbers
- **Meaningful references**: Uses DIN + drug names instead of generic locations

#### Natural Language Support  
- **Drug extraction**: `odb_drug_extractor.py` with pattern matching + GPT-3.5 fallback
- **Query examples**: "Is Ozempic covered for diabetes?" → extracts "Ozempic"
- **Preserves context**: Full query for vector, extracted drug for SQL

### Algorithm
**[UPDATED 2025-01-25: Enhanced context + natural language support]**

1. **Drug Resolution**:
   - Accepts both simple (existing model) and enhanced request formats
   - Maps drug classes to common ingredients (e.g., "statin" → matches all statins)
   - Handles DIN, ingredient, brand name searches
   - Extracts drug from `request.drug`, `request.ingredient`, or `request.din`

2. **Parallel Retrieval + Context Collection**:
   - SQL: `sql_client.query_odb_drugs()` queries:
     - `odb_drugs` table (8,401 records) for drug data
     - Filters by DIN, ingredient, or brand name
     - Retrieves interchangeable group information
     - Gets lowest_cost flag and pricing
   - Vector: `vector_client.search_odb()` searches:
     - `odb_documents` collection (10,815 drug-specific embeddings + 49 PDF chunks)
     - Uses OpenAI `text-embedding-3-small` model for semantic matching
     - Each drug embedded with: DIN, generic/brand names, strength, therapeutic class, price, coverage info
     - Metadata preserved across multi-chunk drugs for context retention
     - Includes condition context for LU evaluation
     - **Context Processing**: Collects text snippets based on search type:
       - **Drug embeddings**: Full structured text (not truncated)
       - **Policy documents**: 500-800 chars depending on vector-only vs hybrid
       - **Vector-only searches**: Up to 5 snippets for comprehensive context
       - **Hybrid searches**: Up to 3 snippets (SQL provides structure)
   - Both run simultaneously with `asyncio.gather()` with exception handling
   - Database: `data/ohip.db` (Consolidated database with all tables)
   - SQL timeout: 500ms, Vector timeout: 1000ms

3. **Interchangeability Processing**:
   - Finds primary drug from SQL results based on request
   - Groups all drugs by `group_id` for interchangeable alternatives
   - Identifies drugs with `lowest_cost=True` flag
   - Calculates savings between requested drug and lowest cost option
   - Creates InterchangeableDrug objects for each alternative
   - Sorts by price to identify cheapest options

4. **LU/EA Extraction from Vector**:
   - Searches for "limited use", "LU", "special authorization" in vector results
   - Extracts requirements mentioning specific drugs
   - Common patterns detected:
     - "Must fail metformin first" for diabetes drugs
     - "Documentation required" flags
     - "Prior authorization needed" indicators
   - Sets `lu_required=True` and populates `lu_criteria` field

5. **Coverage Determination**:
   - If drug found in SQL → `covered=True`
   - If not in SQL but mentioned in vector → check policy text
   - Detects "not covered", "not listed" in vector for exclusions
   - Creates DrugCoverage object with all details

6. **Conflict Detection**:
   - Detects when SQL says covered but vector mentions restrictions
   - Flags special authorization requirements not in SQL
   - Reports conflicts between sources with resolution strategy
   - SQL takes precedence for formulary listing

7. **Alternative Drug Suggestions** (for non-covered drugs):
   - Extracts drug class alternatives from vector results
   - Maps common drug classes to known alternatives:
     - GLP-1s: semaglutide, liraglutide, etc.
     - Statins: atorvastatin, simvastatin, rosuvastatin, etc.
   - Creates pseudo-interchangeable entries for alternatives

8. **Confidence Scoring**:
   - Uses shared `ConfidenceScorer.calculate()`
   - Base 0.9 for SQL drug match
   - +0.03 per corroborating vector passage
   - -0.1 for coverage conflicts
   - 0.0 if no data found at all

---

## Tool 5: source.passages

### Purpose
Retrieve exact text passages from vector store by chunk IDs for "show source" functionality.

### Clinical Use Cases
- **Source verification**: User clicks "show source" on a citation
- **Context expansion**: Retrieve full paragraph around a specific quote
- **Evidence review**: Auditor needs to see exact policy text
- **Training/education**: Show clinicians where information comes from

### Request Schema
```python
{
    "chunk_ids": [str],               # Required: List of chunk IDs
    "highlight_terms": [str]          # Optional: Terms to highlight
}
```

### Response Schema
```python
{
    "passages": [
        {
            "chunk_id": str,
            "text": str,              # Full passage text
            "source": str,            # Source document
            "page": int,              # Page number if available
            "section": str,           # Section reference
            "highlights": [str]       # Highlighted terms
        }
    ],
    "total_chunks": int
}
```

### Algorithm
**[IMPLEMENTED BY SESSION 2C]**

1. **Collection Detection**:
   - Groups chunk IDs by inferred collection based on ID patterns:
     - IDs containing "ohip" or "schedule" → `ohip_chunks`
     - IDs containing "adp" or "device" → `adp_v1`
     - IDs containing "odb" or "drug" → `odb_documents`
   - Default to `ohip_chunks` if pattern unclear
   - Removes empty collection groups

2. **Batch Retrieval**:
   - Uses `vector_client.get_passages_by_ids()` for each collection
   - Retrieves chunks in collection groups (not individually)
   - Continues with other collections if one fails
   - Preserves all metadata from Chroma

3. **Metadata Preservation**:
   - Maintains source document name from metadata
   - Preserves page numbers if available
   - Keeps section references
   - Retains collection information

4. **Term Highlighting** (if requested):
   - Searches for highlight_terms in passage text
   - Extracts 50 characters before/after each term occurrence
   - Finds word boundaries for clean snippets
   - Marks terms with `**term**` for emphasis
   - Limits to 5 highlights per passage
   - Case-insensitive matching

5. **Response Formatting**:
   - Creates SourcePassage objects with all metadata
   - Includes full text (no truncation - UI handles display)
   - Total_chunks count for pagination support
   - Clean structure for frontend consumption

---

## Confidence Scoring Formula

All tools use the same base confidence scoring:

```python
confidence = base_score + modifiers - penalties

where:
  base_score = 0.9 (if SQL hit) or 0.6 (if vector only)
  modifiers = 0.03 * num_vector_matches (max +0.15)
            + 0.02 * (num_sql_records - 1) (max +0.06)
  penalties = 0.1 * has_conflict
```

**Confidence Levels**:
- **Very High (0.9+)**: SQL + vector agree, multiple corroborating sources
- **High (0.8-0.9)**: SQL hit with some vector support
- **Moderate (0.7-0.8)**: SQL or vector with limited corroboration  
- **Low (0.6-0.7)**: Vector only or conflicts present
- **Very Low (<0.6)**: Limited evidence or multiple conflicts

---

## Parallel Execution Architecture

All tools implement dual-path retrieval using Python's `asyncio`:

```python
async def execute_tool():
    # Always run both paths in parallel
    sql_task = asyncio.create_task(sql_client.query(...))
    vector_task = asyncio.create_task(vector_client.search(...))
    
    # Wait for both with timeout
    sql_result, vector_result = await asyncio.gather(
        sql_task, 
        vector_task,
        return_exceptions=True
    )
    
    # Merge results even if one path fails
    return merge_results(sql_result, vector_result)
```

**Timeout Configuration**:
- SQL: 300-500ms (configurable)
- Vector: 1000ms (configurable)
- Total tool timeout: 1500ms

---

## Error Handling

Each tool implements resilient error handling:

1. **Partial Failures**: If SQL fails but vector succeeds (or vice versa), return partial results with lower confidence
2. **Timeout Handling**: Return whatever data was retrieved before timeout
3. **Conflict Resolution**: Always surface conflicts, don't hide them
4. **Graceful Degradation**: `needs_more_info` is better than an error

---

## Testing

### Unit Tests
- `tests/test_coverage_answer.py`: Orchestrator tests [SESSION 2A - 400+ lines]
- `tests/test_schedule_tool.py`: OHIP schedule tests [SESSION 2B - IMPLEMENTED]
  - 3 clinical scenarios: MRP discharge, ED consultation, house calls with premiums
  - Tests parallel execution, timeout handling, enrichment logic
- `tests/test_adp_tool.py`: ADP tests [SESSION 2B - IMPLEMENTED]
  - 5 device scenarios: power wheelchair+CEP, batteries exclusion, SGD fast-track, walker, car substitute
  - Tests eligibility, funding, CEP routing, conflict detection
- `tests/test_odb_tool.py`: ODB tests [SESSION 2C - 350 lines]

### Integration Tests
- `tests/test_parallel_execution.py`: Verifies dual-path always runs [SESSION 2B - IMPLEMENTED]
  - Confirms asyncio.gather() parallel execution
  - Measures timing to ensure parallel not sequential
  - Tests error resilience (one path can fail)
- `tests/golden_qa.py`: 15+ clinical scenarios [SESSION 2C - 550 lines]

### Performance Tests
- Target p50 latency: < 0.8s
- Target p95 latency: < 1.5s
- Parallel execution must complete within timeouts

---

## Database Dependencies

### SQLite Databases

#### Primary: `data/ohip.db`
- `ohip_fee_schedule`: 4,166 fee codes
- `adp_funding_rule`: 50 funding rules
- `adp_exclusion`: 27 exclusion rules
- `act_eligibility_rule`: 58 records (Health Insurance Act)
- `act_health_card_rule`: 11 records

#### Primary Database: `data/ohip.db`
- Consolidated database with OHIP, ODB, and ADP tables
- `odb_drugs`: 8,401 drug records
- `odb_interchangeable_groups`: 2,369 groups
- `ohip_fee_schedule`: 2,123+ fee codes
- `adp_funding_rule`: 50+ funding rules
- `adp_exclusion`: 27+ exclusions

### ChromaDB Collections (`data/dr_off_agent/processed/dr_off/chroma/`)
- `ohip_chunks`: 36 chunks (Health Insurance Act + Schedule)
- `adp_v1`: 199 chunks (ADP manuals - Mobility & Communication Aids)
- `odb_documents`: 10,864 chunks total
  - 10,815 drug-specific embeddings (from XML formulary data)
  - 49 PDF chunks (ODB policy/procedure document)

---

## Future Enhancements

1. **Caching Layer**: Add Redis for frequent queries
2. **Query Rewriting**: Improve semantic search with query expansion
3. **Feedback Loop**: Track which sources users find most helpful
4. **Multi-source Validation**: Cross-reference between OHIP, ODB, and ADP
5. **Audit Trail**: Complete logging of all decisions for compliance