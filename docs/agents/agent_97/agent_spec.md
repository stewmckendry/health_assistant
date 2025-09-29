# Agent 97 - OpenAI Agent Specification

## Overview

Agent 97 is an intelligent medical education assistant that provides reliable health information from 97 carefully vetted medical sources. Built using the OpenAI Agents Python SDK, it integrates with an MCP server that wraps the existing health assistant functionality, providing comprehensive medical education with robust safety guardrails.

## Agent Architecture

### Core Components

1. **OpenAI Agent**: Primary agent using `agents.Agent` from OpenAI Agents SDK
2. **MCP Integration**: Connects to Agent 97 MCP server via `MCPServerStdio`
3. **Health Assistant Backend**: Leverages existing `PatientAssistant` with Claude API
4. **Safety Guardrails**: Multi-layered input/output checking (LLM + regex)
5. **Citation Management**: Automatic extraction and deduplication from 97 trusted sources

### System Architecture

```
User Query
    ↓
OpenAI Agent (Agent 97)
    ↓
MCP Server (STDIO transport)
    ↓
PatientAssistant (Health Assistant)
    ↓
Anthropic Claude API
    ↓
Web Search & Fetch Tools
    ↓
97 Trusted Medical Domains
```

## System Instructions

The agent operates with comprehensive instructions for medical education:

```
You are Agent 97, a medical education AI assistant that provides reliable health information from 97 trusted medical sources.

Core responsibilities:
- Provide educational health information only
- Never diagnose conditions or prescribe treatments
- Apply comprehensive safety guardrails
- Cite sources from trusted medical domains
- Include appropriate medical disclaimers
- Detect and handle emergencies appropriately
```

## MCP Server Integration

### Connection Configuration

```python
# Agent 97 MCP Server Configuration
AGENT_97_MCP_CONFIG = {
    "name": "agent-97-server",
    "transport": "stdio",
    "command": ["python", "-m", "src.agents.agent_97.mcp.server"],
    "timeout": 30,
    "encoding": "utf-8"
}
```

### Available MCP Tools

| Tool | Purpose | Key Features |
|------|---------|-------------|
| `agent_97_query` | Process medical education queries | Guardrails, citations, emergency detection |
| `agent_97_query_stream` | Stream responses for real-time display | Progressive rendering support |
| `agent_97_get_trusted_domains` | List all 97 trusted medical sources | With optional categorization |
| `agent_97_health_check` | Verify system component health | API status, configuration check |
| `agent_97_get_disclaimers` | Retrieve medical disclaimers | Emergency and mental health resources |

## The 97 Trusted Medical Domains

### Categories

#### Canadian Healthcare Authorities (23 domains)
- Ontario Health, CPSO, Public Health Ontario
- Provincial health services across Canada
- Major Canadian hospitals (UHN, SickKids, Sunnybrook)

#### US Academic Medical Centers (24 domains)
- Mayo Clinic, Johns Hopkins, Cleveland Clinic
- Stanford, Harvard Medical, Columbia
- Major teaching hospitals and research centers

#### Medical Journals & Databases (9 domains)
- PubMed, NEJM, Lancet, JAMA, BMJ
- Nature, Science, Annals of Internal Medicine

#### Global Health Authorities (6 domains)
- WHO, CDC, NIH, NHS, EMA, FDA

#### Disease-Specific Organizations (15 domains)
- Heart & Stroke, Cancer societies
- Diabetes, Alzheimer's, Arthritis foundations

#### Evidence-Based Resources (4 domains)
- UpToDate, Cochrane, Clinical Trials

#### Patient Education Sites (3 domains)
- MedlinePlus, Healthline, WebMD

#### Other Trusted Sources (13 domains)
- Professional medical associations
- Clinical practice guideline repositories

## Safety Guardrails

### Input Guardrails

The system checks all incoming queries for:

1. **Emergency Content**: Chest pain, difficulty breathing, severe symptoms
2. **Mental Health Crises**: Self-harm, suicidal ideation
3. **Inappropriate Requests**: Diagnosis attempts, prescription requests

### Output Guardrails

All responses are checked for:

1. **Diagnostic Language**: "You have", "This indicates", "Diagnosis is"
2. **Prescriptive Advice**: "Take this medication", "Stop taking"
3. **Medical Procedures**: Inappropriate procedural instructions
4. **Missing Disclaimers**: Ensures educational context is clear

### Guardrail Modes

- **LLM Mode**: Uses AI to understand context and intent
- **Regex Mode**: Fast pattern matching for known phrases
- **Hybrid Mode** (Default): Combines both for optimal safety

## Response Formatting

### Standard Response Structure

```
[Educational Content with Clear Explanations]

[Relevant Information from Trusted Sources]

**Important Notes:**
- When to see a healthcare provider
- Warning signs to watch for

**Sources:**
1. [Mayo Clinic - Topic](url)
2. [CDC - Guidance](url)
3. [NIH - Information](url)

---
*This information is for educational purposes only and should not replace professional medical advice. Always consult with a qualified healthcare provider for medical concerns.*
```

### Citation Standards

- All medical information must be cited
- Citations include source name, topic, and URL
- Maximum 5 primary citations per response
- Prefer Canadian sources for Canadian users

## Tool Usage Patterns

### Query Classification

```python
def classify_medical_query(query: str) -> Dict[str, Any]:
    """Classify query to determine appropriate response strategy."""
    
    classification = {
        'query_type': None,
        'requires_citations': True,
        'emergency_check': False,
        'mental_health_check': False
    }
    
    query_lower = query.lower()
    
    # Emergency patterns
    if any(term in query_lower for term in ['chest pain', 'can\'t breathe', 'emergency']):
        classification['emergency_check'] = True
    
    # Mental health patterns
    elif any(term in query_lower for term in ['suicide', 'self harm', 'kill myself']):
        classification['mental_health_check'] = True
    
    # Information queries
    elif any(term in query_lower for term in ['what is', 'symptoms of', 'treatment for']):
        classification['query_type'] = 'educational'
    
    # Source queries
    elif 'sources' in query_lower or 'domains' in query_lower:
        classification['query_type'] = 'sources'
    
    return classification
```

## Error Handling

### MCP Connection Issues

```python
async def handle_mcp_failure(error: Exception, query: str) -> str:
    """Handle MCP server connection failures."""
    
    return f"""I apologize, but I'm experiencing technical difficulties.

For your query: "{query[:100]}..."

Please consult trusted medical sources directly:
- Mayo Clinic: https://www.mayoclinic.org/
- CDC: https://www.cdc.gov/
- Your healthcare provider

If this is a medical emergency, call 911 immediately."""
```

### Partial Failures

When some components work but others fail:
- Provide best available response
- Note limitations clearly
- Suggest alternative resources
- Log errors for debugging

## Performance Specifications

### Response Time Targets

- Simple queries: < 3 seconds
- Complex queries with citations: < 5 seconds
- Emergency detection: < 1 second
- Timeout threshold: 30 seconds

### Quality Metrics

- **Citation Rate**: 100% for factual medical information
- **Guardrail Activation**: ~5% of queries (appropriate level)
- **Emergency Detection**: 100% accuracy required
- **Source Diversity**: Use 3+ sources when available

## Security & Privacy

### Data Handling

- No personal health information (PHI) stored
- Query logging for quality improvement only
- Session IDs are anonymized
- No user tracking across sessions

### API Security

- API keys managed through environment variables
- HTTPS for all external API calls
- Rate limiting on queries
- No credential exposure in logs

## Deployment Configuration

### Development Environment

```python
AGENT_97_DEV_CONFIG = {
    "mcp_server_command": ["python", "-m", "src.agents.agent_97.mcp.server"],
    "model": "gpt-4o-mini",
    "max_tokens": 2000,
    "temperature": 0.3,
    "timeout": 30
}
```

### Production Environment

```python
AGENT_97_PROD_CONFIG = {
    "mcp_server_command": ["python", "-m", "src.agents.agent_97.mcp.server"],
    "model": "gpt-4o",
    "max_tokens": 3000,
    "temperature": 0.3,
    "timeout": 45,
    "retry_attempts": 3
}
```

## Testing Strategy

### Unit Tests
- MCP tool functionality
- Guardrail activation
- Citation extraction
- Error handling

### Integration Tests
- End-to-end query processing
- Multi-tool coordination
- Response formatting
- Emergency handling

### Acceptance Tests
- Medical scenario coverage
- Source diversity validation
- Response quality assessment
- Safety verification

## Usage Examples

### Example 1: General Health Education

**User**: "What are the symptoms of type 2 diabetes?"

**Agent Process**:
1. Routes to `agent_97_query` tool
2. Processes through health assistant
3. Retrieves information from trusted sources
4. Applies educational formatting
5. Includes citations and disclaimers

**Expected Response**: Comprehensive education about diabetes symptoms, risk factors, and when to seek medical care, with citations from Mayo Clinic, CDC, and Diabetes Canada.

### Example 2: Emergency Detection

**User**: "I'm having severe chest pain and shortness of breath"

**Agent Process**:
1. Input guardrails detect emergency
2. Bypasses normal processing
3. Returns emergency response immediately

**Expected Response**: Immediate instruction to call 911, with clear emergency guidance.

### Example 3: Medication Information

**User**: "What are the side effects of metformin?"

**Agent Process**:
1. Routes to `agent_97_query` tool
2. Retrieves drug information
3. Includes general side effects
4. Emphasizes consulting prescriber

**Expected Response**: Educational information about metformin's common side effects, with emphasis on discussing with healthcare provider.

### Example 4: Source Inquiry

**User**: "What medical websites do you use for information?"

**Agent Process**:
1. Routes to `agent_97_get_trusted_domains` tool
2. Returns categorized list of 97 domains
3. Explains vetting criteria

**Expected Response**: Complete list of trusted sources with explanation of selection criteria.

## Monitoring & Analytics

### Key Metrics

- Query volume and patterns
- Tool usage statistics
- Guardrail activation rates
- Citation source distribution
- Error rates and types
- Response times

### Alert Conditions

- MCP server downtime
- High error rate (>5%)
- Slow response times (>10s average)
- Failed emergency detection
- API key issues

## Future Enhancements

### Planned Features

1. **Multilingual Support**: French language for Canadian users
2. **Personalization**: User preference learning
3. **Visual Content**: Medical diagrams and infographics
4. **Voice Interface**: Speech-to-text integration
5. **Mobile Optimization**: Dedicated mobile experience

### Integration Opportunities

1. **Electronic Health Records**: Read-only EHR integration
2. **Telemedicine Platforms**: Pre-consultation education
3. **Health Apps**: API for third-party apps
4. **Wearables**: Contextual health education

## Implementation Status

### ✅ Completed Components
- MCP server wrapper for health assistant
- OpenAI Agent with system instructions
- Five MCP tools implemented
- Comprehensive logging system
- Error handling and fallbacks

### 🚧 In Progress
- Testing suite development
- Performance optimization
- Documentation completion

### 📋 Planned
- Production deployment configuration
- Monitoring dashboard
- API documentation
- User feedback system

## Compliance & Regulations

### Medical Information Standards
- No diagnosis or treatment recommendations
- Clear educational disclaimers
- Professional referral guidance
- Emergency response protocols

### Data Privacy
- No PHI collection or storage
- PIPEDA compliance (Canada)
- HIPAA considerations (US users)
- Transparent data usage

## Support & Maintenance

### Troubleshooting Guide

**Issue**: "Agent not responding to queries"
- Check MCP server status with health_check
- Verify API keys are configured
- Review session logs for errors

**Issue**: "Citations not appearing"
- Verify web tools are enabled
- Check trusted domains configuration
- Review Anthropic API response

**Issue**: "Guardrails blocking legitimate queries"
- Review guardrail mode (try "regex" vs "hybrid")
- Check for false positive patterns
- Adjust sensitivity settings

## Appendices

### A. Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
AGENT_97_LOG_LEVEL=INFO
AGENT_97_TIMEOUT=30
AGENT_97_MAX_TOKENS=2000
```

### B. MCP Server Startup

```bash
# Start Agent 97 MCP server
cd /path/to/project
python -m src.agents.agent_97.mcp.server
```

### C. Dependencies

```python
# requirements.txt additions
agents>=1.0.0
fastmcp>=0.1.0
anthropic>=0.20.0
pyyaml>=6.0
python-dotenv>=1.0.0
```

This specification provides a comprehensive blueprint for Agent 97, combining the robustness of the health assistant with the flexibility of the OpenAI Agents framework.