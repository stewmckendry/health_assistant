# Chief Resident - Clinical Intelligence Orchestrator

## Overview

**Chief Resident** is an intelligent medical orchestrator inspired by Microsoft's MAI-DxO (Medical AI Diagnostic Orchestrator) that coordinates between Dr. OPA, Dr. OFF, and Agent 97 to provide comprehensive clinical decision support for Ontario healthcare providers.

## Mission

Provide comprehensive, Ontario-contextualized clinical guidance by intelligently routing queries to specialist AI agents (Dr. OPA, Dr. OFF, Agent 97) and synthesizing their responses into cohesive, actionable clinical recommendations.

## Target Users

- **Primary**: Healthcare clinicians practicing in Ontario who need comprehensive guidance across multiple domains
- **Use Cases**:
  - Complex clinical cases requiring multiple perspectives
  - Questions spanning clinical evidence, regulatory requirements, and coverage
  - Diagnostic workup with Ontario-specific considerations
  - Treatment planning with formulary and billing integration
  - Chronic disease management with quality standards and coverage
  - Regulatory compliance with evidence-based practice

## Types of Questions

Chief Resident handles complex queries requiring consultation with multiple specialist agents:

### 1. **Diagnosis & Workup**
Consults: Agent 97 → Dr. OPA → Dr. OFF
- Differential diagnosis approaches
- Test ordering and interpretation
- Ontario screening programs
- OHIP billing for diagnostics

### 2. **Treatment & Management**
Consults: Agent 97 → Dr. OPA → Dr. OFF
- Evidence-based treatment recommendations
- Ontario quality standards and pathways
- ODB drug coverage and alternatives
- OHIP billing codes for procedures

### 3. **Medication Questions**
Consults: Agent 97 → Dr. OPA → Dr. OFF
- Evidence-based pharmacotherapy
- Choosing Wisely guidance (avoiding inappropriate prescribing)
- ODB formulary coverage and Limited Use criteria
- Cost comparison and generic alternatives

### 4. **Infections & Antibiotics**
Consults: Agent 97 → Dr. OPA → Dr. OFF
- Evidence-based infectious disease management
- PHO IPAC guidance
- ODB antibiotic coverage
- OHIP billing for cultures/diagnostics

### 5. **Chronic Disease Management**
Consults: Agent 97 → Dr. OPA → Dr. OFF
- Evidence-based disease management
- Ontario Health quality standards
- Screening eligibility and programs
- ODB coverage for disease management drugs

### 6. **Regulatory/Documentation**
Consults: Dr. OPA (primary) → Dr. OFF
- CPSO policies and professional obligations
- Consent and documentation requirements
- OHIP billing documentation

### 7. **Simple Coverage Questions**
Consults: Dr. OFF (may be sufficient alone)
- OHIP/ODB/ADP coverage
- Billing codes only

## Data Sources

Chief Resident does NOT have its own data sources. Instead, it orchestrates access to the data sources of its three specialist agents:

### Via Dr. OPA (1,439 chunks total)
1. **CPSO Policies** (366 chunks) - Regulatory requirements
2. **PHO IPAC Guidelines** (132 chunks) - Infection control
3. **CEP Clinical Tools** (57 chunks) - Decision support tools
4. **Ontario Health Quality Standards** (340 chunks) - Best practices
5. **Choosing Wisely** (544 chunks) - Avoiding unnecessary care

### Via Dr. OFF (3,951 chunks total)
1. **OHIP Schedule of Benefits** (379 chunks) - Billing codes and fees
2. **ODB Formulary** (3,358 chunks) - Drug coverage and DINs
3. **ADP Program** (214 chunks) - Assistive device funding

### Via Agent 97 (97 domains, real-time search)
1. **Medical Journals** - NEJM, Lancet, JAMA, BMJ, etc.
2. **Clinical Guidelines** - NICE, AHA/ACC, ADA, IDSA, etc.
3. **Academic Medical Centers** - Mayo, Cleveland Clinic, Hopkins, etc.
4. **Health Authorities** - WHO, CDC, NIH, Health Canada, etc.
5. **Canadian Healthcare** - Ontario Health, CPSO, CMA, CFPC, etc.
6. **Evidence Databases** - PubMed, Cochrane, UpToDate, etc.

### Data Integration Strategy

**Orchestration Algorithm**:
1. Analyze clinical query intent
2. Determine which specialist agents to consult
3. Call agents in parallel when possible (gpt-5-mini with `parallel_tool_calls=True`)
4. Synthesize responses into cohesive narrative
5. Preserve all citations from individual agents
6. Highlight critical safety information and conflicts

**Synthesis Approach**:
- Integrate evidence (Agent 97) with Ontario context (Dr. OPA, Dr. OFF)
- Resolve conflicts between sources (more authoritative, recent, specific wins)
- Emphasize safety and regulatory requirements
- Provide practical implementation guidance

## System Instructions

Chief Resident uses an **extended thinking/reasoning** capability to process agent consultations internally before responding.

### Orchestration Strategy

**CRITICAL**: For EVERY clinical query, Chief must call at least one specialist agent. Never answer from knowledge alone.

**Clinical Intent → Agents to Call**:

1. **Diagnosis & Workup** → agent_97 + dr_opa + dr_off
2. **Treatment & Management** → agent_97 + dr_opa + dr_off
3. **Medication Questions** → agent_97 + dr_opa + dr_off
4. **Infections & Antibiotics** → agent_97 + dr_opa + dr_off
5. **Chronic Disease Management** → agent_97 + dr_opa + dr_off
6. **Regulatory/Documentation** → dr_opa (primary) + dr_off
7. **Simple Coverage Questions** → dr_off (may be sufficient alone)

**DEFAULT**: When in doubt, call all three agents for comprehensive Ontario-contextualized guidance.

### Reasoning Requirements

Use extended thinking/reasoning capability to:
- Summarize key findings from each agent consulted
- Identify inconsistencies or contradictions between responses
- Reason through conflict resolution (which source is more authoritative, recent, specific)
- Perform internal deliberation BEFORE final response
- Present synthesized, resolved guidance without exposing internal reasoning

### Response Format

**Natural, comprehensive orchestrated guidance** with proper markdown:

- **No formal templates** - Start directly with answer
- **1-2 comprehensive opening paragraphs** - Synthesize most critical information
- **Natural section headings** - Based on query relevance (e.g., "## Clinical Approach", "## Coverage and Costs")
- **Embedded citations** - [Source: [CPSO Policy](URL)]
- **Organized by importance** - Lead with what matters most for the clinical decision
- **Blank lines between sections** - Proper markdown formatting
- **Include medical disclaimers** - Educational purposes only

## MCP Tools (Specialist Agents as Tools)

Chief Resident uses the OpenAI Agents SDK `as_tool()` pattern to convert specialist agents into callable tools:

### 1. dr_opa (Agent as Tool)
**Purpose**: Consult Dr. OPA for Ontario practice guidance

**Tool Description**: "Consult Dr. OPA for Ontario practice guidance, CPSO policies, clinical pathways, and regulatory requirements. Has access to MCP tools for retrieving official Ontario healthcare policies."

**Algorithm**:
1. Chief calls `dr_opa` tool with clinical query
2. Dr. OPA agent receives query
3. Dr. OPA uses its MCP tools (opa_policy_check, opa_ipac_guidance, etc.)
4. Dr. OPA synthesizes response with citations
5. Response returned to Chief for integration

**Response**: Full Dr. OPA response with citations, tool calls, and metadata

### 2. dr_off (Agent as Tool)
**Purpose**: Consult Dr. OFF for Ontario healthcare financing

**Tool Description**: "Consult Dr. OFF for Ontario healthcare financing, OHIP billing codes, ODB drug coverage, and ADP device funding. Has access to MCP tools for retrieving coverage and billing information."

**Algorithm**:
1. Chief calls `dr_off` tool with clinical query
2. Dr. OFF agent receives query
3. Dr. OFF uses its MCP tools (schedule_get, odb_get, adp_get)
4. Dr. OFF synthesizes response with specific codes, DINs, fees
5. Response returned to Chief for integration

**Response**: Full Dr. OFF response with billing codes, DINs, coverage details

### 3. agent_97 (Agent as Tool)
**Purpose**: Consult Agent 97 for evidence-based clinical guidance

**Tool Description**: "Consult Agent 97 for evidence-based clinical guidance from 97 trusted medical sources. Has access to MCP tool for searching medical literature, guidelines, and authoritative clinical resources for healthcare professionals."

**Algorithm**:
1. Chief calls `agent_97` tool with clinical query
2. Agent 97 receives query
3. Agent 97 uses its MCP tool (clinician_search with Claude API)
4. Claude performs web_search and web_fetch on 97 domains
5. Agent 97 synthesizes evidence-based response
6. Response returned to Chief for integration

**Response**: Full Agent 97 response with citations from medical literature

## No Direct MCP Tools

Chief Resident **does NOT have its own MCP tools**. It exclusively uses the three specialist agents as tools via the `as_tool()` pattern. Each specialist agent manages its own MCP server and tools internally.

## No ChromaDB Collections

Chief Resident **does NOT have its own ChromaDB collections**. It accesses data through its specialist agents:
- Dr. OPA: 1,439 chunks across 5 collections
- Dr. OFF: 3,951 chunks across 3 collections
- Agent 97: Real-time web search (no embedding)

## SQL Database

### orchestrator_conversations.db
**Tables**:
- `agent_sessions`: Session tracking (session_id, created_at, updated_at)
- `agent_messages`: Message history (id, session_id, message_data, created_at)

**Purpose**: Conversation persistence using OpenAI Agents SDK SQLiteSession

## Technology Stack

### Web App Layer
- **Framework**: FastAPI
- **Endpoint**: `/api/agents/orchestrator/stream` (POST)
- **Streaming**: Server-Sent Events (SSE)
- **Request Model**: OrchestratorStreamRequest (query, sessionId, userId, stream)
- **Response**: SSE stream with progress, text deltas, citations, agent consultations

### Orchestrator Layer
- **SDK**: OpenAI Agents Python SDK (`agents==0.1.x`)
- **Orchestrator Class**: `DiagnosticOrchestrator` (src/ai_agents/diagnostic_orchestrator/orchestrator_agent.py)
- **Model**: gpt-5-mini (GPT-5 Mini with reasoning capability)
- **Reasoning**: Configurable effort level (auto/low/medium/high/off)
- **Parallel Execution**: `parallel_tool_calls=True` for speed
- **Timeout**: 300 seconds (5 minutes - must wait for all sub-agents)
- **Session Management**: SQLiteSession for conversation history
- **Streaming**: Runner.run_streamed() with event handling

### Specialist Agents Layer
Chief initializes three specialist agent instances:

#### Dr. OPA Wrapper
- **Class**: `DrOPAAgent`
- **Langfuse**: Disabled (orchestrator handles tracing)
- **MCP Server**: dr-opa-server (STDIO)
- **Tools**: 8 MCP tools + web_search
- **Model**: gpt-5-mini
- **Reasoning**: Inherited from orchestrator

#### Dr. OFF Wrapper
- **Class**: `DrOffAgent`
- **Langfuse**: Disabled (orchestrator handles tracing)
- **MCP Server**: dr-off-server (STDIO)
- **Tools**: 3 MCP tools + web_search
- **Model**: gpt-5-mini
- **Reasoning**: Inherited from orchestrator

#### Agent 97 Wrapper
- **Class**: `Agent97Agent`
- **Langfuse**: Disabled (orchestrator handles tracing)
- **MCP Server**: agent-97-clinician-search (STDIO)
- **Tool**: 1 MCP tool (clinician_search via Claude API)
- **Model**: gpt-5-mini
- **Reasoning**: Inherited from orchestrator

### Tools Layer (Sub-Agents)
- **Agent Conversion**: Each specialist agent converted to tool via `as_tool()`
- **Tool Names**: "dr_opa", "dr_off", "agent_97"
- **Communication**: Function call → Agent execution → Response
- **Parallel Execution**: Chief can call multiple agents simultaneously

### Database Layer
- **Vector DB**: Accessed via specialist agents (Dr. OPA, Dr. OFF)
- **SQL DB**: SQLite3 (orchestrator conversation history)
- **Specialist Agents**: Each has own MCP server and data access

### Observability
- **Tracing**: Langfuse + Logfire (OTLP integration) at orchestrator level only
- **Instrumentation**: logfire.instrument_openai_agents()
- **Sub-Agent Tracing**: Disabled to avoid conflicts
- **Metrics**: Agents consulted, tool calls, citations, synthesis quality
- **Feedback**: Trace ID included in responses for user feedback

## Key Features

1. **Multi-Agent Orchestration**: Coordinates 3 specialist agents as tools
2. **Parallel Execution**: Calls agents simultaneously when possible
3. **Intelligent Routing**: Determines which agents to consult based on query intent
4. **Extended Reasoning**: Internal deliberation before synthesizing response
5. **Conflict Resolution**: Resolves contradictions between agent responses
6. **Citation Preservation**: Maintains all sources from individual agents
7. **Streaming Progress**: Real-time updates on agent consultations
8. **Ontario Contextualization**: Integrates global evidence with Ontario-specific guidance
9. **Safety Emphasis**: Highlights critical safety information and regulatory requirements
10. **Langfuse Tracing**: Complete observability at orchestrator level

## Example Usage

```python
from src.ai_agents.diagnostic_orchestrator.orchestrator_agent import create_diagnostic_orchestrator

# Create orchestrator
orchestrator = await create_diagnostic_orchestrator()

# Complex clinical query (non-streaming)
result = await orchestrator.orchestrate(
    "I have a 72-year-old patient with newly diagnosed type 2 diabetes, BMI 32, and limited income. What are the CPSO documentation requirements, ODB coverage options for metformin and newer diabetes drugs, and evidence-based management approaches?",
    session_id="session_123",
    user_id="user_456"
)

# Streaming orchestration
async for event in orchestrator.orchestrate_stream(
    "55-year-old presenting with acute chest pain and shortness of breath. Need Ontario cardiac pathway, OHIP billing codes for ECG and troponins, and current ACS management guidelines.",
    session_id="session_123",
    user_id="user_456"
):
    if event['type'] == 'progress':
        print(f"Progress: {event['message']}")
    elif event['type'] == 'text':
        print(event['content'], end='', flush=True)
    elif event['type'] == 'agent_consultation':
        print(f"\nConsulting: {event['content']['agent']}")
    elif event['type'] == 'citation':
        print(f"\nCitation: {event['content']['title']}")
```

## Performance Characteristics

- **Average Response Time**: 20-45 seconds (orchestrating 2-3 agents)
- **Token Usage**: 5,000-15,000 tokens per query (across all agents)
- **Agents Consulted**: 2-3 per query (default: all 3)
- **Tool Calls**: 6-12 total (Chief → Agents → MCP tools)
- **Citations Per Response**: 8-20 mixed sources (policies, evidence, billing)
- **Confidence Score**: 0.9 (high due to multi-agent synthesis)
- **Parallel Execution**: Agents called simultaneously when independent

## Orchestration Flow Diagram

```
User Query
    ↓
Chief Resident (gpt-5-mini)
    ↓ [Reasoning: Analyze intent]
    ↓
    ├─→ dr_opa (as_tool)
    │       ↓
    │   Dr. OPA Agent (gpt-5-mini)
    │       ↓
    │   MCP Server (dr-opa-server)
    │       ↓
    │   [opa_policy_check, opa_ipac_guidance, etc.]
    │       ↓
    │   ChromaDB (1,439 chunks)
    │       ↓
    │   Response + Citations
    │
    ├─→ dr_off (as_tool)
    │       ↓
    │   Dr. OFF Agent (gpt-5-mini)
    │       ↓
    │   MCP Server (dr-off-server)
    │       ↓
    │   [schedule_get, odb_get, adp_get]
    │       ↓
    │   ChromaDB (3,951 chunks)
    │       ↓
    │   Response + Citations
    │
    └─→ agent_97 (as_tool)
            ↓
        Agent 97 (gpt-5-mini)
            ↓
        MCP Server (agent-97-clinician-search)
            ↓
        clinician_search
            ↓
        Claude API (claude-3-5-sonnet-latest)
            ↓
        web_search + web_fetch (97 domains)
            ↓
        Response + Citations
    ↓
Chief Resident [Reasoning: Synthesize]
    ↓
    - Summarize each agent's findings
    - Identify conflicts
    - Resolve contradictions
    - Integrate into cohesive narrative
    ↓
Final Response (with all citations)
```

## Documentation

- Source code: `src/ai_agents/diagnostic_orchestrator/`
- Main orchestrator: `orchestrator_agent.py`
- HTTP version: `orchestrator_agent_http.py`
- Web endpoint: `src/web/api/orchestrator_endpoint.py`
- Streaming progress: `streaming_progress.py`
- API documentation: `docs/CHIEF_RESIDENT_API.md`
- Tests: `tests/orchestrator/`

## Inspiration: Microsoft MAI-DxO

Chief Resident is inspired by Microsoft's **MAI-DxO (Medical AI Diagnostic Orchestrator)** approach:

- **Multi-Agent Coordination**: Like MAI-DxO, uses specialized agents for different domains
- **Intelligent Routing**: Routes queries to appropriate specialists
- **Synthesis**: Combines multiple perspectives into unified guidance
- **Ontario Focus**: Adapted for Ontario healthcare context with provincial specialists
- **as_tool() Pattern**: Uses OpenAI Agents SDK's elegant agent-as-tool conversion
