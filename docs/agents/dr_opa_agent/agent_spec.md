# Dr. OPA OpenAI Agent Specification

## Overview

The Dr. OPA OpenAI Agent is an intelligent assistant specialized in Ontario practice guidance for healthcare clinicians. Built using the OpenAI Agents Python SDK, it integrates with the Dr. OPA MCP server to provide access to comprehensive practice guidance from trusted Ontario healthcare authorities.

## Agent Architecture

### Core Components

1. **OpenAI Agent**: Primary agent using `agents.Agent` from OpenAI Agents SDK
2. **MCP Integration**: Connects to Dr. OPA MCP server via `MCPServerStreamableHttp` 
3. **Tool Routing**: Intelligent routing to appropriate MCP tools based on query type
4. **Response Formatting**: Structured responses with proper citations and confidence scores

### System Instructions

The agent operates with the following core instructions:

```
You are Dr. OPA (Ontario Practice Advice), a specialized AI assistant for Ontario healthcare clinicians.

Your mission is to provide accurate, current practice guidance from trusted Ontario healthcare authorities including:
- CPSO (College of Physicians and Surgeons of Ontario) - regulatory policies and expectations
- Ontario Health - clinical programs, screening guidelines, and care pathways  
- CEP (Centre for Effective Practice) - clinical decision support tools and algorithms
- PHO (Public Health Ontario) - infection prevention and control guidance
- MOH (Ministry of Health) - policy bulletins and program updates

CORE PRINCIPLES:
1. Always cite your sources with organization, document title, effective dates, and URLs
2. Distinguish between regulatory expectations (mandatory) vs. advice (recommended)
3. Prioritize current guidance over superseded content
4. Provide Ontario-specific context and considerations
5. Use appropriate clinical terminology while remaining accessible
6. When uncertain, recommend consulting the source documents directly

RESPONSE STRUCTURE:
1. Direct answer to the clinical question
2. Relevant guidance with citations
3. Practical implementation notes
4. Related resources or cross-references
5. Currency note (when guidance was last updated)

Use your MCP tools strategically:
- opa.search_sections: General practice guidance queries
- opa.policy_check: CPSO regulatory requirements
- opa.program_lookup: Ontario Health clinical programs
- opa.ipac_guidance: Infection prevention and control
- opa.clinical_tools: CEP decision support tools
- opa.freshness_probe: Verify guidance currency
```

## MCP Server Integration

### Connection Configuration

```python
from agents.mcp.server import MCPServerStreamableHttp

# Dr. OPA MCP Server Configuration
DR_OPA_MCP_CONFIG = {
    "name": "dr-opa-server",
    "url": "http://localhost:8001",
    "description": "Ontario practice guidance and regulatory information",
    "timeout": 30,
    "retry_attempts": 3
}
```

### Available MCP Tools

| Tool | Purpose | Use Cases |
|------|---------|-----------|
| `opa.search_sections` | Hybrid search across OPA corpus | General guidance queries, topic searches |
| `opa.get_section` | Retrieve complete section by ID | Full text retrieval, context expansion |
| `opa.policy_check` | CPSO policy and regulatory advice | Compliance requirements, professional obligations |
| `opa.program_lookup` | Ontario Health clinical programs | Cancer care, kidney care, screening programs |
| `opa.ipac_guidance` | PHO infection control guidance | Sterilization, PPE, environmental cleaning |
| `opa.freshness_probe` | Check guidance currency | Verify document freshness, detect updates |
| `opa.clinical_tools` | CEP decision support tools | Clinical algorithms, calculators, checklists |

## Tool Routing Logic

The agent uses intelligent routing to determine which MCP tools to invoke based on query characteristics:

### Query Classification

```python
def classify_query(query: str) -> Dict[str, Any]:
    """Classify user query to determine appropriate tool routing."""
    classification = {
        'query_type': None,
        'suggested_tools': [],
        'sources': [],
        'confidence': 0.8
    }
    
    query_lower = query.lower()
    
    # CPSO policy queries
    if any(kw in query_lower for kw in ['cpso', 'college', 'expectation', 'must', 'shall', 'required']):
        classification['query_type'] = 'policy'
        classification['suggested_tools'] = ['opa.policy_check']
        classification['sources'] = ['cpso']
    
    # Ontario Health program queries  
    elif any(kw in query_lower for kw in ['screening', 'program', 'cancer', 'kidney', 'cardiac', 'stroke']):
        classification['query_type'] = 'program'
        classification['suggested_tools'] = ['opa.program_lookup']
        classification['sources'] = ['ontario_health']
    
    # Infection control queries
    elif any(kw in query_lower for kw in ['infection', 'control', 'steriliz', 'disinfect', 'ppe', 'hand hygiene']):
        classification['query_type'] = 'ipac'
        classification['suggested_tools'] = ['opa.ipac_guidance']
        classification['sources'] = ['pho']
    
    # Clinical tool queries
    elif any(kw in query_lower for kw in ['algorithm', 'tool', 'calculator', 'checklist', 'assessment']):
        classification['query_type'] = 'clinical_tools'
        classification['suggested_tools'] = ['opa.clinical_tools']
        classification['sources'] = ['cep']
    
    # Currency check queries
    elif any(kw in query_lower for kw in ['current', 'updated', 'latest', 'recent', 'new']):
        classification['suggested_tools'].append('opa.freshness_probe')
    
    # Default: general search
    else:
        classification['query_type'] = 'general'
        classification['suggested_tools'] = ['opa.search_sections']
    
    return classification
```

### Tool Execution Strategy

```python
async def execute_tools_parallel(agent, query_classification, user_query):
    """Execute multiple MCP tools in parallel for comprehensive coverage."""
    
    tasks = []
    
    # Primary tool based on classification
    for tool in query_classification['suggested_tools']:
        if tool == 'opa.search_sections':
            tasks.append(call_search_sections(user_query, query_classification['sources']))
        elif tool == 'opa.policy_check':
            tasks.append(call_policy_check(user_query))
        elif tool == 'opa.program_lookup':
            tasks.append(call_program_lookup(user_query))
        # ... other tools
    
    # Always include freshness check for critical guidance
    if query_classification['query_type'] in ['policy', 'program']:
        tasks.append(call_freshness_probe(user_query))
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return process_tool_results(results)
```

## Response Formatting

### Citation Standards

All responses must include proper citations following this format:

```python
def format_citation(source_org: str, title: str, section: str, effective_date: str, url: str) -> str:
    """Format citations according to Ontario healthcare standards."""
    
    org_names = {
        'cpso': 'College of Physicians and Surgeons of Ontario',
        'ontario_health': 'Ontario Health',
        'cep': 'Centre for Effective Practice', 
        'pho': 'Public Health Ontario',
        'moh': 'Ministry of Health'
    }
    
    citation = f"{org_names[source_org]}. {title}"
    
    if section:
        citation += f", {section}"
    
    if effective_date:
        citation += f" [Effective: {effective_date}]"
    
    if url:
        citation += f" Available at: {url}"
    
    return citation
```

### Response Template

```python
RESPONSE_TEMPLATE = """
## {query_topic}

{direct_answer}

### Current Guidance

{guidance_content}

**Source**: {formatted_citations}

### Implementation Notes

{practical_notes}

### Related Resources

{cross_references}

---
*Last updated: {last_updated} | Confidence: {confidence_score}/1.0*
*Always verify current requirements with source documents*
"""
```

## Error Handling & Fallbacks

### MCP Connection Issues

```python
async def handle_mcp_failure(error: Exception, query: str) -> str:
    """Handle MCP server connection or tool execution failures."""
    
    logger.error(f"MCP tool failure: {error}")
    
    fallback_response = f"""
I apologize, but I'm experiencing technical difficulties accessing the Ontario practice guidance database.

For your query: "{query[:100]}..."

Please try:
1. Consulting the relevant source documents directly:
   - CPSO: https://www.cpso.on.ca/
   - Ontario Health: https://www.ontariohealth.ca/
   - PHO: https://www.publichealthontario.ca/
   - CEP: https://cep.health/

2. Trying your query again in a few minutes

This is a temporary issue and normal service should resume shortly.
"""
    
    return fallback_response
```

### Partial Tool Failures

```python
def handle_partial_results(results: List, query: str) -> Dict:
    """Process results when some MCP tools succeed and others fail."""
    
    successful_results = [r for r in results if not isinstance(r, Exception)]
    failed_tools = [r for r in results if isinstance(r, Exception)]
    
    if not successful_results:
        return handle_mcp_failure(failed_tools[0], query)
    
    # Build response from available results with confidence adjustment
    confidence_penalty = len(failed_tools) * 0.1
    
    response = build_response_from_results(successful_results)
    response['confidence'] = max(0.3, response['confidence'] - confidence_penalty)
    response['notes'] = f"Note: Some information sources temporarily unavailable"
    
    return response
```

## Performance Specifications

### Response Time Targets

- Simple queries (single tool): < 2 seconds
- Complex queries (multiple tools): < 5 seconds  
- Program lookup (web search): < 10 seconds
- Timeout threshold: 30 seconds

### Quality Metrics

- **Citation Accuracy**: 100% of responses must include proper citations
- **Source Verification**: All guidance traced to authoritative sources
- **Currency Awareness**: Guidance age flagged when > 1 year old
- **Confidence Scoring**: All responses include confidence scores

## Security & Compliance

### Data Handling

- No PHI (Personal Health Information) processed or stored
- Query logging for performance analysis only
- MCP server communications over HTTPS in production
- API keys managed through environment variables

### Access Controls

- Agent operates with read-only access to guidance corpus
- No ability to modify or delete source documents
- Rate limiting on MCP tool calls (10/minute per session)
- Session isolation (no cross-session data sharing)

## Deployment Architecture

### Local Development

```python
# Development environment setup
DR_OPA_AGENT_CONFIG = {
    "mcp_server_url": "http://localhost:8001",
    "model": "gpt-4o-mini",
    "max_tokens": 2000,
    "temperature": 0.1,
    "timeout": 30
}
```

### Production Environment

```python
# Production environment configuration
DR_OPA_AGENT_CONFIG = {
    "mcp_server_url": "https://dr-opa-mcp.health-ai.ca",
    "model": "gpt-4o",
    "max_tokens": 3000,
    "temperature": 0.1,
    "timeout": 45,
    "retry_attempts": 3,
    "circuit_breaker_threshold": 5
}
```

## Testing Strategy

### Unit Tests

- MCP tool integration tests
- Query classification accuracy
- Response formatting validation
- Error handling scenarios

### Integration Tests

- End-to-end agent conversations
- MCP server connectivity
- Tool routing accuracy
- Citation verification

### User Acceptance Tests

- Clinical scenario walkthroughs
- Regulatory guidance accuracy
- Response time validation  
- Usability assessment

## Usage Examples

### Example 1: CPSO Policy Query

**User**: "What are CPSO expectations for virtual care consent documentation?"

**Agent Process**:
1. Classify query → policy type
2. Route to `opa.policy_check`
3. Extract CPSO expectations
4. Format with proper citations
5. Add implementation guidance

**Expected Response**: Structured response with CPSO policy requirements, mandatory vs. recommended practices, and current documentation expectations.

### Example 2: Ontario Health Program Query

**User**: "Cervical screening recommendations for a 35-year-old patient"

**Agent Process**:
1. Classify query → program type  
2. Route to `opa.program_lookup`
3. Extract screening program details
4. Apply age-specific criteria
5. Provide patient-specific recommendations

**Expected Response**: Current cervical screening guidelines, age-appropriate intervals, eligibility criteria, and referral processes.

### Example 3: Multi-tool Complex Query

**User**: "Infection control requirements for reusable medical devices in office practice"

**Agent Process**:
1. Classify query → IPAC type
2. Route to `opa.ipac_guidance` + `opa.search_sections`
3. Execute tools in parallel
4. Consolidate results
5. Cross-reference requirements

**Expected Response**: Comprehensive IPAC guidance covering sterilization requirements, PHO best practices, regulatory expectations, and practical implementation steps.

## Monitoring & Analytics

### Performance Metrics

- Query response times
- Tool success/failure rates
- User satisfaction ratings
- Citation accuracy scores

### Usage Analytics

- Query volume and patterns
- Most requested guidance topics
- Tool utilization statistics
- Error frequency and types

### Alert Conditions

- MCP server downtime
- Response time degradation
- High error rates
- Stale guidance detection

## Future Enhancements

### Planned Features

1. **Multi-language Support**: French language guidance
2. **Personalized Recommendations**: User role-based responses
3. **Proactive Updates**: Automated guidance change notifications
4. **Advanced Analytics**: Query trend analysis and insights
5. **Mobile Optimization**: Mobile-first interface design

### Integration Opportunities

1. **EMR Integration**: Direct integration with electronic medical records
2. **Clinical Decision Support**: Integration with CDSS platforms
3. **Continuing Education**: Link to relevant CME opportunities
4. **Quality Improvement**: Integration with QI tracking systems

## Appendices

### A. Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
DR_OPA_MCP_URL=http://localhost:8001

# Optional
DR_OPA_LOG_LEVEL=INFO
DR_OPA_TIMEOUT=30
DR_OPA_MAX_TOKENS=3000
DR_OPA_TEMPERATURE=0.1
```

### B. MCP Server Startup

```bash
# Start Dr. OPA MCP server
cd /path/to/health_assistant_dr_off_worktree
python -m src.agents.dr_opa_agent.mcp.server
```

### C. Agent Dependencies

```python
# requirements-agent.txt
agents>=1.0.0
asyncio
logging
json
typing
pydantic>=2.0.0
```

This specification provides a comprehensive blueprint for implementing the Dr. OPA OpenAI Agent with proper MCP integration, tool routing, and response formatting aligned with Ontario healthcare requirements.