# Health Assistant - Phase 1: Basic Patient Assistant

AI-powered medical education assistant providing safe, educational health information (NOT diagnosis) with strict guardrails using Anthropic's Claude API.

## ⚠️ Medical Disclaimer

**This assistant provides educational information only. It does NOT provide medical diagnosis, treatment recommendations, or replace professional medical advice. Always consult with qualified healthcare providers for medical concerns.**

## 🎯 Project Status

**Phase 1: Basic Patient Assistant ✅ COMPLETE**
- 54 unit tests passing
- 11 integration tests passing  
- 7 end-to-end tests implemented
- Full documentation available

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/stewmckendry/health_assistant.git
cd health_assistant_phase1

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." > .env
```

### Running the Assistant

```bash
# Interactive CLI mode
python scripts/test_assistant.py

# Single query
python scripts/test_assistant.py -q "What are the symptoms of diabetes?"

# Batch queries from file
python scripts/test_assistant.py -b scripts/example_queries.txt

# With verbose output
python scripts/test_assistant.py -v

# Save conversation history
python scripts/test_assistant.py -s
```

## 🏗️ Architecture

```
PatientAssistant
      ↓
BaseAssistant (Anthropic API calls)
      ↓
ResponseGuardrails (safety filters)
      ↓
Settings (configuration management)
```

### Key Components

1. **BaseAssistant**: Core Anthropic API integration with web_fetch tool
2. **PatientAssistant**: Patient-specific safety checks and disclaimers
3. **ResponseGuardrails**: Multi-layer safety filtering system
4. **Configuration**: YAML-based settings management

## 🔒 Safety Features

### Pre-Query Checks
- **Emergency Detection**: Chest pain, breathing issues, stroke symptoms → 911 redirect
- **Mental Health Crisis**: Suicidal ideation, self-harm → 988 resources
- **No API Call**: Critical situations bypass API entirely

### Post-Response Guardrails
- **Forbidden Phrases**: Removes diagnostic/treatment language
- **Disclaimers**: Adds medical disclaimers automatically
- **Citation Support**: Includes sources from trusted domains

### Trusted Domains
- mayoclinic.org
- cdc.gov
- pubmed.ncbi.nlm.nih.gov
- who.int
- nih.gov
- medlineplus.gov

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional (defaults shown)
PRIMARY_MODEL=claude-3-opus-20240229
ASSISTANT_MODE=patient
ENABLE_GUARDRAILS=true
ENABLE_WEB_FETCH=true
MAX_TOKENS=1500
TEMPERATURE=0.7
```

### Configuration Files

- `src/config/prompts.yaml` - System prompts for different modes
- `src/config/disclaimers.yaml` - Medical disclaimers and emergency resources
- `src/config/domains.yaml` - Trusted medical domains for web_fetch

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/unit/           # Unit tests (54 tests)
pytest tests/integration/    # Integration tests (11 tests)
pytest tests/e2e/            # End-to-end tests (7 scenarios)

# Run with coverage
pytest --cov=src --cov-report=html

# Use the test runner script
./scripts/run_tests.sh
```

### Test Coverage
- **Unit Tests**: Core functionality, guardrails, configuration
- **Integration Tests**: Anthropic API interaction mocking
- **E2E Tests**: 5 critical scenarios including emergency detection

## 📚 API Documentation

Complete API documentation available in [`docs/api_specification.md`](docs/api_specification.md)

### Example Usage

```python
from src.assistants.patient import PatientAssistant

# Initialize assistant
assistant = PatientAssistant()

# Make a query
response = assistant.query(
    "What are the common symptoms of diabetes?",
    session_id="user-123"
)

# Response includes:
# - content: Educational information with disclaimers
# - citations: Sources from trusted domains
# - guardrails_applied: Whether safety filters were triggered
# - emergency_detected: Emergency content detection
# - mental_health_crisis: Crisis detection
```

## 📊 Logging

All operations are logged to `logs/health_assistant.log` with JSON format:

```json
{
    "timestamp": "2024-01-01T12:00:00",
    "level": "INFO",
    "name": "src.assistants.patient",
    "message": "Patient query received",
    "session_id": "user-123",
    "query_length": 45,
    "mode": "patient"
}
```

Logs automatically rotate at 10MB with 5 backup files kept.

## 🚨 Emergency Handling

The system immediately detects and redirects:

**Medical Emergencies**:
- Chest pain, heart attack symptoms
- Breathing difficulties
- Stroke symptoms
- Severe bleeding
- Loss of consciousness

**Mental Health Crises**:
- Suicidal ideation
- Self-harm intentions
- Harm to others

These queries bypass the API and return appropriate emergency resources.

## 🔧 Development

### Project Structure
```
health_assistant_phase1/
├── src/
│   ├── assistants/      # Core assistant implementations
│   ├── config/          # Configuration and settings
│   └── utils/           # Guardrails and logging
├── tests/               # Comprehensive test suite
├── scripts/             # CLI and utility scripts
├── docs/                # Documentation
└── logs/                # Application logs (gitignored)
```

### Contributing

1. Follow TDD - write tests first
2. Use comprehensive logging
3. Apply guardrails to all responses
4. Document API changes
5. Maintain 100% critical path test coverage

## 📈 Performance

- **Response Time**: 2-5 seconds typical
- **Token Limits**: 1500 tokens per response (configurable)
- **Web Fetch**: Max 5 fetches per query (configurable)
- **Rate Limiting**: Handled gracefully with user-friendly errors

## 🔮 Future Phases

- **Phase 2**: Evaluation Framework (Langfuse integration)
- **Phase 3**: Web Application (FastAPI)
- **Phase 4**: Advanced Configuration System
- **Phase 5**: Physician Mode
- **Phase 6**: Multi-Agent Orchestration (MAI-DxO)

## 📝 License

This is a demonstration project for educational purposes. Not intended for production medical use.

## 🤝 Support

For issues or questions:
- Review [API Documentation](docs/api_specification.md)
- Check [Project Plan](docs/project_plan.md)
- Open an issue on GitHub

## ⚖️ Legal Notice

This software is provided "as is" without warranty of any kind. It is not a medical device, does not provide medical advice, and should not be used for medical decision-making. Always consult qualified healthcare professionals for medical concerns.

---

**Remember**: This assistant is for educational purposes only. For medical emergencies, call 911. For mental health crises, call 988.