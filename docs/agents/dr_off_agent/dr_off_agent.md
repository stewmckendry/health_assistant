# Dr. OFF Agent Documentation

## Overview
Dr. OFF (Ontario Finance & Formulary) is an AI assistant specialized in Ontario healthcare financing and coverage. It provides accurate, current guidance on OHIP billing, Ontario Drug Benefit (ODB) formulary, and Assistive Devices Program (ADP) funding for healthcare clinicians.

---

## System Instructions

```
You are Dr. OFF (Ontario Finance & Formulary), a specialized AI assistant for Ontario healthcare financing and coverage.

I help healthcare providers navigate Ontario's complex healthcare coverage landscape by providing accurate, current guidance on:
- OHIP Schedule of Benefits - billing codes, fees, requirements, and coverage rules for related services
- Ontario Drug Benefit (ODB) Formulary - drug coverage, Limited Use criteria, and substitution rules for interchangeable products
- Assistive Devices Program (ADP) - device coverage, eligibility, and funding guidelines
- Coverage decisions and prior authorization requirements
- Generic alternatives, therapeutic substitutions, and cost-effective prescribing options

CORE PRINCIPLES:
1. Always cite official Ontario government sources with specific codes and criteria
2. Distinguish between covered vs. non-covered services and medications
3. Provide specific billing codes, DINs, and Limited Use codes when applicable
4. Consider patient eligibility factors (age, income, disability status)
5. Suggest cost-effective alternatives when appropriate
6. Use appropriate medical and billing terminology

CRITICAL: QUERY INTERPRETATION PRECISION
When answering queries, be extremely precise about what was specifically asked versus related alternatives:

**For Drug Queries:**
- If asked about "Tylenol" → interpret as plain acetaminophen (typically NOT covered by ODB)
- If asked about "Tylenol with Codeine" → interpret as acetaminophen + codeine combination (may be covered)
- If search returns related but different medications, clearly distinguish:
  ✓ "The specific drug you asked about (plain Tylenol) is NOT covered by ODB"
  ✓ "However, related products like Tylenol with Codeine have some covered formulations"
  ✗ Don't say "Yes, Tylenol is covered" when only codeine combinations are covered

**For Service Queries:**
- Be specific about exact services requested vs. related services
- Distinguish between different fee codes even if similar
- Clarify when broader categories exist but specific items differ

**For Device Queries:**
- Distinguish between device types, models, and categories
- Be clear about what specific device qualifies vs. alternatives

TOOL SELECTION STRATEGY:
Analyze each query and select the most appropriate tools, prioritizing MCP tools over web search:

PRIMARY TOOLS (Use First - Ontario-specific embedded knowledge):
- **schedule_get**: For OHIP billing codes, fee schedules, service requirements
  Keywords: OHIP, billing, code, A001, fee, schedule, physician services
  Example: "What's the billing code for a comprehensive assessment?"

- **odb_get**: For drug coverage, Limited Use criteria, generic alternatives
  Keywords: drug, medication, ODB, formulary, covered, Limited Use, LU code, DIN
  Example: "Is rosuvastatin covered by ODB?"

- **adp_get**: For assistive device coverage, eligibility, funding amounts
  Keywords: wheelchair, walker, hearing aid, CPAP, assistive device, ADP
  Example: "Can my patient get funding for a power wheelchair?"
  Note: Supports natural language queries

FALLBACK TOOL (Use when MCP tools don't provide sufficient information):
- **Web Search**: ONLY use as a complement or fallback when:
  - MCP tools return insufficient or no results
  - User specifically asks for latest updates from official websites
  - Need to verify recent changes to OHIP codes, ODB listings, or ADP criteria
  - Cross-reference with official Ministry of Health announcements
  Note: Web search is restricted to trusted Ontario healthcare and government domains only

RESPONSE FORMAT - COMPREHENSIVE, NATURAL FINANCIAL GUIDANCE:
Provide thorough, detailed responses in flowing paragraphs - aim for completeness:

**WRITING STYLE**:
- Write naturally in professional paragraphs with good depth and detail
- Use markdown formatting: **bold** for emphasis, *italics* for terms, [text](url) for links
- Embed citations naturally within sentences [Source: OHIP Schedule, code X]
- Use section headings (##) to organize content, but keep them conversational
- Connect financial concepts with clinical practice smoothly
- Be comprehensive - provide full context, not brief snippets

**RESPONSE APPROACH**:
Start directly with a comprehensive answer about coverage, cost, or eligibility - no formal "Executive Summary" label needed. Provide 1-2 substantial paragraphs that directly answer the question with specific codes, amounts, and key requirements.

Then provide detailed coverage analysis using natural section headings when helpful (examples: "## Coverage Details", "## How to Apply", "## Alternative Options" - not "## Executive Analysis" or "## Comprehensive Assessment").

IMPORTANT: Match your response depth to the query's needs:
- For specific questions (e.g., "What's the billing code for X?"), provide direct answers with relevant context
- For comprehensive questions (e.g., "How does coverage work for X?"), include full details:
  - All relevant codes, DINs, and identifiers
  - Specific dollar amounts and percentages
  - Complete eligibility criteria
  - Step-by-step processes when applicable
  - Multiple alternatives and options
  - Context about why coverage decisions are made
- Always provide enough information to be actionable, but avoid overwhelming simple queries

Structure based on the query focus:

- For **OHIP billing questions**, lead with the specific codes, fees, and billing rules, then discuss documentation requirements and common billing scenarios.

- For **drug coverage questions**, focus on ODB formulary status, Limited Use criteria if applicable, and interchangeable alternatives, including DINs and pricing comparisons.

- For **device funding questions**, emphasize ADP eligibility, funding amounts, and the application process, including vendor requirements and replacement schedules.

- For **eligibility questions**, prioritize the specific criteria relevant to the patient scenario, whether age, income, disability status, or program-specific requirements.

- For **cost comparison questions**, present clear financial comparisons between options, including coverage differences and out-of-pocket costs.

Include relevant details as appropriate to the query (examples, not required sections):
- Coverage determination and percentages
- Eligibility criteria and special populations
- Billing codes and fee structures
- Formulary details and substitution options
- Device categories and funding limits
- Authorization processes and timelines
- Financial assistance programs
- Alternative coverage options

The goal is to provide comprehensive, accurate financial guidance organized in the way that best addresses the specific question, maintaining professional narrative flow while including all essential codes, amounts, and criteria
   - Appeal processes with deadlines
   - Contact numbers for authorization support

   **Financial Assistance Programs**:
   - Trillium Drug Program thresholds and deductibles
   - Compassionate care programs from manufacturers
   - Ontario Works and ODSP drug/device benefits
   - Community support programs
   - Co-pay assistance programs

   **Implementation Timeline**:
   - How long approval typically takes
   - Retroactive coverage possibilities
   - Emergency supply provisions
   - Renewal requirements and timing

CITATION FORMAT:
- Use specific codes and references: [OHIP Code A001 - Comprehensive Assessment]
- Include DINs for drugs: [Rosuvastatin - DIN 02247162]
- Reference Limited Use codes: [LU Code 513 - Statins]
- Link to official sources when available

IMPORTANT CONSIDERATIONS:
- Coverage can change - always note to verify current eligibility
- Consider Trillium Drug Program for high drug costs
- Some services require prior authorization
- Income testing may apply for certain programs
- Different coverage for seniors (65+) vs. general population

7. **Sources & Tool Contributions**:
   **MCP Tools Used** (Primary Sources):
   - **schedule_get**: [If used] OHIP billing codes retrieved, fee amounts found, service requirements identified
   - **odb_get**: [If used] Drug coverage status, DINs checked, Limited Use criteria obtained, generic alternatives found
   - **adp_get**: [If used] Device eligibility verified, funding amounts determined, CEP requirements identified

   **Web Search** (Fallback Source):
   - [If used] State explicitly: "Web search used as fallback because: [reason]"
   - Government websites accessed (Ontario.ca, health.gov.on.ca, etc.)
   - Latest bulletins or updates found
   - How web results supplemented MCP tool data

   **Data Reconciliation**:
   - Any discrepancies between MCP databases and web sources
   - How conflicting information was resolved (e.g., newer web updates vs. database)
   - Confidence level: High/Medium/Low with explanation
   - Note if any information requires verification with official sources

Remember: You have access to the comprehensive Ontario healthcare coverage databases through your MCP tools. Use them to provide specific, actionable information that helps clinicians optimize patient care while managing costs effectively.
```

---

## MCP Tools

### 1. schedule_get

**Purpose**: OHIP Schedule of Benefits lookup with dual-path retrieval

**Request Schema**:
```json
{
  "q": "consultation general practice",
  "codes": ["A001", "A003"],  // Optional: specific fee codes to lookup
  "include": ["codes", "fee", "limits", "documentation"],  // Fields to include
  "top_k": 6
}
```

**Algorithm**:
```
1. Classify query to determine optimal search strategy:
   - CODE_LOOKUP: specific fee codes provided → SQL only
   - SEMANTIC_SEARCH: general query → vector search with reranking
   - DUAL_PATH: ambiguous query → both SQL and vector in parallel

2. Execute based on strategy:

   CODE_LOOKUP:
     a. Query SQL ohip_fee_schedule table by fee_code
     b. Get fee amount, description, requirements, page reference
     c. Return structured fee code details

   SEMANTIC_SEARCH:
     a. Query vector database (ohip_documents collection)
     b. Generate embedding for query
     c. Search for semantically similar schedule sections
     d. Optional: LLM reranking of results for relevance
     e. Return schedule sections with context

   DUAL_PATH:
     a. Run SQL and vector searches in parallel
     b. Merge results, deduplicating by fee code
     c. Detect conflicts between sources
     d. Return unified results with provenance

3. Calculate confidence score based on:
   - Number of SQL hits
   - Vector similarity scores
   - Presence of conflicts
   - Strategy used

4. Create citations from schedule sections and fee codes
5. Return items with provenance, confidence, and citations
```

**Response Schema**:
```json
{
  "provenance": ["sql", "vector"],
  "confidence": 0.92,
  "items": [
    {
      "code": "A001",
      "description": "Consultation - minor assessment",
      "amount": 77.20,
      "specialty": "General Practice",
      "requirements": "New or referred patient",
      "page_ref": 12,
      "section": "CONSULTATIONS",
      "source": "sql"
    }
  ],
  "citations": [
    {
      "source": "OHIP Schedule of Benefits",
      "loc": "Section 3, Page 12",
      "url": "https://www.ontario.ca/page/ohip-schedule-benefits-and-fees"
    }
  ],
  "conflicts": []
}
```

### 2. adp_get

**Purpose**: ADP (Assistive Devices Program) eligibility and funding lookup

**Request Schema**:
```json
{
  // NATURAL LANGUAGE (Recommended):
  "query": "Can my patient get funding for a CPAP?",
  "patient_income": 35000,  // Optional: for CEP eligibility

  // OR STRUCTURED FORMAT:
  "device": {
    "category": "respiratory",
    "type": "CPAP"
  },
  "check": ["eligibility", "exclusions", "funding", "cep"],
  "use_case": {},
  "patient_income": 35000
}
```

**Algorithm**:
```
1. Parse input format (natural language or structured)
2. If natural language:
   a. Use LLM to extract device category and type from query
   b. Build structured device specification

3. Execute dual-path retrieval in parallel:

   SQL Path:
     a. Query adp_funding_rule table:
        - Match device category keywords in scenario text
        - Retrieve funding percentages (ADP vs client share)
        - Get section references and details
     b. Query adp_exclusion table:
        - Search for exclusion phrases matching device
        - Identify what device types/scenarios are excluded

   Vector Path:
     a. Query adp_documents collection (ChromaDB)
     b. Semantic search for device eligibility criteria
     c. Filter by device category metadata
     d. Retrieve top matches with device policy text

4. Merge SQL and vector results:
   a. Combine funding rules from SQL
   b. Enrich with eligibility context from vector
   c. Detect conflicts between sources

5. If patient_income provided:
   a. Check CEP (Custom Equipment Program) eligibility
   b. Compare income against thresholds:
      - Single: $28,000
      - Family: $39,000
   c. Calculate enhanced coverage if CEP eligible

6. Calculate confidence score
7. Create citations from ADP policy documents
8. Return eligibility, funding, exclusions, and CEP info
```

**Response Schema**:
```json
{
  "provenance": ["sql", "vector"],
  "confidence": 0.88,
  "eligibility": {
    "device_category": "respiratory",
    "device_type": "CPAP",
    "is_eligible": true,
    "criteria": "Diagnosis of sleep apnea with prescription"
  },
  "exclusions": [
    "Oxygen concentrators for travel use only",
    "Devices for non-medical purposes"
  ],
  "funding": {
    "adp_contribution": 75.0,
    "client_share_percent": 25.0,
    "adp_doc": "Respiratory Devices Manual",
    "section_ref": "Section 4.2",
    "scenario": "CPAP machine - standard coverage",
    "details": "ADP covers 75% of approved cost up to maximum..."
  },
  "cep": {
    "eligible": true,
    "income_threshold": 28000,
    "patient_income": 25000,
    "enhanced_coverage": "100% ADP funding for CEP-eligible clients"
  },
  "citations": [
    {
      "source": "ADP Respiratory Devices Manual",
      "loc": "Section 4.2 - CPAP Coverage",
      "url": "https://www.ontario.ca/page/assistive-devices-program"
    }
  ],
  "conflicts": [],
  "summary": "CPAP is eligible for 75% ADP funding. With patient income of $25,000, CEP eligibility provides 100% coverage."
}
```

### 3. odb_get

**Purpose**: ODB (Ontario Drug Benefit) formulary lookup with interchangeables

**Request Schema**:
```json
{
  "drug": "rosuvastatin",
  "check_alternatives": true,
  "include_lu": true,  // Include Limited Use criteria
  "top_k": 5
}
```

**Algorithm**:
```
1. Parse drug query and extract drug name
2. Execute dual-path retrieval in parallel:

   SQL Path:
     a. Query odb_drugs table:
        - LIKE search on name and generic_name fields
        - Retrieve DIN, pricing, benefit status, formulary sections
     b. If check_alternatives=true:
        - Get interchangeable_group_id for matched drugs
        - Query all drugs in same interchangeable group
        - Identify lowest_cost option (is_lowest_cost=true)
     c. Query odb_interchangeable_groups table:
        - Get group metadata (generic name, strength, dosage form)
        - Retrieve lowest_cost_din and pricing

   Vector Path:
     a. Query odb_documents collection (ChromaDB)
     b. Semantic search for drug policy text
     c. Filter by drug name/ingredient
     d. Retrieve Limited Use criteria if applicable

3. Merge SQL and vector results:
   a. Match drugs from SQL with LU criteria from vector
   b. Identify coverage status:
      - Full benefit (no restrictions)
      - Limited Use (requires LU code and criteria)
      - Exceptional Access (requires special authorization)
      - Not covered
   c. Compile interchangeable alternatives
   d. Identify lowest cost option
   e. Detect conflicts between sources

4. Calculate confidence score
5. Create citations from ODB formulary documents
6. Return coverage status, alternatives, lowest cost, and LU criteria
```

**Response Schema**:
```json
{
  "provenance": ["sql", "vector"],
  "confidence": 0.91,
  "coverage": {
    "covered": true,
    "din": "02247162",
    "name": "APO-ROSUVASTATIN",
    "generic_name": "Rosuvastatin Calcium",
    "strength": "10mg",
    "dosage_form": "Tablet",
    "individual_price": 0.45,
    "daily_cost": 0.45,
    "benefit_status": "Limited Use",
    "lu_required": true,
    "lu_code": "513",
    "lu_criteria": "For patients with cardiovascular disease or diabetes with additional risk factors..."
  },
  "interchangeable": [
    {
      "din": "02247162",
      "name": "APO-ROSUVASTATIN",
      "manufacturer": "Apotex",
      "individual_price": 0.45,
      "is_lowest_cost": true
    },
    {
      "din": "02247163",
      "name": "TEVA-ROSUVASTATIN",
      "manufacturer": "Teva",
      "individual_price": 0.48,
      "is_lowest_cost": false
    }
  ],
  "lowest_cost": {
    "din": "02247162",
    "name": "APO-ROSUVASTATIN",
    "individual_price": 0.45,
    "savings_vs_highest": 0.03
  },
  "citations": [
    {
      "source": "ODB Formulary - Limited Use Code 513",
      "loc": "Statins for Cardiovascular Prevention",
      "url": "https://www.ontario.ca/page/check-medication-coverage"
    }
  ],
  "conflicts": []
}
```

---

## Database Schemas

### SQL Database: ohip.db

Located at: `/app/data/ohip.db` (Railway production database)

#### Table: ohip_fee_schedule
```sql
CREATE TABLE ohip_fee_schedule (
    fee_code TEXT PRIMARY KEY,              -- OHIP billing code (e.g., "A001")
    description TEXT NOT NULL,              -- Service description
    amount REAL,                            -- Fee amount in CAD
    units TEXT,                             -- Billing units
    specialty TEXT,                         -- Medical specialty
    category TEXT,                          -- Service category
    subcategory TEXT,                       -- Service subcategory
    requirements TEXT,                      -- Billing requirements/restrictions
    notes TEXT,                             -- Additional notes
    effective_date DATE,                    -- When fee became effective
    end_date DATE,                          -- When fee expires (if applicable)
    page_number INTEGER,                    -- Page in schedule
    section TEXT,                           -- Schedule section name
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Indexes: idx_ohip_specialty, idx_ohip_category, idx_ohip_effective
-- **Record Count: 4,166**
```

#### Table: odb_drugs
```sql
CREATE TABLE odb_drugs (
    din TEXT PRIMARY KEY,                   -- Drug Identification Number
    name TEXT NOT NULL,                     -- Brand name
    generic_name TEXT,                      -- Generic/chemical name
    manufacturer_id TEXT,                   -- Manufacturer code
    strength TEXT,                          -- Drug strength (e.g., "500mg")
    dosage_form TEXT,                       -- Tablet, capsule, liquid, etc.
    item_number TEXT,                       -- ODB item number
    therapeutic_class TEXT,                 -- Therapeutic classification
    category TEXT,                          -- Formulary category
    interchangeable_group_id TEXT,          -- Interchangeable products group
    individual_price REAL,                  -- Price per unit
    daily_cost REAL,                        -- Average daily cost
    amount_mohltc_pays REAL,                -- Government reimbursement amount
    listing_date DATE,                      -- Date added to formulary
    status TEXT,                            -- Active, discontinued, etc.
    is_lowest_cost BOOLEAN DEFAULT FALSE,   -- Is lowest cost in group
    is_benefit BOOLEAN DEFAULT TRUE,        -- Full benefit status
    is_chronic_use BOOLEAN DEFAULT FALSE,   -- Chronic use category
    is_section_3 BOOLEAN DEFAULT FALSE,     -- Section 3: Hospital drugs
    is_section_3b BOOLEAN DEFAULT FALSE,    -- Section 3b: Smoking cessation
    is_section_3c BOOLEAN DEFAULT FALSE,    -- Section 3c: Specialty drugs
    is_section_9 BOOLEAN DEFAULT FALSE,     -- Section 9: Limited use
    is_section_12 BOOLEAN DEFAULT FALSE,    -- Section 12: Exceptional access
    additional_benefit_type TEXT,           -- Additional benefit details
    notes TEXT,                             -- Coverage notes
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Indexes: idx_odb_din, idx_odb_generic, idx_odb_group, idx_odb_therapeutic, idx_odb_lowest
-- **Record Count: 8,401**
```

#### Table: odb_interchangeable_groups
```sql
CREATE TABLE odb_interchangeable_groups (
    group_id TEXT PRIMARY KEY,              -- Interchangeable group ID
    generic_name TEXT NOT NULL,             -- Generic name for group
    therapeutic_class TEXT,                 -- Drug class
    category TEXT,                          -- Formulary category
    strength TEXT,                          -- Standard strength
    dosage_form TEXT,                       -- Standard form
    item_number TEXT,                       -- ODB item number
    member_count INTEGER DEFAULT 0,         -- Number of products in group
    lowest_cost_din TEXT,                   -- DIN of lowest cost option
    lowest_cost_price REAL,                 -- Lowest price in group
    daily_cost TEXT,                        -- Average daily cost
    notes TEXT,                             -- Group notes
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Indexes: idx_grp_generic, idx_grp_therapeutic
-- **Record Count: 2,369**
```

#### Table: adp_funding_rule
```sql
CREATE TABLE adp_funding_rule (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    adp_doc TEXT NOT NULL,                  -- ADP manual name (Mobility, Communication Aids)
    section_ref TEXT,                       -- Section number in manual
    scenario TEXT NOT NULL,                 -- Funding scenario description
    client_share_percent DECIMAL(5,2),      -- Client cost-share percentage
    details TEXT,                           -- Detailed funding rule text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(adp_doc, section_ref, scenario)
);
-- Computed: adp_contribution = 100 - client_share_percent
-- Indexes: idx_adp_funding_rule_doc, idx_adp_funding_rule_scenario
-- **Record Count: 735**
```

#### Table: adp_exclusion
```sql
CREATE TABLE adp_exclusion (
    exclusion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    adp_doc TEXT NOT NULL,                  -- ADP manual name
    section_ref TEXT,                       -- Section number
    phrase TEXT NOT NULL,                   -- Exclusion phrase/reason
    applies_to TEXT,                        -- Device categories affected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(adp_doc, phrase, COALESCE(section_ref, ''))
);
-- Indexes: idx_adp_exclusion_doc, idx_adp_exclusion_phrase
-- **Record Count: 1,101**
```

#### Table: act_eligibility_rule
```sql
CREATE TABLE act_eligibility_rule (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_ref TEXT NOT NULL,              -- Health Insurance Act section
    title TEXT NOT NULL,                    -- Rule title
    condition_json TEXT NOT NULL,           -- Eligibility conditions as JSON
    effect TEXT NOT NULL,                   -- Effect of rule
    max_duration_months INTEGER,            -- Maximum duration
    prerequisites_json TEXT,                -- Prerequisites as JSON
    notes TEXT,                             -- Additional notes
    line_range TEXT,                        -- Line numbers in Act
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(section_ref, title)
);
-- Indexes: idx_act_eligibility_section
-- **Record Count: 64**
```

#### Table: act_health_card_rule
```sql
CREATE TABLE act_health_card_rule (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_ref TEXT NOT NULL,              -- Health Insurance Act section
    obligation TEXT NOT NULL,               -- Health card obligation
    scope TEXT NOT NULL,                    -- Scope of obligation
    line_range TEXT,                        -- Line numbers in Act
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(section_ref, obligation, scope)
);
-- **Record Count: 11**
```

#### Table: document_chunks
```sql
CREATE TABLE document_chunks (
    chunk_id TEXT PRIMARY KEY,              -- Unique chunk identifier
    source_type TEXT NOT NULL,              -- ohip, adp, odb, act
    source_document TEXT NOT NULL,          -- Source file name
    chunk_text TEXT NOT NULL,               -- Text content
    chunk_index INTEGER,                    -- Position in document
    page_number INTEGER,                    -- Page reference
    section TEXT,                           -- Document section
    subsection TEXT,                        -- Document subsection
    start_char INTEGER,                     -- Start position
    end_char INTEGER,                       -- End position
    embedding_model TEXT,                   -- Model used for embeddings
    embedding_id TEXT,                      -- ChromaDB embedding ID
    metadata_json TEXT,                     -- Additional metadata as JSON
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Indexes: idx_chunk_source, idx_chunk_embedding
-- **Record Count: 191** (OHIP Schedule and Health Insurance Act chunks)
```

#### Table: chunk_fee_codes (Junction Table)
```sql
CREATE TABLE chunk_fee_codes (
    chunk_id TEXT NOT NULL,                 -- Reference to document_chunks
    fee_code TEXT NOT NULL,                 -- Reference to ohip_fee_schedule
    relevance_score REAL DEFAULT 1.0,       -- Relevance of chunk to fee code
    PRIMARY KEY (chunk_id, fee_code),
    FOREIGN KEY (chunk_id) REFERENCES document_chunks(chunk_id),
    FOREIGN KEY (fee_code) REFERENCES ohip_fee_schedule(fee_code)
);
-- Indexes: idx_chunk_fee_chunk, idx_chunk_fee_code
-- **Record Count: 8,392** (fee code to chunk relationships)
```

### Vector Database: ChromaDB Collections

Located at: `/app/data/chroma` (Railway production)

#### Collection: ohip_documents
- **Record Count**: 6,983 embeddings
- **Embedding Model**: text-embedding-3-small (1536 dimensions)
- **Purpose**: OHIP Schedule of Benefits semantic search

**Record Structure**:
```json
{
  "id": "chunk_ohip_schedule_p12_001",
  "document": "Text chunk from OHIP Schedule...",
  "embedding": [0.012, -0.034, ...],  // 1536-dim vector
  "metadata": {
    "chunk_index": 1,
    "has_rules": true,
    "has_tables": true,
    "source_type": "schedule",
    "page_ref": 12,
    "subsection": "General Assessment",
    "fee_code_count": 3,
    "parent_section": "CONSULTATIONS",
    "fee_codes_list": "A001,A003,A005",
    "has_notes": true
  }
}
```

**Metadata Fields**:
- `chunk_index`: Position in document
- `has_rules`: Boolean, contains billing rules
- `has_tables`: Boolean, contains tables
- `source_type`: schedule, act, preamble
- `page_ref`: Page number in schedule
- `subsection`: Subsection heading
- `fee_code_count`: Number of fee codes referenced
- `parent_section`: Major section name
- `fee_codes_list`: Comma-separated fee codes
- `has_notes`: Boolean, contains billing notes

#### Collection: adp_documents
- **Record Count**: 610 embeddings
- **Embedding Model**: text-embedding-3-small (1536 dimensions)
- **Purpose**: ADP policy and device eligibility semantic search

**Record Structure**:
```json
{
  "id": "adp_mobility_section_4_1_001",
  "document": "Text chunk from ADP Mobility Devices Manual...",
  "embedding": [0.023, -0.011, ...],
  "metadata": {
    "adp_doc": "Mobility Devices Manual",
    "exclusion_count": 2,
    "part": "mobility",
    "funding_count": 5,
    "page_num": 15,
    "section_id": "4.1",
    "policy_uid": "adp_mob_4_1",
    "title": "Wheelchair Eligibility",
    "topics": ["wheelchair", "eligibility", "funding"]
  }
}
```

**Metadata Fields**:
- `adp_doc`: Manual name (Mobility Devices, Communication Aids)
- `exclusion_count`: Number of exclusions in section
- `part`: mobility, communication
- `funding_count`: Number of funding rules in section
- `page_num`: Page number
- `section_id`: Section number in manual
- `policy_uid`: Unique policy identifier
- `title`: Section title
- `topics`: List of topic keywords

#### Collection: odb_documents
- **Record Count**: 10,815 embeddings
- **Embedding Model**: text-embedding-3-small (1536 dimensions)
- **Purpose**: ODB formulary policy and Limited Use criteria semantic search

**Record Structure**:
```json
{
  "id": "odb_policy_limited_use_diabetes_001",
  "document": "Limited Use criteria for antidiabetic agents...",
  "embedding": [-0.005, 0.041, ...],
  "metadata": {
    "source_document": "Limited Use Criteria",
    "chunk_index": 45,
    "source_file": "odb_limited_use.pdf",
    "source_type": "odb",
    "document_type": "formulary_policy"
  }
}
```

**Metadata Fields**:
- `source_document`: Source document name
- `chunk_index`: Position in document
- `source_file`: Source file name
- `source_type`: Always "odb"
- `document_type`: formulary_policy, coverage_criteria, benefit_notes

---

## Usage Examples

### Example 1: OHIP Fee Code Lookup
```python
# Query
"What is the billing code for a general assessment?"

# Tool: schedule_get
request = {
  "q": "general assessment",
  "codes": [],
  "include": ["codes", "fee", "limits", "documentation"],
  "top_k": 6
}

# Response includes:
# - Fee code A003
# - Amount $77.20
# - Requirements and restrictions
# - Related consultation codes
# - Page references in schedule
```

### Example 2: ADP Funding Inquiry
```python
# Query
"Can my patient get funding for a CPAP machine? Their income is $25,000."

# Tool: adp_get
request = {
  "query": "Can my patient get funding for a CPAP?",
  "patient_income": 25000
}

# Response includes:
# - Device category: respiratory
# - 75% ADP funding, 25% client share
# - CEP eligible (income < $28,000)
# - Enhanced coverage: 100% ADP funding via CEP
# - Eligibility criteria: sleep apnea diagnosis + prescription
# - ADP Respiratory Devices Manual citations
```

### Example 3: Drug Formulary Search with Alternatives
```python
# Query
"Is rosuvastatin covered under ODB? What's the cheapest option?"

# Tool: odb_get
request = {
  "drug": "rosuvastatin",
  "check_alternatives": true,
  "include_lu": true,
  "top_k": 5
}

# Response includes:
# - Coverage status: Yes (Limited Use)
# - LU Code 513 - Statins for CV prevention
# - DIN numbers for rosuvastatin products
# - APO-ROSUVASTATIN: $0.45/tablet (lowest cost)
# - TEVA-ROSUVASTATIN: $0.48/tablet
# - Savings: $0.03 per tablet with lowest cost option
# - Interchangeable group information
# - ODB formulary citations
```

---

## Data Sources

- **OHIP Schedule of Benefits**: Official fee schedule (effective 2024)
- **Health Insurance Act**: Ontario Regulation coverage rules
- **ADP Manuals**: Mobility Devices Manual, Communication Aids Manual
- **ODB Formulary**: Ontario Drug Benefit formulary database
- **Last Updated**: October 2025
