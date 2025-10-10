# Agent 97 Documentation

## Overview

**Agent 97** is an AI-powered clinical evidence search assistant that provides healthcare clinicians with evidence-based guidance from 97 carefully vetted medical sources. It combines the OpenAI Agents SDK with Claude's web search capabilities, delivering comprehensive clinical information without the domain limitations of OpenAI's WebSearchTool.

## Purpose

Agent 97 answers clinical questions for healthcare professionals:

- **Evidence-Based Clinical Guidance**: "What are the current hypertension guidelines?"
- **Latest Research**: "What's the evidence on SGLT2 inhibitors for HFpEF?"
- **Diagnostic Workup**: "Recommended diagnostic approach for suspected PE?"
- **Treatment Protocols**: "Latest guidelines for managing atrial fibrillation?"
- **Pharmacotherapy**: "Evidence for GLP-1 agonists in cardiovascular risk reduction?"

## Key Features

### 1. 97 Trusted Medical Sources
- **Medical Journals**: NEJM, Lancet, JAMA, BMJ, Nature Medicine, Circulation
- **Clinical Guidelines**: NICE, AHA, ACC, ADA, ESC, CCS, Medical Societies
- **Academic Medical Centers**: Mayo Clinic, Johns Hopkins, Cleveland Clinic, Harvard, Stanford
- **Health Authorities**: WHO, CDC, NIH, Health Canada, FDA
- **Canadian Healthcare**: Ontario Health, CPSO, Canadian Medical Associations
- **Evidence-Based Resources**: UpToDate, Cochrane, Clinical Trials, Specialty Societies

### 2. Clinician-Focused Design
- **No Patient Guardrails**: Designed for healthcare professionals who exercise clinical judgment
- **Professional Language**: Direct, evidence-based clinical terminology
- **No Domain Limits**: Claude's web_search supports all 97 domains (vs OpenAI's 20 max)
- **Configurable Search**: Adjustable web_search (default: 2) and web_fetch (default: 5) limits

### 3. Advanced Citation System
- Automatic extraction from Claude web searches
- Direct links to medical literature and guidelines
- Evidence quality notation when relevant
- Citations from trusted clinical sources only

### 4. Multi-Agent Architecture
- OpenAI Agent SDK for orchestration and conversation management
- MCP server with clinician search tool
- Claude API with web_search and web_fetch (no domain limits)
- Streaming support for real-time responses

## Architecture Components

### Agent Layer (`openai_agent.py`)
- OpenAI Agents SDK for conversation management
- Clinician-focused system instructions
- Tool routing and response formatting
- Streaming support with progress events
- Langfuse tracing integration

### MCP Server Layer (`clinician_search_server.py`)
- FastMCP server with STDIO transport
- `clinician_search` tool for evidence retrieval
- Claude API integration with web_search/web_fetch
- All 97 trusted domains (no OpenAI WebSearchTool limit)
- Session logging and error handling

### Claude Web Search Layer
- `web_search_20250305`: Search across all 97 domains (configurable max_uses: 2)
- `web_fetch_20250910`: Fetch detailed content (configurable max_uses: 5)
- Citations enabled for source tracking
- No patient safety guardrails (clinician audience)

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd health_assistant

# Install dependencies
pip install -r requirements.txt
pip install agents fastmcp anthropic pyyaml

# Set environment variables
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### Running Agent 97

```bash
# Start the MCP server (in one terminal)
python -m src.ai_agents.agent_97.mcp.clinician_search_server

# Run the agent (in another terminal)
python -m src.ai_agents.agent_97.openai_agent
```

### Using the Agent

```python
from src.ai_agents.agent_97.openai_agent import create_agent_97

# Create agent instance
agent = await create_agent_97()

# Ask a clinical question
response = await agent.query(
    "What are the current evidence-based guidelines for managing hypertension in adults?"
)

print(response['response'])
print(f"Citations: {len(response['citations'])}")
```

### Streaming Support

```python
# Stream responses with real-time progress
async for event in agent.query_stream(
    "Latest evidence on SGLT2 inhibitors for heart failure with preserved ejection fraction?",
    session_id="session_123"
):
    if event['type'] == 'progress':
        print(f"Progress: {event['message']}")
    elif event['type'] == 'text':
        print(event['content'], end='', flush=True)
    elif event['type'] == 'citation':
        print(f"\nCitation: {event['content']['url']}")
    elif event['type'] == 'complete':
        print(f"\n\nTotal citations: {len(event['citations'])}")
```

## Tools Available

### 1. `clinician_search`
Primary tool for searching 97 trusted medical sources.

**Parameters**:
- `query` (str): The clinical question to research
- `session_id` (str, optional): Session identifier
- `user_id` (str, optional): User identifier
- `max_web_search_uses` (int, default=2): Number of web searches
- `max_web_fetch_uses` (int, default=5): Number of fetches

**Returns**:
- Clinical guidance with citations from trusted sources
- Evidence quality indicators
- Direct links to medical literature

### 2. `clinician_search_get_domains`
Retrieve the list of 97 trusted medical domains.

**Parameters**:
- `include_categories` (bool, default=False): Include domain categorization

**Returns**:
- List of all 97 trusted medical domains
- Optional categorization by source type

### 3. `clinician_search_health_check`
Check the health status of the clinician search service.

**Returns**:
- Service health status
- Component availability
- Configuration verification

## Configuration

### Trusted Domains
Agent 97 uses the same 97 trusted domains from `src/config/domains.yaml` that are used by the patient assistant, but without safety guardrails.

### Search Limits
Configurable in the MCP server:
- `max_web_search_uses`: Default 2 (Claude uses web_search more than web_fetch)
- `max_web_fetch_uses`: Default 5

### Model Configuration
- Primary model: `gpt-5-mini` (reasoning-enabled)
- Temperature: 0.3 (lower for factual clinical information)
- Max tokens: 3000 (higher for detailed clinical guidance)

## Integration with Orchestrator

Agent 97 is integrated into "The Chief" orchestrator for coordinated Ontario healthcare guidance:

```python
# The orchestrator uses Agent 97 for evidence-based clinical guidance
# alongside Dr. OPA (regulations) and Dr. OFF (coverage)

from src.ai_agents.diagnostic_orchestrator.orchestrator_agent import create_diagnostic_orchestrator

orchestrator = await create_diagnostic_orchestrator()

response = await orchestrator.orchestrate(
    "What are the evidence-based treatment options for atrial fibrillation, and how are they covered in Ontario?"
)

# The orchestrator will:
# 1. Call Agent 97 for evidence-based AFib management guidelines
# 2. Call Dr. OPA for Ontario clinical pathways and quality standards
# 3. Call Dr. OFF for OHIP billing and ODB drug coverage
# 4. Synthesize into comprehensive Ontario-contextualized guidance
```

## Web API Endpoint

Agent 97 is available via the web API at `/api/agents/agent-97/stream`:

```typescript
// Frontend usage
const response = await fetch('/api/agents/agent-97/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Current guidelines for managing type 2 diabetes?',
    sessionId: 'session_123'
  })
});

const reader = response.body.getReader();
// Process streaming events...
```

## Differences from Patient Assistant

| Feature | Agent 97 (Clinicians) | Patient Assistant (Patients) |
|---------|----------------------|------------------------------|
| **Audience** | Healthcare clinicians | Patients and public |
| **Language** | Professional clinical | Plain language |
| **Safety Guardrails** | None (clinical judgment) | Input + output guardrails |
| **Disclaimers** | Professional only | Patient education disclaimers |
| **System Instructions** | Evidence-based guidance | Educational information |
| **Web Search Implementation** | Claude (no domain limit) | Claude (97 domains) |
| **MCP Tool** | `clinician_search` | `agent_97_query` |

## Limitations

- **Evidence-based guidance only**: Not for emergency medical decisions
- **Requires clinical judgment**: Information must be interpreted by healthcare professionals
- **Should verify with primary literature**: Always check source documents for critical decisions
- **Not diagnostic**: Provides clinical guidance, not patient-specific diagnoses

## Troubleshooting

### MCP Server Won't Start
```bash
# Check if ANTHROPIC_API_KEY is set
echo $ANTHROPIC_API_KEY

# Verify domains.yaml exists
ls src/config/domains.yaml

# Check logs
tail -f logs/agent_97/clinician_search_session_*.log
```

### No Citations Returned
- Verify trusted domains are configured in `domains.yaml`
- Check that web_search and web_fetch tools are enabled
- Review MCP server logs for API errors

### Slow Responses
- Reduce `max_web_fetch_uses` in clinician_search call
- Check network connectivity to medical sources
- Review Claude API rate limits

## Logging

Agent 97 maintains comprehensive logs:

```bash
# MCP server logs
logs/agent_97/clinician_search_session_YYYYMMDD_HHMMSS_XXXX.log

# OpenAI agent logs
logs/agent_97/openai_agent_session_YYYYMMDD_HHMMSS.log
```

Logs include:
- All search queries and tool calls
- Citations retrieved
- Processing times
- API errors and warnings

## Future Enhancements

- [ ] Add specialty-specific search filters
- [ ] Implement evidence grading (Level I, II, III)
- [ ] Support for clinical calculator integration
- [ ] Enhanced reasoning with chain-of-thought for complex queries
- [ ] Integration with institutional clinical guidelines

## Support

For issues or questions about Agent 97:
- Check logs in `logs/agent_97/`
- Review trusted domains in `src/config/domains.yaml`
- Test MCP health check: `clinician_search_health_check`
- See main project documentation in `docs/`
