# Dr. OPA - Ontario Practice Advice Agent

## Overview

**Dr. OPA** (Ontario Practice Advice) is a specialized AI agent that provides accurate, current practice guidance from trusted Ontario healthcare authorities for healthcare clinicians.

## Mission

Provide comprehensive, evidence-based Ontario healthcare guidance by synthesizing information from authoritative sources including CPSO policies, Ontario Health programs, CEP clinical tools, PHO infection control guidelines, and Choosing Wisely recommendations.

## Target Users

- **Primary**: Healthcare clinicians practicing in Ontario (physicians, nurse practitioners, physician assistants)
- **Use Cases**:
  - Regulatory compliance and CPSO policy interpretation
  - Clinical pathway navigation and quality standards
  - Infection prevention and control protocols
  - Decision support tool access and usage
  - Choosing Wisely recommendations for avoiding unnecessary care

## Types of Questions

1. **CPSO Policy**: Regulatory requirements, professional expectations, college policies
2. **IPAC Guidelines**: Infection prevention and control protocols
3. **Clinical Programs**: Ontario Health programs, screening, care pathways
4. **Clinical Tools**: Decision support tools, algorithms, calculators (CEP)
5. **Quality Standards**: Ontario Health quality standards and best practices
6. **Choosing Wisely**: Avoiding unnecessary tests, procedures, overuse

## Data Sources

Dr. OPA retrieves information from five primary authoritative sources in Ontario healthcare:

### 1. College of Physicians and Surgeons of Ontario (CPSO)
- **Source Type**: Regulatory policies and professional expectations
- **Content**: Practice policies, advice documents, ethical guidelines
- **Update Frequency**: As policies are revised (monitored regularly)
- **Key Documents**:
  - Professional obligations and expectations
  - Medical records documentation requirements
  - Virtual care policies
  - Consent and capacity guidelines
  - Prescribing policies
- **URL**: https://www.cpso.on.ca/
- **Collection**: opa_cpso_corpus (366 chunks)

### 2. Public Health Ontario (PHO)
- **Source Type**: Infection prevention and control guidance
- **Content**: IPAC best practices, protocols, outbreak management
- **Update Frequency**: Regularly updated, especially during outbreaks
- **Key Documents**:
  - IPAC best practices
  - Routine practices and additional precautions
  - PPE recommendations
  - Cleaning and disinfection protocols
  - Respiratory pathogen guidance
- **URL**: https://www.publichealthontario.ca/
- **Collection**: opa_pho_corpus (132 chunks)

### 3. Centre for Effective Practice (CEP)
- **Source Type**: Clinical decision support tools and algorithms
- **Content**: Evidence-based clinical tools, calculators, pathways
- **Update Frequency**: Tools updated based on new evidence
- **Key Tools**:
  - Clinical decision support algorithms
  - Risk calculators
  - Treatment protocols
  - Screening tools
  - Management pathways
- **URL**: https://cep.health/
- **Collection**: opa_cep_corpus (57 chunks)

### 4. Ontario Health (Quality Standards)
- **Source Type**: Quality standards and best practice guidelines
- **Content**: Condition-specific quality standards, indicators
- **Update Frequency**: New standards released periodically
- **Key Standards**:
  - Chronic disease management (diabetes, hypertension, COPD)
  - Mental health conditions
  - Screening programs
  - Palliative care
  - Acute care pathways
- **URL**: https://www.ontariohealth.ca/ and https://www.hqontario.ca/
- **Collection**: opa_quality_standards_corpus (340 chunks)

### 5. Choosing Wisely Canada (Ontario)
- **Source Type**: Evidence-based recommendations to avoid unnecessary care
- **Content**: "Don't do" recommendations by specialty
- **Update Frequency**: New recommendations added regularly
- **Key Content**:
  - Unnecessary tests and procedures
  - Overuse of medications
  - Low-value care practices
  - Evidence rationale
  - Alternative approaches
- **URL**: https://choosingwiselycanada.org/
- **Collection**: opa_choosing_wisely_corpus (544 chunks)

### 6. Ontario Health Programs (Web Search)
- **Source Type**: Ministry of Health and Ontario Health programs
- **Content**: Program eligibility, referral pathways, coverage criteria
- **Update Frequency**: Real-time via web search
- **Key Programs**:
  - Screening programs (cancer, prenatal)
  - Chronic disease programs
  - Specialized services
  - Access criteria
  - Program transitions
- **URLs**: ontario.ca, health.gov.on.ca, ontariohealth.ca
- **Retrieval**: Web search tool (fallback)

### Data Processing Pipeline

1. **Document Collection**: Scraped from official websites and PDFs
2. **Chunking**: Documents split into semantic chunks (typically 500-1000 tokens)
3. **Embedding**: OpenAI text-embedding-3-small (1536 dimensions)
4. **Storage**: ChromaDB persistent collections with metadata
5. **Metadata Enrichment**: source_org, document_title, source_url, section_heading, policy_level
6. **Quality Assurance**: Manual review of high-priority documents

### Trust and Verification

- **Trusted Domains**: 20 Ontario healthcare domains whitelisted
- **Citation Validation**: All sources validated against is_trusted flag
- **Source Transparency**: Every response includes source URLs and document titles
- **Confidence Scoring**: Based on number of sources, relevance scores, and trusted source ratio

## System Instructions

Dr. OPA uses a structured 4-step workflow (internal reasoning only - not shown to users):

**STEP 1: PLAN** - Identify intent and required information fields
**STEP 2: RETRIEVE** - Call appropriate MCP tools and extract facts
**STEP 3: SELF-CHECK** - Verify completeness and fill gaps (must make ≥2 tool calls)
**STEP 4: SYNTHESIZE** - Format complete answer with proper markdown

### Key Instructions
- Always follow 4-step workflow internally
- Make at least 2 tool calls per query
- Fill ≥90% of schema fields before synthesis
- Use human-readable section headings (not schema field names)
- Provide rich, comprehensive detail with specific citations
- Use web_search as fallback when MCP tools insufficient
- Proper markdown formatting with blank lines between sections

## MCP Tools

### 1. opa_policy_check
**Purpose**: CPSO policy lookup with two-tier auto-classification

**Request Parameters**:
- `query` (string): Natural language policy question
- `k` (int, optional): Number of results (default: 5)
- `filters` (dict, optional): Filter by sources (e.g., `{"sources": ["cpso"]}`)

**Algorithm**:
1. Auto-classify query intent (catalog/discovery/specific)
2. Scope retrieval based on classification
3. Retrieve from ChromaDB opa_cpso_corpus (366 chunks)
4. Assemble parent context for specific queries
5. Return with citations and metadata

**Response Parameters**:
- `items` (list): Policy sections with text, metadata, relevance_score
- `citations` (list): Source references with URLs
- `confidence` (float): Retrieval confidence score
- `provenance` (list): Source tracking information

### 2. opa_ipac_guidance
**Purpose**: PHO infection prevention and control guidance

**Request Parameters**:
- `query` (string): IPAC-related question
- `k` (int, optional): Number of results
- `filters` (dict, optional): Filter options

**Algorithm**:
1. Query ChromaDB opa_pho_corpus (132 chunks)
2. Retrieve relevant IPAC guidance sections
3. Extract requirements vs. recommendations
4. Return with PHO document citations

**Response Parameters**:
- `items` (list): IPAC guidance sections
- `citations` (list): PHO document references
- `confidence` (float)

### 3. opa_clinical_tools
**Purpose**: CEP clinical decision support tools with two-tier retrieval

**Request Parameters**:
- `query` (string): Clinical tool question
- `k` (int, optional): Number of results
- `filters` (dict, optional): Tool type filters

**Algorithm**:
1. Auto-classify query (catalog/discovery/specific)
2. Search ChromaDB opa_cep_corpus (57 chunks)
3. Return tool descriptions, usage guidance, algorithms
4. Include CEP citations

**Response Parameters**:
- `items` (list): Tool information with usage guidance
- `citations` (list): CEP tool references
- `confidence` (float)

### 4. opa_quality_standards
**Purpose**: Ontario Health quality standards lookup

**Request Parameters**:
- `query` (string): Quality standard question
- `k` (int, optional): Number of results
- `filters` (dict, optional): Source filters

**Algorithm**:
1. Auto-classify and scope query
2. Search ChromaDB opa_quality_standards_corpus (340 chunks)
3. Retrieve quality statements and indicators
4. Return with Ontario Health citations

**Response Parameters**:
- `items` (list): Quality standard sections
- `citations` (list): Standard references with numbers/dates
- `confidence` (float)

### 5. opa_choosing_wisely
**Purpose**: Choosing Wisely recommendations

**Request Parameters**:
- `query` (string): Question about unnecessary care
- `k` (int, optional): Number of results
- `filters` (dict, optional): Specialty filters

**Algorithm**:
1. Search ChromaDB opa_choosing_wisely_corpus (544 chunks)
2. Retrieve "don't do" recommendations
3. Extract evidence rationale and alternatives
4. Return with Choosing Wisely citations

**Response Parameters**:
- `items` (list): Recommendations with rationale
- `citations` (list): Choosing Wisely references
- `confidence` (float)

### 6. opa_search_sections
**Purpose**: General multi-source search

**Request Parameters**:
- `query` (string): General clinical question
- `k` (int, optional): Number of results
- `filters` (dict, optional): Source filters

**Algorithm**:
1. Search across all 5 ChromaDB collections
2. Aggregate results by relevance
3. Deduplicate and rank
4. Return consolidated results

**Response Parameters**:
- `items` (list): Sections from multiple sources
- `citations` (list): Mixed source citations
- `confidence` (float)

### 7. opa_program_lookup
**Purpose**: Ontario Health program information

**Request Parameters**:
- `query` (string): Program-related question
- `k` (int, optional): Number of results
- `filters` (dict, optional): Program type filters

**Algorithm**:
1. Search program databases
2. Retrieve eligibility, referral pathways, coverage
3. Supplement with web search if needed
4. Return with program citations

**Response Parameters**:
- `items` (list): Program information
- `citations` (list): Program references
- `confidence` (float)

### 8. web_search
**Purpose**: Fallback for recent/missing information

**Request Parameters**:
- `query` (string): Search query
- Domain restrictions: 20 Ontario healthcare domains (CPSO, ontario.ca, etc.)

**Algorithm**:
1. Search restricted to trusted Ontario healthcare domains
2. Fetch relevant web pages
3. Extract information with citations
4. Return with web sources

**Response Parameters**:
- Search results with URLs
- Content snippets
- Domain information

## ChromaDB Collections

### opa_cpso_corpus
- **Records**: 366 chunks
- **Embedding Dimension**: 1536 (OpenAI text-embedding-3-small)
- **Content**: CPSO policies, expectations, advice documents
- **Schema**: text, metadata (source_org, document_title, source_url, section_heading, policy_level)

### opa_pho_corpus
- **Records**: 132 chunks
- **Embedding Dimension**: 1536
- **Content**: PHO infection prevention and control guidelines
- **Schema**: text, metadata (source_org, document_title, source_url, guidance_type)

### opa_cep_corpus
- **Records**: 57 chunks
- **Embedding Dimension**: 1536
- **Content**: CEP clinical decision support tools and algorithms
- **Schema**: text, metadata (source_org, tool_name, source_url, tool_type)

### opa_quality_standards_corpus
- **Records**: 340 chunks
- **Embedding Dimension**: 1536
- **Content**: Ontario Health quality standards
- **Schema**: text, metadata (source_org, standard_number, source_url, quality_statement)

### opa_choosing_wisely_corpus
- **Records**: 544 chunks
- **Embedding Dimension**: 1536
- **Content**: Choosing Wisely Canada recommendations
- **Schema**: text, metadata (source_org, recommendation_id, source_url, specialty)

**Total Chunks**: 1,439
**Database Size**: 41.3 MB
**Location**: `data/dr_opa_agent/chroma/`

## SQL Database

### dr_opa_conversations.db
**Tables**:
- `agent_sessions`: Session tracking (session_id, created_at, updated_at)
- `agent_messages`: Message history (id, session_id, message_data, created_at)

**Purpose**: Conversation persistence using OpenAI Agents SDK SQLiteSession

## Technology Stack

### Web App Layer
- **Framework**: FastAPI
- **Endpoint**: `/api/agents/dr-opa/stream` (POST)
- **Streaming**: Server-Sent Events (SSE)
- **Request Model**: StreamingDrOPARequest (query, sessionId, messageHistory)
- **Response**: SSE stream with progress, text deltas, citations, tool calls

### Agent Layer
- **SDK**: OpenAI Agents Python SDK (`agents==0.1.x`)
- **Agent Class**: `DrOPAAgent` (src/ai_agents/dr_opa_agent/openai_agent.py)
- **Model**: gpt-5-mini (GPT-5 Mini with reasoning capability)
- **Reasoning**: Configurable effort level (auto/low/medium/high/off)
- **Session Management**: SQLiteSession for conversation history
- **Streaming**: Runner.run_streamed() with event handling

### Tools Layer
- **MCP Server**: FastMCP-based server (dr-opa-server)
- **Communication**: STDIO protocol
- **Tools**: 8 MCP tools (opa_policy_check, opa_ipac_guidance, etc.)
- **Web Search**: OpenAI WebSearchTool (20 Ontario healthcare domains)
- **Timeout**: 180 seconds for complex queries

### Database Layer
- **Vector DB**: ChromaDB v0.5.x (persistent client)
- **SQL DB**: SQLite3 (conversation history)
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Retrieval**: Cosine similarity search with metadata filtering

### Observability
- **Tracing**: Langfuse + Logfire (OTLP integration)
- **Instrumentation**: logfire.instrument_openai_agents()
- **Metrics**: Tool calls, citations, confidence scores, processing time
- **Feedback**: Trace ID included in responses for user feedback

## Key Features

1. **4-Step Reasoning Workflow**: Ensures comprehensive, complete answers
2. **Two-Tier Retrieval**: Auto-classifies queries and scopes retrieval appropriately
3. **Multi-Source Integration**: Synthesizes information from 5+ trusted sources
4. **Citation Deduplication**: Prevents duplicate sources in responses
5. **Confidence Scoring**: Provides transparency on answer quality
6. **Streaming Progress**: Real-time updates on tool calls and reasoning
7. **Web Search Fallback**: Supplements MCP tools with recent web information
8. **Langfuse Tracing**: Complete observability and user feedback integration

## Example Usage

```python
from src.ai_agents.dr_opa_agent.openai_agent import create_dr_opa_agent

# Create agent
agent = await create_dr_opa_agent()

# Query (non-streaming)
result = await agent.query(
    "What are CPSO expectations for virtual care consent documentation?",
    session_id="session_123",
    user_id="user_456"
)

# Query (streaming)
async for event in agent.query_stream(
    "What are the IPAC requirements for N95 respirator fit testing?",
    session_id="session_123",
    user_id="user_456"
):
    if event['type'] == 'text':
        print(event['content'], end='', flush=True)
    elif event['type'] == 'citation':
        print(f"\nCitation: {event['content']['title']}")
```

## Performance Characteristics

- **Average Response Time**: 8-15 seconds (with tool calls)
- **Token Usage**: 2,000-5,000 tokens per query
- **MCP Tool Calls**: 2-4 per query (enforced minimum: 2)
- **Citations Per Response**: 3-8 trusted sources
- **Confidence Score**: Typically 0.85-0.95 for policy questions

## Documentation

- Source code: `src/ai_agents/dr_opa_agent/`
- MCP server: `src/ai_agents/dr_opa_agent/dr_opa_mcp/server.py`
- Web endpoint: `src/web/api/dr_opa_streaming_endpoint.py`
- Tests: `tests/dr_opa_agent/`
