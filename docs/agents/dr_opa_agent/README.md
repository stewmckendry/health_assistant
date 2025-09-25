# Dr. OPA Agent Documentation

## Overview

**Dr. OPA** (Ontario Practice Advice) is an AI agent that provides Ontario-specific primary care and practice guidance to clinicians. It complements Dr. OFF (Ontario Finance & Formulary) by focusing on clinical practice standards, regulatory requirements, and evidence-based care pathways.

## Purpose

Dr. OPA answers critical practice questions for Ontario clinicians:

- **Regulatory Compliance**: "What are CPSO expectations for virtual care consent?"
- **Ontario Health Programs**: "What kidney care programs are available for a 65-year-old patient?"
- **Infection Control**: "What are PHO IPAC requirements for instrument reprocessing?"
- **Clinical Pathways**: "What is the CEP algorithm for managing chronic pain?"
- **Digital Health**: "How do I integrate with OLIS for lab result retrieval?"

## Key Features

### 1. Authoritative Sources
- **CPSO**: College of Physicians and Surgeons of Ontario policies and advice (366 vectors)
- **Ontario Health**: ALL clinical programs via Claude + Web Search (cancer, kidney, cardiac, mental health, etc.)
- **CEP**: Centre for Effective Practice clinical tools and algorithms (57 vectors, 6 tools)
- **PHO**: Public Health Ontario infection prevention and control guidance (132 vectors)
- **MOH**: Ministry of Health bulletins and program updates (pending)

### 2. Intelligent Retrieval
- Parent-child chunking for optimal context and precision
- Hybrid vector + keyword search with metadata filtering
- Automatic supersession tracking for updated guidelines
- Control tokens for enhanced semantic retrieval

### 3. Citation & Currency
- Every response includes source citations with URLs
- Displays effective dates and last updated dates
- Preferentially surfaces current guidance over superseded content
- Flags when guidance may be outdated

### 4. Ontario-Specific Focus
- Tailored to Ontario regulatory environment
- Aware of OHIP billing implications
- Integrated with Ontario screening programs
- Aligned with provincial digital health initiatives

## Architecture Components

### Ingestion Pipeline
- Fetches HTML/PDF documents from authoritative sources
- Extracts structured metadata (dates, topics, policy levels)
- Creates hierarchical parent-child chunks
- Generates embeddings and stores in Chroma vector database
- Tracks document supersession automatically

### MCP Tools
- `opa.search_sections`: Hybrid retrieval with metadata filters
- `opa.get_section`: Fetch full section text with citations
- `opa.policy_check`: CPSO-specific policy retrieval
- `opa.program_lookup`: Ontario Health clinical programs (ALL programs via web search)
- `opa.ipac_guidance`: PHO infection control sections
- `opa.freshness_probe`: Check for guideline updates

### AI Agent
- System prompt with Ontario practice context
- Tool routing based on query type
- Response formatting with proper citations
- Confidence scoring and fallback strategies

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-key"
```

### Ingesting Knowledge Sources

```python
from src.agents.dr_opa_agent.ingestion.opa_ingester import OPADocumentIngester

# Initialize ingester for CPSO documents
ingester = OPADocumentIngester(
    source_org="cpso",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# Ingest CPSO policies
urls = [
    "https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Policies/Continuity-of-Care",
    "https://www.cpso.on.ca/en/Physicians/Policies-Guidance/Policies/Medical-Records"
]

stats = ingester.ingest(urls)
print(f"Ingested {stats['documents_processed']} documents")
```

### Using MCP Tools

```python
from src.agents.dr_opa_agent.mcp.server import app
from mcp import ClientSession, StdioServerParameters
import asyncio

# Initialize MCP server
async def main():
    async with stdio_client() as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Search for cervical screening guidance
            result = await session.call_tool(
                "opa.search_sections",
                arguments={
                    "query": "cervical screening intervals HPV",
                    "source_org": "ontario_health",
                    "n_results": 5
                }
            )
            print(result)

asyncio.run(main())
```

### Running the Agent

```python
from src.agents.dr_opa_agent.opa_agent import OPAAgent

# Initialize agent
agent = OPAAgent()

# Ask a practice question
response = agent.query(
    "What are the CPSO documentation requirements for virtual care visits?"
)

print(response)
# Output includes cited sections, effective dates, and summary
```

## Ontario Health Clinical Programs

### Comprehensive Program Coverage

The `opa.program_lookup` tool now provides access to ALL Ontario Health clinical programs using Claude with web search technology. This covers:

- **Cancer Care**: Screening programs, treatment pathways, patient navigation
- **Kidney Care**: Chronic kidney disease management, dialysis programs
- **Cardiac Care**: Heart disease prevention, rehabilitation programs
- **Stroke Care**: Prevention, acute care pathways, rehabilitation
- **Mental Health**: Depression programs, anxiety treatment, psychotherapy access
- **Palliative Care**: End-of-life care programs and resources
- **And many more specialized programs**

### Example Query

```python
# Get kidney care information for an elderly patient
result = await session.call_tool(
    "opa.program_lookup",
    arguments={
        "program": "kidney care",
        "patient_age": 65,
        "info_needed": ["eligibility", "locations", "referral"]
    }
)

# Returns comprehensive information including:
# - Eligibility criteria for the patient's age
# - Available services and procedures
# - Referral processes and self-referral options
# - Contact information and service locations
# - Patient education resources
# - Official Ontario Health citations
```

### Key Features

- **Real-time Information**: Searches 25+ Ontario Health domains for current program details
- **Patient-Specific**: Provides age and risk-factor specific recommendations
- **Comprehensive**: Includes eligibility, procedures, locations, referral processes, and resources
- **Authoritative**: Cites official Ontario Health sources with direct links
- **Current**: Always retrieves the most up-to-date program information

## Usage Examples

### Example 1: Screening Guidelines

**Query**: "What are the cervical screening guidelines for a 30-year-old patient?"

**Response**:
```
Based on Ontario Health's Cervical Screening Program (Effective: March 3, 2025):

For patients aged 25-69:
- Primary HPV testing every 5 years (new as of March 2025)
- No longer using Pap tests as primary screening
- Self-collection option available for under-screened patients

Source: Ontario Health/CCO HPV Hub [Updated: January 2025]
```

### Example 2: Regulatory Requirements

**Query**: "Can I send lab results to patients via email?"

**Response**:
```
According to CPSO Policy - Protecting Personal Health Information (Policy #4-21):

EXPECTATION: Physicians must ensure appropriate safeguards when transmitting PHI electronically:
- Use encryption for email containing PHI
- Obtain patient consent for communication method
- Document consent in medical record
- Consider sensitivity of information

Source: CPSO Policies & Guidance [Effective: May 2021]
```

### Example 3: Infection Control

**Query**: "What are the reprocessing requirements for reusable medical devices?"

**Response**:
```
Per PHO's Best Practices for Infection Prevention in Clinical Office Practice:

Critical items (enter sterile tissue):
- Must be sterilized between uses
- Steam sterilization preferred
- Validated processes required

Semi-critical items (contact mucous membranes):
- Minimum high-level disinfection
- Follow manufacturer's instructions
- Maintain reprocessing logs

Source: Public Health Ontario IPAC Guidance [Version 2.0, 2023]
```

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...           # For embeddings
DATABASE_PATH=/path/to/opa.db   # SQLite database location
CHROMA_PATH=/path/to/chroma     # Vector store location

# Optional
LOG_LEVEL=INFO                  # Logging verbosity
CACHE_TTL=3600                  # Query cache duration (seconds)
MAX_CHUNKS=10                   # Maximum chunks per query
```

### Source Configuration

Edit `config/sources.yaml` to add/modify knowledge sources:

```yaml
sources:
  cpso:
    base_url: "https://www.cpso.on.ca"
    update_frequency: "monthly"
    document_types: ["policy", "advice"]
    
  ontario_health:
    base_url: "https://www.cancercareontario.ca"
    update_frequency: "quarterly"
    programs: ["cervical", "breast", "colorectal"]
```

## Maintenance

### Updating Knowledge Base

```bash
# Run scheduled ingestion
python -m src.agents.dr_opa_agent.ingestion.update_corpus

# Check for superseded documents
python -m src.agents.dr_opa_agent.ingestion.check_supersession

# Validate corpus integrity
python -m src.agents.dr_opa_agent.validation.validate_corpus
```

### Monitoring

- Check ingestion logs: `logs/ingestion/`
- Review query performance: `logs/queries/`
- Monitor embedding costs: `logs/openai_usage/`

## Development

### Running Tests

```bash
# Unit tests
pytest tests/dr_opa_agent/unit/

# Integration tests
pytest tests/dr_opa_agent/integration/

# End-to-end tests
pytest tests/dr_opa_agent/e2e/
```

### Adding New Sources

1. Create ingester subclass in `ingestion/sources/`
2. Add metadata extraction logic
3. Update `config/sources.yaml`
4. Run test ingestion
5. Validate retrieval quality

## Troubleshooting

### Common Issues

**Issue**: "No results found for query"
- Check if documents are ingested for the topic
- Verify Chroma collection exists
- Review query formulation

**Issue**: "Outdated guidance returned"
- Run supersession check
- Update corpus from sources
- Check effective dates in metadata

**Issue**: "PDF extraction failing"
- Ensure PyPDF2 is installed
- Check if PDF is scanned (needs OCR)
- Try alternative extraction library

## Support

For issues or questions:
- Review documentation in `docs/agents/dr_opa_agent/`
- Check logs in `logs/` directory
- Contact the development team

## License

This agent is part of the Ontario Health AI Assistant suite. See main project LICENSE file.