# AI Health Assistant

An AI-powered health assistant providing personalized medical education and information to patients and physicians, with strict guardrails ensuring responses are grounded in trusted knowledge bases.

## ⚠️ Important Disclaimer

This system provides **educational health information only** and does NOT provide medical diagnosis, treatment recommendations, or replace professional medical advice. Always consult qualified healthcare providers for medical concerns.

## Features

- 🏥 **Patient Mode**: Accessible medical information with clear educational focus
- 👨‍⚕️ **Physician Mode**: Technical, evidence-based information for healthcare professionals
- 🔒 **Strict Guardrails**: Ensures no diagnostic or treatment advice is given
- 📚 **Trusted Sources**: Information from PubMed, Mayo Clinic, CDC, WHO, and configurable sources
- 🔄 **Multi-Model Support**: Configurable AI models (Anthropic, OpenAI, Gemini)
- 📊 **Comprehensive Evaluation**: Built-in evaluation framework with metrics
- 🎯 **MAI-DxO Pattern**: Advanced orchestrated decision support (Phase 6)

## Quick Start

### Prerequisites

- Python 3.11+
- API keys for Anthropic, OpenAI, and Exa
- Access to `~/thunder_playbook/.env` for API keys

### Installation

```bash
# Clone the repository
git clone https://github.com/stewmckendry/health_assistant.git
cd health_assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Load environment variables
source ~/thunder_playbook/.env
```

### Basic Usage

```python
from src.assistants.patient import PatientAssistant

# Initialize assistant
assistant = PatientAssistant()

# Ask a health question
response = assistant.query("What are the symptoms of the common cold?")
print(response)
```

## Development

This project follows Test-Driven Development (TDD) principles. Always write tests first.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test category
pytest tests/unit/
```

### Logging

All interactions are logged to `logs/health_assistant.log` for audit and debugging:

```bash
# Monitor logs
tail -f logs/health_assistant.log
```

## Project Structure

```
health_assistant/
├── src/              # Source code
├── tests/            # Test suites
├── data/             # Test data and prompts
├── logs/             # Application logs
├── docs/             # Documentation
└── scripts/          # Utility scripts
```

## Configuration

The system is highly configurable. Edit `src/config/settings.py` or provide environment variables:

```python
# Example configuration
TRUSTED_DOMAINS=["pubmed.ncbi.nlm.nih.gov", "mayoclinic.org"]
PRIMARY_MODEL="claude-3-opus"
MAX_RESPONSE_LENGTH=1500
```

## Roadmap

- [x] Phase 1: Basic Patient Assistant
- [ ] Phase 2: Evaluation Framework
- [ ] Phase 3: Web Application
- [ ] Phase 4: Configuration System
- [ ] Phase 5: Physician Mode
- [ ] Phase 6: Medical Decision Support (MAI-DxO)

## Contributing

1. Follow TDD - write tests first
2. Use existing SDKs (ref-tools, Exa) before custom solutions
3. Implement comprehensive logging
4. Make features configurable
5. Ensure all tests pass before submitting

## License

This project is for demonstration and educational purposes only. Not for clinical use.

## Support

For issues or questions, please open an issue on GitHub.

## Acknowledgments

- Based on MAI-DxO pattern from Nori et al. (2025)
- Uses Anthropic Claude, OpenAI GPT, and other AI models
- Integrates ref-tools and Exa for knowledge retrieval