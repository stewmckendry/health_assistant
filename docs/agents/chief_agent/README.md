# The Chief - Clinical Intelligence Orchestrator

## Overview

The Chief is an intelligent orchestration agent that coordinates between three specialized Ontario healthcare agents to provide comprehensive clinical decision support. Acting as a clinical intelligence router, The Chief analyzes queries and seamlessly delegates to the most appropriate specialist agents while synthesizing their responses into unified, actionable guidance.

## Clinical Purpose

The Chief serves as a single point of contact for complex healthcare queries that may span:
- **Clinical Practice Guidelines** (via Dr. OPA)
- **Healthcare Financing & Coverage** (via Dr. OFF) 
- **Medical Education & Evidence** (via Agent 97)

By intelligently routing queries and synthesizing responses, The Chief eliminates the need for users to determine which specialist agent to consult, providing comprehensive answers that consider regulatory, financial, and clinical evidence dimensions.

## Architecture

### Agent Orchestration Model

```
User Query → The Chief → Analysis & Routing → Specialist Agents → Synthesis → Response
                ↓                                    ↓
         [Query Analysis]                    [Dr. OPA | Dr. OFF | Agent 97]
                ↓                                    ↓
         [Intent Classification]              [Domain-Specific Processing]
                ↓                                    ↓
         [Multi-Agent Routing]               [Evidence & Citations]
                ↓                                    ↓
         [Response Synthesis]                [Unified Response]
```

### Specialist Agents

1. **Dr. OPA (Ontario Practice Advice)**
   - CPSO policies and guidelines
   - Clinical pathways and protocols
   - Ontario Health programs
   - Public health guidance

2. **Dr. OFF (Ontario Finance & Formulary)**
   - OHIP billing codes and coverage
   - ODB formulary and drug coverage
   - ADP device funding eligibility
   - Healthcare financing rules

3. **Agent 97 (Medical Education)**
   - Evidence-based medical content
   - Clinical guidelines from 97 trusted sources
   - Medical education resources
   - Peer-reviewed literature

## Technical Implementation

### Core Components

```python
# src/agents/diagnostic_orchestrator/orchestrator_agent.py
class DiagnosticOrchestrator:
    - Query analysis and intent detection
    - Multi-agent consultation management
    - Response synthesis and deduplication
    - Citation aggregation
    - Langfuse tracing integration
```

### Key Features

1. **Intelligent Query Routing**
   - Natural language understanding for intent detection
   - Multi-domain query support
   - Parallel agent consultation when appropriate

2. **Response Synthesis**
   - Deduplication of overlapping information
   - Citation aggregation and standardization
   - Confidence scoring based on evidence quality

3. **Streaming Response**
   - Real-time SSE (Server-Sent Events) streaming
   - Progressive response rendering
   - Tool call visualization in UI

4. **Observability**
   - Langfuse tracing for all interactions
   - Detailed tool call tracking
   - Performance metrics and latency monitoring

### API Endpoints

```
POST /agents/orchestrator/stream
- Streaming response with real-time updates
- SSE format with citation and tool call events

POST /agents/orchestrator/query  
- Non-streaming synchronous response
- Complete JSON response with citations

GET /agents/orchestrator/status
- Health check and capability information
- Available agents and their status
```

### Configuration

```python
# Environment Variables
OPENAI_API_KEY          # Required for GPT-4o model
LANGFUSE_PUBLIC_KEY     # Observability tracing
LANGFUSE_SECRET_KEY     # Observability authentication
LANGFUSE_HOST          # Tracing endpoint

# Model Configuration
PRIMARY_MODEL = "gpt-4o"
TEMPERATURE = 0.2        # Low temperature for consistency
MAX_TOKENS = 4000       # Response length limit
```

## Usage Examples

### Complex Multi-Domain Query
**Query**: "What are the OHIP billing codes for diabetes management and is continuous glucose monitoring covered by ADP?"

**The Chief's Process**:
1. Identifies billing code request → Routes to Dr. OFF
2. Identifies ADP coverage question → Routes to Dr. OFF  
3. May consult Dr. OPA for clinical guidelines
4. Synthesizes comprehensive response with citations

### Clinical Practice with Financial Context
**Query**: "Can I prescribe medical cannabis and how is it covered?"

**The Chief's Process**:
1. Regulatory question → Routes to Dr. OPA (CPSO policies)
2. Coverage question → Routes to Dr. OFF (ODB formulary)
3. Clinical evidence → Routes to Agent 97 (medical literature)
4. Provides unified guidance with regulatory, financial, and clinical context

## Response Format

Responses include:
- **Synthesized Answer**: Unified narrative combining all agent inputs
- **Citations**: Aggregated and deduplicated source references
- **Tool Calls**: Which specialist agents were consulted
- **Confidence Score**: Based on evidence quality and consistency
- **Trace ID**: For feedback and debugging

```json
{
  "response": "Comprehensive synthesized answer...",
  "agents_consulted": ["Dr. OPA", "Dr. OFF"],
  "citations": [
    {
      "title": "OHIP Schedule of Benefits",
      "url": "https://health.gov.on.ca/...",
      "source": "Dr. OFF"
    }
  ],
  "confidence": 0.92,
  "trace_id": "abc-123-def"
}
```

## Development

### Running The Chief

```bash
# Start the orchestrator (included in main API)
python -m src.web.api.main

# The Chief is available at:
# http://localhost:8000/agents/orchestrator/
```

### Testing

```python
# Test orchestrator functionality
python test_chief_orchestrator.py

# Test with specific scenarios
python -c "from src.ai_agents.diagnostic_orchestrator.orchestrator_agent import create_diagnostic_orchestrator; ..."
```

### Monitoring

- Langfuse Dashboard: View traces and performance metrics
- Session logs: `data/orchestrator_conversations.db`
- API logs: Standard FastAPI logging

## Best Practices

1. **Query Formulation**
   - Include relevant clinical context
   - Specify Ontario-specific requirements
   - Mention both clinical and administrative needs

2. **Response Interpretation**
   - Review all citations for authoritative sources
   - Consider confidence scores for decision-making
   - Verify currency of guidelines and policies

3. **Performance Optimization**
   - Cache frequently accessed data
   - Use streaming for real-time feedback
   - Monitor trace data for bottlenecks

## Future Enhancements

- [ ] Adaptive learning from usage patterns
- [ ] Specialized routing for emergency scenarios
- [ ] Integration with additional specialist agents
- [ ] Advanced conflict resolution between agent responses
- [ ] Temporal awareness for guideline updates

## Support

For issues or questions:
- Technical issues: Check Langfuse traces for debugging
- Clinical accuracy: Review agent-specific citations
- Performance concerns: Monitor streaming latency metrics