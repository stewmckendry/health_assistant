# Provider Assistant Documentation

## Overview

The Provider Assistant is a specialized medical information assistant designed specifically for healthcare professionals. It extends the base assistant functionality with advanced clinical capabilities, relaxed guardrails, and access to expanded medical resources.

## Architecture

### Class Hierarchy
```
BaseAssistant
└── ProviderAssistant (src/assistants/provider.py)
```

### Key Components
- **ProviderAssistant Class**: Main implementation extending BaseAssistant
- **Provider-Specific System Prompt**: Located in `src/config/prompts.yaml`
- **Extended Trusted Domains**: Additional medical journals and clinical resources
- **Relaxed Guardrails**: Minimal safety restrictions for professional use
- **Professional Markdown Formatting**: Enhanced clinical communication standards

## Features

### 1. Clinical Information Standards
The Provider Assistant provides:
- Precise medical terminology with ICD-10/CPT codes
- Evidence levels (Level I-V) and recommendation grades (A-D)
- NNT (Number Needed to Treat) and NNH (Number Needed to Harm) data
- Clinical statistics: prevalence, incidence, sensitivity, specificity, PPV, NPV
- Contraindications, drug interactions, and black box warnings
- Current clinical practice guidelines (≤5 years unless gold standard)
- Dosing ranges with renal/hepatic adjustments

### 2. Enhanced Source Access
Extended trusted domains include:
- **Medical Journals**: NEJM, JAMA, Lancet, BMJ, Nature Medicine
- **Clinical Resources**: UpToDate, DynaMed, ClinicalKey, Epocrates
- **Pharmacological Databases**: Lexicomp, Micromedex, FDA prescribing info
- **Guidelines**: Medical societies (AHA, ADA, ACOG, AAP), NICE, USPSTF

### 3. Professional Response Formatting
Automatic markdown formatting optimized for clinical communication:
- **Bold text** for diagnoses, drug names, critical warnings
- *Italic text* for clinical signs and symptoms
- Numbered lists for treatment protocols and diagnostic steps
- Bullet points for differential diagnoses and contraindications
- Code formatting for dosages, lab values, and medical codes
- Blockquotes for critical warnings and practice alerts
- Tables for medication comparisons and diagnostic criteria

### 4. Relaxed Guardrail System
- **No Emergency Redirects**: Providers can handle clinical emergencies
- **Professional Use Disclaimers**: Subtle reminders about clinical judgment
- **Minimal Output Filtering**: Allows technical medical discussions
- **Direct Clinical Information**: No patient-style educational restrictions

## Implementation Details

### Initialization
```python
class ProviderAssistant(BaseAssistant):
    def __init__(self, guardrail_mode: str = "hybrid"):
        # Load provider-specific prompt from prompts.yaml
        # Combine standard and provider-specific trusted domains
        # Initialize with professional configuration
```

### Configuration Loading
1. **System Prompt**: Loads from `prompts.yaml["provider"]["system_prompt"]`
2. **Trusted Domains**: Merges `trusted_domains` + `provider_domains` from `domains.yaml`
3. **Deduplication**: Removes duplicate domains while preserving order
4. **Professional Settings**: Optimized for clinical use

### Query Processing
```python
@observe(name="provider_query", capture_input=True, capture_output=True)
def query(self, query: str, session_id: Optional[str] = None, 
          user_id: Optional[str] = None, message_history: Optional[list] = None):
    # 1. Langfuse observability tagging
    # 2. Skip input guardrails (providers can ask anything clinical)
    # 3. Call base assistant query method
    # 4. Apply minimal output guardrails (professional disclaimers only)
    # 5. Return professional response
```

### Streaming Support
```python
def query_stream(self, query: str, session_id: Optional[str] = None,
                user_id: Optional[str] = None, message_history: Optional[list] = None):
    # Stream responses with professional context
    # No input guardrails - providers can handle all medical content
    # Complete trace logged to Langfuse after streaming
    # Returns SSE events: start, text, tool_use, citation, complete
```

**Streaming Characteristics:**
- **No Input Guardrails**: Providers can discuss emergencies, complex cases
- **Real-time Response**: TTFT typically < 1 second
- **Professional Context**: Maintains clinical tone throughout stream
- **Complete Tracing**: Full Langfuse trace after stream completes

## Configuration Files

### 1. System Prompt (`src/config/prompts.yaml`)
```yaml
provider:
  system_prompt: |
    You are a medical information assistant for healthcare professionals...
    ## Clinical Information Standards
    ## Professional Response Formatting
    ## Source Priority for Providers
    ## Clinical Decision Support
```

### 2. Extended Domains (`src/config/domains.yaml`)
```yaml
provider_domains:
  # Medical Journals
  - cell.com
  - springer.com
  - wiley.com
  # Clinical Resources
  - dynamed.com
  - clinicalkey.com
  - epocrates.com
  # And 60+ additional domains
```

## API Integration

### Mode Selection
The web API automatically selects the Provider Assistant when `mode: "provider"` is specified:

```python
def get_assistant(mode: str = "patient"):
    if mode == "provider":
        if provider_assistant is None:
            provider_assistant = ProviderAssistant()
        return provider_assistant
```

### Request Format
```json
{
  "query": "What are current AHA guidelines for anticoagulation in AFib?",
  "sessionId": "session_123",
  "userId": "provider_456",
  "mode": "provider"
}
```

### Response Enhancements
- Professional markdown formatting
- Extended citation access
- Clinical-grade information depth
- Minimal guardrail interference

## Langfuse Observability

### Provider-Specific Tags
```python
tags = [
    "provider_assistant", 
    f"guardrail_{self.guardrail_mode}", 
    "mode:provider",
    f"session:{session_id[:8]}",
    f"user:{user_id}"
]
```

### Trace Filtering
- Filter by `mode:provider` for provider queries only
- Track clinical query patterns and response quality
- Monitor extended domain usage and citation patterns

## Testing

### Unit Tests (`tests/unit/test_provider_assistant.py`)
- Provider initialization with extended domains
- Relaxed guardrail behavior
- Professional disclaimer application
- Technical medical query handling
- Langfuse tag verification

### Integration Tests
- Mode switching between patient and provider
- Extended domain web fetching
- Clinical query processing
- Professional response formatting

## Usage Examples

### Clinical Decision Support
```python
assistant = ProviderAssistant()
response = assistant.query(
    "67-year-old with T2DM, CKD Stage 3b, recurrent hypoglycemia on metformin/glipizide. Dosing modifications?",
    session_id="clinical_001",
    user_id="provider_123"
)
```

### Evidence-Based Guidelines
```python
response = assistant.query(
    "2024 AHA/ACC anticoagulation guidelines for AFib, CHA2DS2-VASc score 4",
    mode="provider"
)
```

## Key Differences from Patient Assistant

| Feature | Patient Assistant | Provider Assistant |
|---------|------------------|-------------------|
| **Guardrails** | Strict safety checks | Minimal professional disclaimers |
| **Terminology** | Accessible language | Technical medical terminology |
| **Sources** | Basic medical sites | Extended journals + clinical resources |
| **Emergency Handling** | Immediate redirects | Professional context assumed |
| **Response Depth** | Educational overview | Clinical decision support |
| **Formatting** | Patient-friendly | Professional markdown |

## Development Notes

### Adding New Clinical Resources
1. Add domains to `domains.yaml` under `provider_domains`
2. Update documentation in `allowed_domains.md`
3. Test domain accessibility and citation quality

### Extending Clinical Capabilities
1. Modify system prompt in `prompts.yaml`
2. Update professional formatting guidelines
3. Add clinical decision support templates

### Monitoring and Quality Assurance
- Use Langfuse tags to filter provider queries
- Monitor citation quality from extended domains
- Track clinical accuracy and professional appropriateness

## Future Enhancements (Phase 6)

- **Clinical Decision Support Tools**: Integration with medical calculators
- **Drug Interaction Checking**: Real-time pharmaceutical analysis
- **Evidence Grading**: Automatic GRADE assessment of recommendations
- **Multi-Agent Orchestration**: Specialized clinical domain experts
- **Real-time Guidelines**: Dynamic updates from medical societies