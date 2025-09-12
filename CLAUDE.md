# AI Health Assistant - Claude Code Context

## Project Overview
AI-powered health assistant providing personalized medical education and information (NOT diagnosis) to patients and physicians, with strict guardrails ensuring responses are grounded in trusted knowledge bases.

## Key Principles
1. **NO MEDICAL DIAGNOSIS** - Only educational information
2. **Test-Driven Development** - Write tests first, then implementation
3. **SDK-First** - Use ref-tools and Exa SDKs before custom solutions
4. **Comprehensive Logging** - Log all decisions and interactions to files
5. **Configuration-Driven** - Everything should be configurable

## Repository Structure
```
health_assistant/
├── src/
│   ├── assistants/      # Core assistant implementations
│   │   ├── base.py       # Base assistant class
│   │   ├── patient.py    # Patient-focused assistant
│   │   ├── physician.py  # Physician-focused assistant
│   │   └── orchestrator.py # MAI-DxO orchestrator (Phase 6)
│   ├── evaluation/       # Evaluation framework
│   │   ├── evaluator.py  # LLM-as-judge implementation
│   │   └── metrics.py    # Performance metrics
│   ├── web/             # Web application (Phase 3)
│   │   └── api/         # FastAPI endpoints
│   ├── config/          # Configuration management
│   │   ├── settings.py  # Pydantic settings
│   │   └── domains.yaml # Trusted domains config
│   └── utils/           # Shared utilities
│       ├── logging.py   # Logging configuration
│       ├── guardrails.py # Response guardrails
│       └── sources.py   # Source management
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── e2e/           # End-to-end tests
├── data/
│   ├── prompts/       # Test prompts
│   └── responses/     # Response logs (gitignored)
├── logs/              # Application logs (gitignored)
├── scripts/           # Utility scripts
└── docs/             # Documentation
```

## Technology Stack

### Core Dependencies
- **Python 3.11+** - Primary language
- **Anthropic SDK** - Claude API integration
- **OpenAI SDK** - GPT models and Agents framework (Phase 6)
- **ref-tools SDK** - Documentation retrieval (MCP)
- **Exa SDK** - Web search capabilities (MCP)
- **FastAPI** - Web API framework
- **Langfuse** - Evaluation and monitoring
- **pytest** - Testing framework
- **pydantic** - Data validation and settings

### Environment Setup
```bash
# API keys location
source ~/thunder_playbook/.env

# Required environment variables:
# - ANTHROPIC_API_KEY
# - OPENAI_API_KEY
# - EXA_API_KEY
# - LANGFUSE_SECRET_KEY
# - LANGFUSE_PUBLIC_KEY
```

## Development Guidelines

### 1. Test-Driven Development
```python
# ALWAYS write test first
def test_patient_assistant_includes_disclaimer():
    assistant = PatientAssistant()
    response = assistant.query("What are symptoms of flu?")
    assert "This information is for educational purposes" in response
    assert "consult a healthcare provider" in response

# THEN implement functionality
class PatientAssistant:
    def query(self, text: str) -> str:
        # Implementation here
        pass
```

### 2. Logging Strategy
```python
import logging
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Log all key decisions
logger.info("Query received", extra={
    "session_id": session_id,
    "query": query_text,
    "mode": "patient"
})

# Log API calls
logger.info("Calling Anthropic API", extra={
    "model": "claude-3-opus",
    "tokens": token_count
})

# Log guardrail triggers
logger.warning("Guardrail triggered", extra={
    "rule": "no_diagnosis",
    "original_response": response
})
```

### 3. Configuration Management
```python
# src/config/settings.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Models
    primary_model: str = "claude-3-opus"
    fallback_model: str = "gpt-4"
    
    # Trusted sources (configurable)
    trusted_domains: list[str] = [
        "pubmed.ncbi.nlm.nih.gov",
        "mayoclinic.org",
        "cdc.gov"
    ]
    
    # Response settings
    max_response_length: int = 1500
    include_citations: bool = True
    
    class Config:
        env_file = ".env"
```

### 4. SDK Usage Examples
```python
# Using ref-tools for documentation
from ref_tools import search_documentation

results = search_documentation(
    query="hypertension treatment guidelines",
    sources=["medical"]
)

# Using Exa for web search
from exa import search_web

results = search_web(
    query="latest CDC flu guidelines",
    domains=settings.trusted_domains
)
```

### 5. Guardrails Implementation
```python
# src/utils/guardrails.py
class ResponseGuardrails:
    DISCLAIMERS = {
        "patient": "This information is for educational purposes only...",
        "physician": "This information should be used in conjunction with clinical judgment..."
    }
    
    FORBIDDEN_PHRASES = [
        "you have",
        "you should take",
        "diagnosis is",
        "treatment plan"
    ]
    
    def apply(self, response: str, mode: str) -> str:
        # Check for forbidden content
        # Add appropriate disclaimers
        # Log any modifications
        pass
```

## Testing Requirements

### Test Coverage Goals
- Unit tests: >90% coverage
- Integration tests: All SDK integrations
- E2E tests: Critical user journeys

### Test Data Location
- `data/prompts/` - Test queries
- `tests/fixtures/` - Mock responses

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## Implementation Phases

### Current Phase Focus
When working on any phase:
1. Start by writing tests
2. Use SDKs (ref-tools, Exa) before custom code
3. Log everything to files
4. Make features configurable
5. End by proving tests pass

### Phase Status Tracking
- Phase 1: Basic Patient Assistant ⏳
- Phase 2: Evaluation Framework ⏸️
- Phase 3: Web Application ⏸️
- Phase 4: Configuration System ⏸️
- Phase 5: Physician Mode ⏸️
- Phase 6: Medical Decision Support ⏸️

## Common Commands

```bash
# Run tests
pytest tests/

# Run specific assistant
python -m src.assistants.patient

# Start web server (Phase 3+)
uvicorn src.web.api.main:app --reload

# Run evaluation
python -m src.evaluation.evaluator

# Check logs
tail -f logs/health_assistant.log
```

## Important Notes

1. **API Keys**: Always load from `~/thunder_playbook/.env`
2. **No Authentication**: This is a demo - no auth required
3. **Logging**: Use file-based logging for inspection
4. **Testing**: TDD - tests come first
5. **SDKs**: Research and use ref-tools and Exa before building custom
6. **Configuration**: Make everything configurable for different organizations

## Code Review Checklist
- [ ] Tests written and passing?
- [ ] Logging implemented?
- [ ] Configuration options added?
- [ ] SDKs used where applicable?
- [ ] Guardrails applied?
- [ ] Documentation updated?