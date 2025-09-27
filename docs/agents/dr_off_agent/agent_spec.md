# Dr. OFF Agent Specification

## Overview

Dr. OFF (Ontario Finance & Formulary) is a specialized AI assistant for Ontario healthcare clinicians, providing comprehensive guidance on drug coverage, billing codes, and assistive device funding. Built using the OpenAI Agents SDK with MCP (Model Context Protocol) integration, Dr. OFF helps healthcare providers navigate Ontario's complex healthcare financing landscape.

## Mission

To provide accurate, current guidance on Ontario healthcare coverage including OHIP billing codes, Ontario Drug Benefit (ODB) formulary, Assistive Devices Program (ADP) eligibility, and cost-effective prescribing strategies to optimize patient care while managing healthcare costs effectively.

## Architecture

### Technology Stack

- **Agent Framework**: OpenAI Agents Python SDK
- **MCP Server**: FastMCP with STDIO communication
- **Backend**: FastAPI streaming endpoints
- **Frontend**: Next.js with SSE (Server-Sent Events)
- **Database**: SQLite for OHIP/ODB/ADP data
- **Embeddings**: OpenAI text-embedding-3-small

### Components

```
dr_off_agent/
├── openai_agent.py         # OpenAI Agent wrapper with MCP integration
├── mcp/
│   ├── server.py           # FastMCP server implementation
│   ├── tools/
│   │   ├── schedule.py     # OHIP Schedule of Benefits tool
│   │   ├── odb.py          # Ontario Drug Benefit tool
│   │   └── adp.py          # Assistive Devices Program tool
│   ├── models/
│   │   ├── request.py      # Request models
│   │   └── response.py     # Response models with NLP support
│   ├── utils/
│   │   └── response_formatter.py  # Citation standardization
│   └── retrieval/
│       ├── sql_client.py   # Database queries
│       └── vector_client.py # Semantic search
└── ingestion/              # Data pipeline for updates
```

## Core Capabilities

### 1. OHIP Schedule of Benefits
- **Billing Codes**: Lookup specific service codes (e.g., A001, K005)
- **Fee Information**: Current fee schedules and payment rules
- **Requirements**: Documentation and eligibility requirements
- **Modifiers**: Premium codes and special circumstances

### 2. Ontario Drug Benefit (ODB) Formulary
- **Drug Coverage**: Check if medications are covered
- **Limited Use (LU)**: Specific criteria and LU codes
- **Generic Alternatives**: Cost-effective substitutions
- **Exceptional Access Program**: Special authorization guidance

### 3. Assistive Devices Program (ADP)
- **Device Coverage**: Wheelchairs, hearing aids, CPAP, etc.
- **Eligibility Assessment**: Income testing and requirements
- **Funding Amounts**: Coverage percentages (usually 75%)
- **Application Process**: Required documentation

### 4. Natural Language Processing
- **Flexible Queries**: Understands both clinical and billing language
- **Context Awareness**: Considers patient demographics
- **Smart Routing**: Automatically selects appropriate tools

## MCP Tools

### schedule_get
```python
def schedule_get(q: str, codes: list = None, include: list = None, top_k: int = 6)
```
- **Purpose**: Search OHIP Schedule of Benefits
- **Dual Retrieval**: Vector search + keyword matching
- **Returns**: Billing codes, fees, requirements

### odb_get
```python
def odb_get(drug: str, check_alternatives: bool = True, include_lu: bool = True, top_k: int = 5)
```
- **Purpose**: Check drug coverage and alternatives
- **Features**: Limited Use criteria, generic options
- **Returns**: Coverage status, LU codes, alternatives

### adp_get
```python
def adp_get(query: str = None, device: dict = None, patient_income: float = None, check: list = None)
```
- **Purpose**: ADP eligibility and funding
- **NLP Support**: Natural language or structured queries
- **Returns**: Coverage, eligibility, funding amounts

## Response Format

### Standardized Citations
```json
{
  "id": "cite_abc123",
  "source": "OHIP Schedule of Benefits (March 2025)",
  "title": "Schedule of Benefits for Physician Services",
  "domain": "health.gov.on.ca",
  "url": "https://www.ontario.ca/page/ohip-schedule-benefits-and-fees",
  "snippet": "Comprehensive assessment...",
  "isTrusted": true,
  "accessDate": "2025-01-27T10:30:00Z"
}
```

### Tool Response Structure
```json
{
  "type": "ohip_schedule|odb_formulary|adp_coverage",
  "query": "original query",
  "results": [...],
  "citations": [...],
  "confidence": 0.9,
  "timestamp": "ISO 8601"
}
```

## System Instructions

Dr. OFF follows these core principles:

1. **Accuracy First**: Always cite specific codes, DINs, and criteria
2. **Cost Awareness**: Suggest generic alternatives when appropriate
3. **Eligibility Focus**: Consider patient demographics and income
4. **Practical Guidance**: Provide actionable next steps
5. **Current Information**: Note when to verify with official sources
6. **Query Precision**: Distinguish between exact matches and related alternatives
   - Example: "Tylenol" (plain acetaminophen) vs "Tylenol with Codeine" (combination)
   - Clearly state when requested items are NOT covered but alternatives exist

## Integration Points

### Frontend
- **Endpoint**: `/api/agents/dr-off/stream`
- **Streaming**: Server-Sent Events (SSE) with real-time citations
- **Status**: Active in agent registry
- **UI Features**:
  - Regenerate last response
  - New chat sessions
  - Inline citations with source links
  - Tool call visualization
  - Action-oriented input placeholder

### Backend
- **FastAPI**: Registered in `main.py`
- **Session Management**: Native SDK session handling (no custom implementation needed)
- **Multi-turn Conversations**: Built-in context retention via OpenAI Agents SDK
- **Error Handling**: Graceful fallbacks with Pydantic validation

### MCP Server
- **Port**: 8002 (configurable)
- **Protocol**: STDIO communication
- **Timeout**: 30 seconds per tool call

## Usage Examples

### Example 1: OHIP Billing
```
User: "What's the billing code for a comprehensive assessment?"
Dr. OFF: "The OHIP billing code for a comprehensive assessment is A001..."
[Citations: OHIP Schedule - Code A001]
```

### Example 2: Drug Coverage
```
User: "Is Tylenol covered by ODB?"
Dr. OFF: "Plain Tylenol (acetaminophen) is NOT covered by ODB as it's an over-the-counter medication. However, Tylenol with Codeine combinations are covered with appropriate prescriptions..."
[Citations: ODB Formulary - Acetaminophen, Codeine combinations]
```

### Example 3: ADP Eligibility
```
User: "Can my patient get funding for a power wheelchair?"
Dr. OFF: "ADP provides 75% funding for power wheelchairs for eligible Ontario residents..."
[Citations: ADP Guidelines - Mobility Devices]
```

## Performance Metrics

- **Response Time**: <2 seconds for first token
- **Accuracy**: 95%+ for code lookups
- **Citation Quality**: All from official Ontario sources with PDF references
- **Tool Success Rate**: 98%+ for well-formed queries
- **Session Persistence**: Native SDK handling with automatic context retention
- **Error Recovery**: Automatic retry with Pydantic validation

## Security & Compliance

- **Data Source**: Official Ontario government databases
- **Updates**: Monthly ingestion of latest schedules
- **Privacy**: No patient data stored
- **Audit Trail**: All queries logged for quality improvement

## Limitations

1. **Ontario Only**: Coverage limited to Ontario programs
2. **Public Insurance**: Does not cover private insurance
3. **Currency**: Subject to schedule updates
4. **Complexity**: Some cases require manual verification

## Future Enhancements

### Phase 2
- **Trillium Integration**: High drug cost assistance
- **Prior Authorization**: Automated form guidance
- **Billing Optimization**: Revenue maximization strategies

### Phase 3
- **Claims Analysis**: Historical billing patterns
- **Denial Management**: Appeal assistance
- **Cost Comparison**: Cross-program optimization

## Monitoring & Maintenance

### Health Checks
- **Endpoint**: `/agents/dr-off/health`
- **MCP Status**: Tool availability verification
- **Data Freshness**: Last update timestamps

### Updates Required
- **Monthly**: OHIP schedule changes
- **Quarterly**: ODB formulary updates
- **As Needed**: ADP policy changes

## Support Resources

### Official Sources
- [OHIP Schedule of Benefits](https://www.ontario.ca/page/ohip-schedule-benefits-and-fees)
- [ODB Formulary](https://www.ontario.ca/page/check-medication-coverage/)
- [ADP Program](https://www.ontario.ca/page/assistive-devices-program)

### Contact
- **Technical Issues**: Development team
- **Content Updates**: Clinical advisory committee
- **User Feedback**: Through web app interface