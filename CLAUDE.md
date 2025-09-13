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
│   │   ├── physician.py  # Physician-focused assistant (Phase 5)
│   │   └── orchestrator.py # MAI-DxO orchestrator (Phase 6)
│   ├── evaluation/       # Evaluation framework (Phase 2)
│   │   ├── evaluator.py  # LLM-as-judge implementation
│   │   └── metrics.py    # Performance metrics
│   ├── web/             # Web application (Phase 3)
│   │   └── api/         # FastAPI endpoints
│   ├── config/          # Configuration management
│   │   ├── settings.py  # Pydantic settings
│   │   ├── prompts.yaml # System prompts
│   │   ├── disclaimers.yaml # Medical disclaimers
│   │   ├── domains.yaml # 97 trusted domains
│   │   └── guardrail_prompts.yaml # LLM guardrail prompts
│   └── utils/           # Shared utilities
│       ├── logging.py   # Logging configuration
│       ├── session_logging.py # Session tracking
│       ├── guardrails.py # Regex-based guardrails
│       └── llm_guardrails.py # LLM-based guardrails
├── tests/
│   ├── unit/           # Unit tests (54 tests)
│   ├── integration/    # Integration tests (11 tests)
│   └── e2e/           # End-to-end tests (7 tests)
├── logs/
│   └── sessions/      # Session logs (.jsonl + .json)
├── scripts/           # Utility scripts
│   ├── test_assistant.py # CLI interface
│   └── view_session_log.py # Log viewer
└── docs/             # Documentation
    ├── api_specification.md
    ├── session_logging.md
    └── project_plan.md
```

## Technology Stack

### Core Dependencies (Phase 1 Complete)
- **Python 3.11+** - Primary language
- **Anthropic SDK v0.67.0+** - Claude API integration with web tools
- **pytest** - Testing framework (72 tests)
- **pydantic** - Data validation and settings
- **pyyaml** - Configuration file management
- **python-json-logger** - Structured JSON logging
- **python-dotenv** - Environment variable management

### Future Phases
- **OpenAI SDK** - GPT models and Agents framework (Phase 6)
- **FastAPI** - Web API framework (Phase 3)
- **Langfuse** - Evaluation and monitoring (Phase 2)

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

# Run CLI assistant
python scripts/test_assistant.py

# View session logs
python scripts/view_session_log.py --latest

# Start web server (Phase 3+)
uvicorn src.web.api.main:app --reload

# Run evaluation (Phase 2+)
python -m src.evaluation.evaluator
```

## Important Notes

1. **API Keys**: Always load from `~/thunder_playbook/.env`
2. **No Authentication**: This is a demo - no auth required
3. **Logging**: Use file-based logging for inspection
4. **Testing**: TDD - tests come first
5. **SDKs**: Research and use ref-tools and Exa before building custom
6. **Configuration**: Make everything configurable for different organizations

## Troubleshooting Common Issues

### 1. API Key Not Loading
```bash
# Add to script or use dotenv
from dotenv import load_dotenv
load_dotenv()
```

### 2. Model Not Found
```bash
# Use latest Anthropic models (as of September 2025)
PRIMARY_MODEL=claude-3-5-sonnet-latest
```

### 3. Web Fetch Not Working
- Ensure both web_search and web_fetch tools are enabled
- Check anthropic-beta headers are set correctly
- Verify trusted domains in domains.yaml

### 4. Session Logs Not Opening
- .jsonl files: Right-click → Open With → TextEdit
- .json files: Double-click to open in browser
- Or use: `python scripts/view_session_log.py <session_id>`

### 5. Emergency False Positives
- Use hybrid guardrail mode for context-aware checking
- LLM guardrails understand educational vs actual emergencies

## Code Review Checklist
- [ ] Tests written and passing?
- [ ] Session logging implemented?
- [ ] Configuration options added?
- [ ] Guardrails applied (input + output)?
- [ ] Citations deduplicated?
- [ ] Documentation updated?