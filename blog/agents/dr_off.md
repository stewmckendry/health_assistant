# Dr. OFF - Ontario Finance & Formulary Agent

## Overview

**Dr. OFF** (Ontario Finance & Formulary) is a specialized AI agent that provides accurate, current guidance on Ontario healthcare financing, drug coverage, and assistive device funding for healthcare clinicians.

## Mission

Help healthcare providers navigate Ontario's complex healthcare coverage landscape by providing accurate information on OHIP billing, ODB drug formulary, and ADP device funding to optimize patient care while managing costs effectively.

## Target Users

- **Primary**: Healthcare clinicians practicing in Ontario (physicians, nurse practitioners, pharmacists)
- **Use Cases**:
  - OHIP billing code lookup and requirements
  - ODB drug formulary coverage and Limited Use criteria
  - Generic alternatives and cost-effective prescribing
  - ADP device eligibility and funding
  - Prior authorization requirements
  - Patient eligibility determination

## Types of Questions

1. **Billing**: OHIP billing codes, fees, billing requirements
2. **Drug Coverage**: ODB formulary status, Limited Use criteria, DIN numbers
3. **Device Funding**: ADP coverage, eligibility, funding percentages
4. **Eligibility**: Patient qualification criteria, income thresholds
5. **Documentation**: Required forms, submission processes

## Data Sources

Dr. OFF retrieves information from three primary Ontario healthcare financing databases:

### 1. OHIP Schedule of Benefits
- **Source Type**: Provincial billing codes and fee schedule
- **Content**: Billing codes, descriptions, fees, coverage rules
- **Update Frequency**: Annually with interim updates (monitored regularly)
- **Key Information**:
  - Fee codes and descriptions
  - Service fees (in CAD)
  - Billing requirements and conditions
  - Frequency limits
  - Related services and modifiers
  - Premium codes
- **Official URL**: https://www.ontario.ca/page/ohip-schedule-benefits-and-fees
- **Collection**: ohip_documents (ChromaDB - 379 chunks)
- **Processing**: Scraped from official MOH Schedule of Benefits, chunked by code/service

### 2. Ontario Drug Benefit (ODB) Formulary
- **Source Type**: Provincial drug formulary and coverage database
- **Content**: Drug coverage status, DINs, Limited Use criteria
- **Update Frequency**: Quarterly updates with monthly bulletins
- **Key Information**:
  - Drug coverage status (General Benefit, Limited Use, Exceptional Access)
  - Drug Identification Numbers (DINs)
  - Limited Use (LU) codes and criteria
  - Interchangeable products
  - Brand vs. generic options
  - Unit cost information
  - Prior authorization requirements
- **Official URL**: https://www.ontario.ca/page/check-medication-coverage/
- **API**: Ontario Formulary Search (https://www.formulary.health.gov.on.ca/)
- **Collection**: odb_documents (ChromaDB - 3,358 chunks)
- **Processing**: Scraped from ODB Formulary Search API and static files

### 3. Assistive Devices Program (ADP)
- **Source Type**: Provincial assistive device funding program
- **Content**: Device categories, eligibility, funding guidelines
- **Update Frequency**: Program updates as announced
- **Key Information**:
  - Eligible device categories
  - Funding percentages (typically 75% ADP / 25% client)
  - Patient eligibility criteria
  - Clinical requirements
  - Vendor authorization
  - Application procedures
  - Exceptional funding (CEP program)
- **Official URL**: https://www.ontario.ca/page/assistive-devices-program
- **Collection**: adp_documents (ChromaDB - 214 chunks)
- **Processing**: Scraped from ADP program guidelines and device lists

### 4. Ontario Government Health Sites (Web Search)
- **Source Type**: Real-time web information
- **Content**: Recent policy updates, program changes, announcements
- **Update Frequency**: Real-time via web search
- **Key URLs**:
  - ontario.ca
  - health.gov.on.ca
  - ontariohealth.ca
  - Trillium Drug Program
  - Ontario Pharmacists Association resources
- **Retrieval**: Web search tool (fallback for recent information)

### Data Processing Pipeline

1. **Document Collection**:
   - OHIP: Scraped from Schedule of Benefits PDF and HTML
   - ODB: API queries to Formulary Search + static document parsing
   - ADP: Scraped from program guidelines and eligibility documents

2. **Chunking Strategy**:
   - OHIP: By billing code and service description (typically 300-500 tokens)
   - ODB: By drug product and DIN (typically 400-600 tokens)
   - ADP: By device category and eligibility criteria (typically 400-700 tokens)

3. **Embedding**:
   - Model: OpenAI text-embedding-3-small
   - Dimensions: 1536
   - Semantic similarity search with metadata filtering

4. **Metadata Enrichment**:
   - OHIP: code, fee, schedule_section, service_type
   - ODB: din, drug_name, lu_code, coverage_type, ingredient
   - ADP: device_category, funding_percent, eligibility_criteria

5. **Quality Assurance**:
   - Validation against official sources
   - Regular updates from MOH bulletins
   - Cross-reference with OMA billing guides

### Trust and Verification

- **Trusted Domains**: 20 Ontario healthcare/government domains whitelisted
- **Citation Validation**: All sources include DINs, codes, or official URLs
- **Source Transparency**: Responses include specific codes, DINs, and formulary URLs
- **Confidence Scoring**: Based on exact matches, code specificity, and source currency

## System Instructions

Dr. OFF uses a structured 4-step workflow (internal reasoning only - not shown to users):

**STEP 1: PLAN** - Identify intent (Billing/Drug Coverage/Device Funding/Eligibility/Documentation) and required fields
**STEP 2: RETRIEVE** - Call appropriate MCP tools (schedule_get, odb_get, adp_get) and extract facts
**STEP 3: SELF-CHECK** - Verify completeness and fill gaps (must make ≥2 tool calls)
**STEP 4: SYNTHESIZE** - Format complete answer with specific codes, DINs, and fees

### Key Instructions
- Always follow 4-step workflow internally
- Make at least 2 tool calls per query
- Fill ≥90% of schema fields before synthesis
- Be extremely precise about what was asked (e.g., distinguish plain vs. combination formulations)
- Provide specific billing codes, DINs, and Limited Use codes
- Include cost information when available
- Suggest cost-effective alternatives when appropriate
- Use web_search as fallback when MCP tools insufficient

## MCP Tools

### 1. schedule_get
**Purpose**: OHIP Schedule of Benefits lookup with dual-path retrieval

**Request Parameters**:
- `query` (string): OHIP billing query (service description or code)
- `k` (int, optional): Number of results (default: 6)
- `filters` (dict, optional):
  - `codes` (List[str]): Direct code lookup (e.g., ["E083A", "E083B"])
  - `include` (str): Additional filtering

**Algorithm**:
1. Parse query for explicit codes
2. If codes provided in filters, do direct code lookup
3. Otherwise, semantic search in ohip_documents (379 chunks)
4. Rank by relevance and code match
5. Return with fee amounts and billing requirements

**Response Parameters**:
- `items` (list): Schedule items with code, description, fee, requirements
- `citations` (list): Source references with OHIP Schedule URLs
- `confidence` (float): Match confidence
- `provenance` (list): Retrieval path information

### 2. odb_get
**Purpose**: ODB Formulary lookup with interchangeable products

**Request Parameters**:
- `query` (string): Drug name, brand, or ingredient
- `k` (int, optional): Number of alternatives (default: 5)
- `filters` (dict, optional):
  - `din` (str): Direct DIN lookup
  - `ingredient` (str): Active ingredient name
  - `drug_class` (str): Therapeutic class
  - `check_alternatives` (bool): Find interchangeable products
  - `include_lu` (bool): Include Limited Use details
  - `formulary_only` (bool): Only covered drugs

**Algorithm**:
1. Search odb_documents (3,358 chunks) by drug name/ingredient
2. Identify coverage status (General Benefit/Limited Use/Exceptional Access)
3. Find interchangeable products (same ingredient, different manufacturer)
4. Calculate cost comparison (if pricing available)
5. Extract Limited Use criteria if applicable
6. Return with DINs and formulary URLs

**Response Parameters**:
- `coverage` (dict): Coverage status, DIN, LU code, criteria
- `interchangeable` (list): Alternative formulations with DINs and costs
- `lowest_cost` (dict): Most cost-effective option
- `citations` (list): ODB Formulary URLs with DINs
- `confidence` (float)
- `provenance` (list)

### 3. adp_get
**Purpose**: ADP device eligibility and funding lookup

**Request Parameters**:
- `query` (string): Natural language device query
- `k` (int, optional): Number of results (default: 10)
- `filters` (dict, optional):
  - `device_category` (str): Device type (e.g., "wheelchair", "walker")
  - `check` (str): Eligibility check type
  - `use_case` (str): Clinical use case
  - `patient_income` (str): Income level for CEP eligibility

**Algorithm**:
1. Search adp_documents (214 chunks) by device type/category
2. Retrieve eligibility criteria (age, diagnosis, functional assessment)
3. Extract funding information (ADP %, client %, CEP eligibility)
4. Identify application requirements and forms
5. Return with ADP program URLs

**Response Parameters**:
- `eligibility` (dict): Patient eligibility criteria
- `funding` (dict): ADP contribution %, client share %, CEP thresholds
- `exclusions` (list): Non-covered scenarios
- `cep` (dict): Exceptional funding eligibility (low-income)
- `citations` (list): ADP program URLs
- `confidence` (float)
- `provenance` (list)

### 4. web_search
**Purpose**: Fallback for recent policy updates or missing information

**Request Parameters**:
- `query` (string): Search query
- Domain restrictions: 20 Ontario healthcare/government domains

**Algorithm**:
1. Search restricted to trusted domains (ontario.ca, health.gov.on.ca, etc.)
2. Fetch relevant pages
3. Extract coverage/billing information
4. Return with source URLs

**Response Parameters**:
- Search results with URLs
- Content snippets
- Update dates

## ChromaDB Collections

### ohip_documents
- **Records**: 379 chunks
- **Embedding Dimension**: 1536 (OpenAI text-embedding-3-small)
- **Content**: OHIP Schedule of Benefits codes, fees, requirements
- **Schema**: text, metadata (code, fee, schedule_section, service_type, requirements)
- **Key Fields**: billing code, service description, fee amount (CAD), billing conditions

### odb_documents
- **Records**: 3,358 chunks
- **Embedding Dimension**: 1536
- **Content**: ODB Formulary drugs, DINs, Limited Use criteria
- **Schema**: text, metadata (din, drug_name, lu_code, coverage_type, ingredient, cost)
- **Key Fields**: DIN, brand name, generic name, coverage status, LU criteria, unit cost

### adp_documents
- **Records**: 214 chunks
- **Embedding Dimension**: 1536
- **Content**: ADP device categories, eligibility, funding guidelines
- **Schema**: text, metadata (device_category, funding_percent, eligibility_criteria, cep_eligible)
- **Key Fields**: device type, ADP funding %, client cost %, eligibility requirements

**Total Chunks**: 3,951
**Database Size**: 56.4 MB
**Location**: `data/dr_off_agent/processed/dr_off/chroma/`

## SQL Database

### dr_off_conversations.db
**Tables**:
- `agent_sessions`: Session tracking (session_id, created_at, updated_at)
- `agent_messages`: Message history (id, session_id, message_data, created_at)

**Purpose**: Conversation persistence using OpenAI Agents SDK SQLiteSession

## Technology Stack

### Web App Layer
- **Framework**: FastAPI
- **Endpoint**: `/agents/dr-off/stream` (POST)
- **Streaming**: Server-Sent Events (SSE)
- **Request Model**: DrOffStreamRequest (query, sessionId, userId, stream)
- **Response**: SSE stream with progress, text deltas, citations, tool calls

### Agent Layer
- **SDK**: OpenAI Agents Python SDK (`agents==0.1.x`)
- **Agent Class**: `DrOffAgent` (src/ai_agents/dr_off_agent/openai_agent.py)
- **Model**: gpt-5-mini (GPT-5 Mini with reasoning capability)
- **Reasoning**: Configurable effort level (auto/low/medium/high/off)
- **Session Management**: SQLiteSession for conversation history
- **Streaming**: Runner.run_streamed() with event handling

### Tools Layer
- **MCP Server**: FastMCP-based server (dr-off-server)
- **Communication**: STDIO protocol
- **Tools**: 3 MCP tools (schedule_get, odb_get, adp_get)
- **Web Search**: OpenAI WebSearchTool (20 Ontario healthcare/government domains)
- **Timeout**: 180 seconds for complex queries

### Database Layer
- **Vector DB**: ChromaDB v0.5.x (persistent client)
- **SQL DB**: SQLite3 (conversation history)
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Retrieval**: Cosine similarity search with metadata filtering

### Observability
- **Tracing**: Langfuse + Logfire (OTLP integration)
- **Instrumentation**: logfire.instrument_openai_agents()
- **Metrics**: Tool calls, codes found, DINs retrieved, confidence scores
- **Feedback**: Trace ID included in responses for user feedback

## Key Features

1. **4-Step Reasoning Workflow**: Ensures complete coverage/billing information
2. **Precise Query Interpretation**: Distinguishes between similar drugs/codes
3. **Cost Comparison**: Identifies lowest-cost alternatives
4. **Limited Use Criteria**: Extracts specific eligibility requirements
5. **Interchangeable Products**: Finds generic substitutions automatically
6. **Funding Calculations**: Provides ADP cost breakdowns
7. **Citation Specificity**: Includes exact codes, DINs, and fees
8. **Langfuse Tracing**: Complete observability and user feedback

## Example Usage

```python
from src.ai_agents.dr_off_agent.openai_agent import create_dr_off_agent

# Create agent
agent = await create_dr_off_agent()

# OHIP billing query
result = await agent.query(
    "What's the OHIP code for a comprehensive assessment?",
    session_id="session_123",
    user_id="user_456"
)

# ODB drug query
result = await agent.query(
    "Is rosuvastatin covered by ODB? What about the generic?",
    session_id="session_123"
)

# ADP device query (streaming)
async for event in agent.query_stream(
    "Can my patient get ADP funding for a power wheelchair?",
    session_id="session_123",
    user_id="user_456"
):
    if event['type'] == 'text':
        print(event['content'], end='', flush=True)
    elif event['type'] == 'citation':
        print(f"\nCitation: {event['content']['title']}")
```

## Performance Characteristics

- **Average Response Time**: 6-12 seconds (with tool calls)
- **Token Usage**: 1,500-4,000 tokens per query
- **MCP Tool Calls**: 2-3 per query (enforced minimum: 2)
- **Citations Per Response**: 2-5 sources (with specific codes/DINs)
- **Confidence Score**: Typically 0.85-0.95 for exact code/DIN matches

## Documentation

- Source code: `src/ai_agents/dr_off_agent/`
- MCP server: `src/ai_agents/dr_off_agent/mcp/server.py`
- Web endpoint: `src/web/api/dr_off_endpoint.py`
- Tests: `tests/dr_off_agent/`
