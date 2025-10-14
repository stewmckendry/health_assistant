# Agent 97 - Evidence-Based Clinical Search

## Overview

**Agent 97** is a specialized AI agent that provides evidence-based clinical guidance from 97 trusted medical sources for healthcare professionals. Unlike patient-focused assistants, Agent 97 delivers professional, clinician-appropriate medical information without safety guardrails.

## Mission

Provide healthcare clinicians with rapid access to evidence-based medical information from authoritative sources including medical journals, clinical guidelines, academic medical centers, and health authorities to support clinical decision-making.

## Target Users

- **Primary**: Healthcare clinicians (physicians, nurse practitioners, physician assistants) - NOT patients
- **Use Cases**:
  - Evidence-based clinical guideline lookup
  - Latest research on treatment approaches
  - Diagnostic workup recommendations
  - Pharmacotherapy evidence
  - Risk assessment and stratification
  - Clinical practice standard verification

## Types of Questions

1. **Clinical Guidelines**: Current evidence-based guidelines for disease management
2. **Pharmacotherapy**: Latest evidence on medication efficacy and safety
3. **Diagnostic Approach**: Recommended workup and diagnostic criteria
4. **Treatment Protocols**: Evidence-based treatment algorithms
5. **Risk Assessment**: Clinical risk stratification tools and studies
6. **Comparative Effectiveness**: Comparing treatment options based on evidence

## Data Sources

Agent 97 searches 97 trusted medical domains in real-time using Claude AI with web search capabilities. Unlike Dr. OPA and Dr. OFF which use embedded ChromaDB collections, Agent 97 performs live web searches to access the most current medical information.

### Source Categories

#### 1. Medical Journals (Premier Tier)
- **New England Journal of Medicine** (NEJM) - nejm.org
- **The Lancet** - thelancet.com
- **JAMA** (Journal of the American Medical Association) - jamanetwork.com
- **BMJ** (British Medical Journal) - bmj.com
- **Annals of Internal Medicine** - annals.org
- **Circulation** - ahajournals.org
- **Nature Medicine** - nature.com
- **Cell** - cell.com
- **Updates**: Real-time via web search (latest publications)

#### 2. Clinical Practice Guidelines
- **NICE** (National Institute for Health and Care Excellence) - nice.org.uk
- **AHA/ACC** (American Heart Association/American College of Cardiology) - heart.org, acc.org
- **ADA** (American Diabetes Association) - diabetes.org
- **IDSA** (Infectious Diseases Society of America) - idsociety.org
- **ASCO** (American Society of Clinical Oncology) - asco.org
- **European Society of Cardiology** - escardio.org
- **Canadian Cardiovascular Society** - ccs.ca
- **Updates**: Guidelines updated annually or as new evidence emerges

#### 3. Academic Medical Centers
- **Mayo Clinic** - mayoclinic.org
- **Cleveland Clinic** - clevelandclinic.org
- **Johns Hopkins Medicine** - hopkinsmedicine.org
- **Massachusetts General Hospital** - massgeneral.org
- **UCSF Health** - ucsfhealth.org
- **MD Anderson Cancer Center** - mdanderson.org
- **Updates**: Clinical content updated regularly

#### 4. Health Authorities (International)
- **WHO** (World Health Organization) - who.int
- **CDC** (Centers for Disease Control and Prevention) - cdc.gov
- **NIH** (National Institutes of Health) - nih.gov
- **Health Canada** - canada.ca
- **FDA** (Food and Drug Administration) - fda.gov
- **European Medicines Agency** - ema.europa.eu
- **Updates**: Real-time guidance and recommendations

#### 5. Canadian Healthcare (Ontario Focus)
- **Ontario Health** - ontariohealth.ca
- **CPSO** (College of Physicians and Surgeons of Ontario) - cpso.on.ca
- **Canadian Medical Association** - cma.ca
- **College of Family Physicians of Canada** - cfpc.ca
- **Royal College of Physicians and Surgeons of Canada** - royalcollege.ca
- **Canadian Pharmacists Association** - pharmacists.ca
- **Updates**: Real-time via web search

#### 6. Evidence Databases
- **PubMed/MEDLINE** - pubmed.ncbi.nlm.nih.gov
- **Cochrane Library** - cochranelibrary.com
- **UpToDate** - uptodate.com
- **DynaMed** - dynamed.com
- **TRIP Database** - tripdatabase.com
- **Updates**: Continuously updated databases

### Search Strategy

Agent 97 uses **Claude AI with web search and web fetch tools** rather than pre-embedded documents:

**Advantages**:
- **Real-time information**: Access to latest publications and guidelines
- **No domain limit**: Claude supports all 97 domains (OpenAI WebSearchTool limited to 20)
- **Content freshness**: Always retrieves current information
- **Comprehensive coverage**: Full text access via web fetch

**Search Configuration**:
- **Primary Model**: Claude 3.5 Sonnet (claude-3-5-sonnet-latest)
- **Web Search Tool**: `web_search_20250305` (max 2 uses per query)
- **Web Fetch Tool**: `web_fetch_20250910` (max 5 uses per query)
- **Temperature**: 0.3 (lower for factual medical information)
- **Max Tokens**: 3,000 (higher for clinical detail)

### Trust and Verification

- **Trusted Domains**: All 97 domains whitelisted in domains.yaml
- **Citation Tracking**: URLs and titles extracted from Claude's citations
- **Source Transparency**: Every response includes source links
- **No Domain Restrictions**: Unlike OpenAI's 20-domain limit, Claude handles all 97 domains

## System Instructions

Agent 97's system instructions emphasize **clinician-focused, evidence-based guidance**:

### Key Principles

1. **Target Audience**: Healthcare clinicians, NOT patients
2. **Professional Language**: Direct clinical terminology without patient disclaimers
3. **Evidence Quality**: Note evidence levels (RCT, meta-analysis, expert consensus)
4. **Specific Details**: Include doses, protocols, diagnostic criteria
5. **Authoritative Sources**: Reference medical societies, journals, guidelines

### Response Format

- Direct, professional clinical language
- Specific details clinicians need (doses, protocols, criteria)
- Citations from authoritative sources with URLs
- Evidence quality indicators (e.g., "based on RCT", "expert consensus")
- NO patient safety disclaimers (users are clinicians)

### Markdown Requirements

- Proper section headers (## for main sections, ### for subsections)
- Blank lines between all sections
- Bullet lists with proper formatting
- **Bold** for emphasis, *italics* for terms
- Inline citations: [Source Name](URL)

## MCP Tools

### 1. clinician_search
**Purpose**: Search 97 trusted medical sources for evidence-based clinical information

**Request Parameters**:
- `query` (string): The clinical question to research
- `session_id` (string, optional): Session identifier for tracking
- `user_id` (string, optional): User identifier
- `max_web_search_uses` (int, optional): Max web searches (default: 2)
- `max_web_fetch_uses` (int, optional): Max sources to fetch (default: 5)

**Algorithm**:
1. Receive clinical query from orchestrator or direct user
2. Initialize Claude client with web tools beta headers
3. Configure web_search tool with all 97 trusted domains
4. Configure web_fetch tool with citation tracking
5. Call Claude API with clinician-focused system prompt
6. Claude automatically uses web_search (up to 2x) and web_fetch (up to 5x)
7. Extract response text and citations from Claude's response
8. Return structured response with content, citations, tool usage

**Response Parameters**:
- `success` (bool): Whether search completed successfully
- `request_id` (string): Unique request identifier
- `content` (string): Clinical guidance text with inline citations
- `citations` (list): Extracted citations with URLs, titles, domains
- `tool_calls` (list): Tools used by Claude (web_search, web_fetch)
- `model` (string): Claude model used (claude-3-5-sonnet-latest)
- `usage` (dict): Token usage (input_tokens, output_tokens)
- `session_id` (string): Session identifier
- `processing_time` (float): Time in seconds
- `note` (string): "Clinician-focused search from 97 trusted medical sources"

### 2. clinician_search_get_domains
**Purpose**: Get the list of 97 trusted medical domains

**Request Parameters**:
- `include_categories` (bool, optional): Whether to include categorization

**Response Parameters**:
- `success` (bool)
- `total_domains` (int): 97
- `domains` (list): List of trusted domain strings
- `categories` (dict, optional): Domain categorization (journals, guidelines, etc.)
- `note` (string): Description

### 3. clinician_search_health_check
**Purpose**: Check health status of the clinician search service

**Request Parameters**: None

**Response Parameters**:
- `success` (bool): Overall health status
- `server` (string): "healthy" or "unhealthy"
- `timestamp` (string): ISO timestamp
- `session_id` (string)
- `components` (dict): Health of anthropic_client, anthropic_api, trusted_domains, logging

## No ChromaDB Collections

**Agent 97 does NOT use ChromaDB**. Instead, it performs real-time web searches via Claude AI. This design choice provides:

- **Current Information**: Always up-to-date with latest publications
- **Broader Coverage**: Access to full text of articles and guidelines
- **No Maintenance**: No need to re-embed documents
- **Flexibility**: Can search any of the 97 domains dynamically

## SQL Database

### agent_97_conversations.db
**Tables**:
- `agent_sessions`: Session tracking (session_id, created_at, updated_at)
- `agent_messages`: Message history (id, session_id, message_data, created_at)

**Purpose**: Conversation persistence using OpenAI Agents SDK SQLiteSession

## Technology Stack

### Web App Layer
- **Framework**: FastAPI
- **Endpoint**: `/agents/agent-97/stream` (POST)
- **Streaming**: Server-Sent Events (SSE)
- **Request Model**: Agent97StreamRequest (query, sessionId, userId, stream)
- **Response**: SSE stream with progress, text deltas, citations, tool calls

### Agent Layer
- **SDK**: OpenAI Agents Python SDK (`agents==0.1.x`)
- **Agent Class**: `Agent97Agent` (src/ai_agents/agent_97/openai_agent.py)
- **Model**: gpt-5-mini (GPT-5 Mini for orchestration)
- **Reasoning**: Configurable effort level (auto/low/medium/high/off)
- **Session Management**: SQLiteSession for conversation history
- **Streaming**: Runner.run_streamed() with event handling

### Tools Layer
- **MCP Server**: FastMCP-based server (agent-97-clinician-search)
- **Communication**: STDIO protocol
- **Tool**: 1 primary MCP tool (clinician_search) + 2 utility tools
- **Backend**: Anthropic Claude API (claude-3-5-sonnet-latest)
- **Web Search**: Claude native web_search_20250305 (all 97 domains)
- **Web Fetch**: Claude native web_fetch_20250910 with citations
- **Timeout**: 180 seconds for complex searches

### Search Layer (Claude AI)
- **API**: Anthropic Claude API
- **Model**: claude-3-5-sonnet-latest
- **Temperature**: 0.3 (factual medical information)
- **Max Tokens**: 3,000 (detailed clinical responses)
- **Tools**: web_search (max 2), web_fetch (max 5)
- **Beta Headers**: "web-search-2025-03-05,web-fetch-2025-09-10"
- **Domain Coverage**: All 97 domains (no limit like OpenAI's 20)

### Database Layer
- **Vector DB**: None (real-time search instead)
- **SQL DB**: SQLite3 (conversation history only)
- **Configuration**: domains.yaml (97 trusted domains)

### Observability
- **Tracing**: Langfuse + Logfire (OTLP integration)
- **Instrumentation**: logfire.instrument_openai_agents()
- **Metrics**: Tool calls, citations found, processing time, token usage
- **Feedback**: Trace ID included in responses for user feedback

## Key Features

1. **Real-Time Search**: Always current information from 97 sources
2. **No Domain Limit**: Claude supports all 97 domains (vs OpenAI's 20 limit)
3. **Clinician-Focused**: Professional language without patient guardrails
4. **Citation Extraction**: Automatic citation tracking from Claude responses
5. **Evidence Quality**: Notes RCTs, meta-analyses, guideline levels
6. **Comprehensive Detail**: Includes doses, protocols, diagnostic criteria
7. **Streaming Progress**: Real-time updates on search progress
8. **Langfuse Tracing**: Complete observability and user feedback

## Example Usage

```python
from src.ai_agents.agent_97.openai_agent import create_agent_97

# Create agent
agent = await create_agent_97()

# Clinical guideline query
result = await agent.query(
    "What are the current guidelines for hypertension management in adults?",
    session_id="session_123",
    user_id="user_456"
)

# Pharmacotherapy query (streaming)
async for event in agent.query_stream(
    "What is the latest evidence on SGLT2 inhibitors for heart failure with preserved ejection fraction?",
    session_id="session_123",
    user_id="user_456"
):
    if event['type'] == 'text':
        print(event['content'], end='', flush=True)
    elif event['type'] == 'citation':
        print(f"\nCitation: {event['content']['title']} - {event['content']['url']}")
```

## Performance Characteristics

- **Average Response Time**: 10-20 seconds (Claude API + web search/fetch)
- **Token Usage**: 2,500-5,000 tokens per query (Claude)
- **MCP Tool Calls**: 1 (clinician_search)
- **Web Searches**: Up to 2 per query (Claude internal)
- **Web Fetches**: Up to 5 per query (Claude internal)
- **Citations Per Response**: 3-10 medical sources
- **Confidence Score**: 0.9 (high-quality trusted sources)

## Documentation

- Source code: `src/ai_agents/agent_97/`
- MCP server: `src/ai_agents/agent_97/mcp/clinician_search_server.py`
- Web endpoint: `src/web/api/agent_97_endpoint.py`
- Domains config: `src/config/domains.yaml`
- Tests: `tests/agent_97/`

## Comparison with Dr. OPA and Dr. OFF

| Feature | Agent 97 | Dr. OPA / Dr. OFF |
|---------|----------|-------------------|
| **Data Storage** | No embedding (real-time search) | ChromaDB embedded collections |
| **Information Currency** | Real-time (always current) | Periodic updates required |
| **Source Coverage** | 97 domains via Claude | 5-6 sources (Dr. OPA), 3 sources (Dr. OFF) |
| **Domain Limit** | No limit (Claude) | 20 domains (OpenAI WebSearchTool) |
| **Backend** | Claude 3.5 Sonnet | GPT-5 Mini |
| **Search Mechanism** | Claude web_search + web_fetch | Vector similarity search |
| **Update Process** | Automatic (web search) | Manual re-embedding |
| **Best For** | Latest evidence, guidelines | Regulatory policies, billing codes |
| **Target Scope** | Global medical evidence | Ontario-specific guidance |
