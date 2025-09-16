# Patient Assistant Documentation

## Overview

The `PatientAssistant` class is a specialized medical information assistant designed specifically for patient education. It extends the `BaseAssistant` with enhanced safety features, comprehensive guardrails, and patient-focused communication patterns.

## Architecture

```
PatientAssistant
      ↓
BaseAssistant (handles Anthropic API calls)
      ↓
LLMGuardrails (intelligent safety checks)
      ↓
ResponseGuardrails (regex fallback)
      ↓
Settings (configuration management)
```

## Class: `PatientAssistant`

**Location:** `src/assistants/patient.py`

Specialized assistant for patient education with enhanced safety features.

### Constructor

```python
PatientAssistant(guardrail_mode: str = "hybrid")
```

**Parameters:**
- `guardrail_mode`: Guardrail checking mode - "llm", "regex", or "hybrid" (default: "hybrid")

Automatically configures itself using patient-specific settings from configuration files.

## Enhanced System Prompt Features

The patient assistant uses a comprehensive 4.7KB system prompt with:

### Core Boundaries
- Never diagnose, prescribe, or provide treatment plans
- Cite at least one trusted source for every medical claim
- State disagreements between sources and advise clinical follow-up

### Geographic Prioritization
- Prefers Canadian/Ontario health guidance when relevant
- Falls back to US CDC/NIH, WHO, major academic centers
- Acknowledges geographic limitations for region-specific queries

### Emergency Detection (Immediate 911 Redirect)
The system immediately redirects to emergency services for:
- Chest pain or crushing pressure
- Difficulty breathing or shortness of breath  
- Stroke symptoms (FAST protocol)
- Severe abdominal pain with fever/vomiting
- Signs of anaphylaxis or sepsis
- Suicidal ideation or self-harm
- Severe bleeding or traumatic injury
- Loss of consciousness

### Out of Scope Handling
Politely declines and redirects for:
- Diagnosis requests
- Medication dosing or adjustments
- Controlled substances guidance
- Personal lab/imaging interpretation
- Prior authorization or disability letters

### Special Communication Modes

#### Chronic Conditions
When users mention established chronic conditions:
- Acknowledges user's likely familiarity: "You may already be aware of this, but from vetted sources..."
- Provides neutral educational updates
- Avoids suggesting changes to their management
- Reminds them to confirm any changes with their clinician

#### Information Currency
- Prefers guidance published within the last 5 years
- If citing older sources, explicitly states: "Note: This guidance is from [year]"
- Flags when newer information may be available

#### Pressed Beyond Scope
If user insists on out-of-scope information after initial decline:
- Requires explicit user acknowledgment
- Sets clear boundaries about limitations
- Politely ends medical discussion if user refuses acknowledgment

#### Multilingual Support
Supports 7 languages: EN, FR, ES, ZH, AR, HI, PT

## Methods

### `query(query: str, session_id: Optional[str] = None) -> Dict[str, Any]`

Process a patient query with safety checks and guardrails.

**Parameters:**
- `query`: Patient's medical question or concern
- `session_id`: Optional session identifier for logging

**Returns:**
```python
{
    "content": str,                    # Safe, educational response
    "model": str,                      # Model used
    "usage": Dict,                     # Token usage
    "citations": List[Dict],           # Source citations
    "mode": "patient",                 # Assistant mode
    "guardrails_applied": bool,        # Whether guardrails modified response
    "violations": List[str],           # Detected policy violations
    "emergency_detected": bool,        # Emergency content detected
    "mental_health_crisis": bool,      # Mental health crisis detected
    "session_id": str                  # Session identifier
}
```

## Safety Features

### 1. Pre-query checks (Input Guardrails)

**Emergency Detection**
- Analyzes query for emergency symptoms
- Severity levels: critical/high/medium/low
- Blocks query and returns immediate emergency resources

**Mental Health Crisis Detection**
- Identifies suicide ideation, self-harm thoughts
- Provides immediate crisis resources
- No API call made for safety

**Out-of-Scope Detection**
- Recognizes requests for diagnosis, treatment, medication advice
- Returns educational alternatives when appropriate
- Maintains boundaries while being helpful

### 2. Post-response Guardrails (Output Guardrails)

#### Critical Violations (block response)
- **Diagnosis suggestions**: "You have diabetes" → blocked
- **Treatment recommendations**: "Take 2 aspirin daily" → blocked
- **Medication dosing**: "Increase your dose to..." → blocked
- **Lab interpretation**: "Your results show..." → blocked
- **Emergency downplaying**: Minimizing serious symptoms → blocked

#### Moderate Violations (modify response)
- **Personalized medical advice**: Made more general
- **Missing disclaimers**: Appropriate disclaimers added
- **No citations**: Warning about unverified information
- **Untrusted sources**: Citations from non-approved domains
- **Outdated information**: Information >5 years old without noting age

#### Quality Issues (enhance response)
- **Complex medical jargon**: Simplified language suggested
- **Speculation without evidence**: Evidence-based alternatives provided
- **Missing safety guidance**: When to seek medical care added
- **Regional assumptions**: Geographic limitations acknowledged

### 3. Error Handling
- Returns safe error messages
- Includes emergency contact information
- Maintains session continuity

## Response Patterns

### Emergency Response Template
```
🚨 I can't safely evaluate those symptoms. They may be an emergency.

**Please call 911 or go to the nearest emergency department immediately.**

Do not delay seeking immediate medical attention.

**Emergency Resources:**
• Medical Emergency: Call 911 (US/Canada) or your local emergency number
• Poison Control: 1-800-222-1222 (US) | 1-844-764-7669 (Canada)
• Mental Health Crisis: 988 (US) | Talk Suicide Canada: 1-833-456-4566

This AI assistant cannot provide emergency medical assistance.
```

### Mental Health Crisis Template
```
💚 **We're Here to Help**

If you're experiencing thoughts of suicide or self-harm, please know that you're not alone 
and help is available right now.

**Immediate Support:**
• National Suicide Prevention Lifeline: 988 or 1-800-273-8255 (US)
• Talk Suicide Canada: 1-833-456-4566 or text 45645
• Crisis Text Line: Text HOME to 741741 (US) | Text TALK to 686868 (Canada)
• SAMHSA National Helpline: 1-800-662-4357
• Veterans Crisis Line: 1-800-273-8255, Press 1

**For immediate danger, call 911**

This AI assistant cannot provide crisis counseling. Please reach out to these professional 
resources who have trained counselors ready to help you.
```

### Out-of-Scope Template
```
⚠️ I can't provide that safely. This requires a licensed clinician who knows your medical history.

For general educational context about this topic, I can share that [general information if available].

Please consult with your healthcare provider for personalized guidance.
```

### Chronic Condition Response
```
📝 You may already be aware of this information given your experience with 
this condition, but from vetted medical sources:

[Educational content]

Please confirm any changes to your management plan with your healthcare provider.
```

## Usage Examples

### Basic Patient Query
```python
from src.assistants.patient import PatientAssistant

assistant = PatientAssistant()
response = assistant.query(
    "What are the common symptoms of diabetes?",
    session_id="user-123"
)

print(response["content"])
# Output includes educational information with disclaimers
```

### Emergency Detection (Input Guardrail Triggered)
```python
response = assistant.query(
    "I'm having severe chest pain and can't breathe",
    session_id="user-123"
)

print(response["emergency_detected"])  # True
print(response["content"])  # Emergency redirect message - no API call made
```

### Different Guardrail Modes
```python
# LLM-only mode (most intelligent)
assistant = PatientAssistant(guardrail_mode="llm")

# Regex-only mode (fastest, pattern-based)
assistant = PatientAssistant(guardrail_mode="regex")

# Hybrid mode (default - LLM with regex fallback)
assistant = PatientAssistant(guardrail_mode="hybrid")
```

### Response with Violations (Output Guardrail Triggered)
```python
# If the API returns diagnostic content
response = assistant.query(
    "Based on my symptoms, what condition do I have?",
    session_id="user-123"
)

# Output guardrail will modify the response
print(response["guardrails_applied"])  # True
print(response["violations"])  # ["DIAGNOSIS", "MISSING_DISCLAIMER"]
print(response["content"])  # Modified safe response with disclaimers
```

### With Citations
```python
response = assistant.query(
    "What are the latest CDC guidelines for flu prevention?",
    session_id="user-123"
)

print(response["citations"])
# [{"url": "https://cdc.gov/flu/prevent/...", "title": "Flu Prevention"}]
```

## Configuration

### System Prompt
The patient assistant loads its system prompt from `src/config/prompts.yaml`:

```yaml
patient:
  system_prompt: |
    You are a helpful medical information assistant designed to provide educational health information to patients.
    
    ## Core Purpose & Boundaries
    You provide general, educational health information ONLY. You MUST:
    1. NEVER diagnose, prescribe, adjust medications, or provide individualized treatment plans
    2. ALWAYS encourage users to consult healthcare providers for medical advice
    # ... (comprehensive 4.7KB prompt)
```

### Trusted Domains
Uses the standard list of 97 trusted medical domains from `src/config/domains.yaml`.

### Guardrail Configuration
Guardrail prompts and settings are loaded from `src/config/guardrail_prompts.yaml`.

## Logging

All operations are logged with structured JSON format:

```json
{
    "timestamp": "2024-01-01T12:00:00",
    "level": "INFO",
    "name": "src.assistants.patient",
    "message": "Patient query received",
    "session_id": "user-123",
    "query_length": 45,
    "mode": "patient",
    "guardrail_mode": "hybrid",
    "emergency_detected": false
}
```

## Testing

Comprehensive test coverage includes:

```bash
# Run patient assistant tests
pytest tests/unit/test_patient_assistant.py

# Test safety features
pytest tests/unit/test_guardrails.py

# Test emergency detection
pytest tests/integration/test_emergency_detection.py
```

### Key Test Categories
- **Safety Tests**: Guardrail effectiveness
- **Emergency Tests**: Crisis detection accuracy
- **Multi-turn Tests**: Conversation context maintenance
- **Citation Tests**: Source attribution and formatting
- **Violation Tests**: Output modification behavior

## Performance Characteristics

- **Response Time**: Typically 2-5 seconds
- **Safety Checks**: 2 layers (input + output guardrails)
- **Token Limits**: 1500 tokens per response (configurable)
- **Web Fetch**: Max 5 fetches per query (configurable)
- **Guardrail Latency**: <500ms for LLM checks

## Security Considerations

1. **Multiple Safety Layers**: Input and output guardrails
2. **Emergency Override**: Immediate crisis resource provision
3. **No Personal Advice**: Strictly educational content
4. **Source Verification**: Only trusted medical domains
5. **Content Filtering**: Multiple violation categories
6. **Session Isolation**: No cross-session data leakage

## Future Enhancements

1. **Advanced Crisis Detection**: Machine learning-based risk assessment
2. **Dynamic Disclaimers**: Context-aware safety messaging
3. **Regional Customization**: Location-specific emergency resources
4. **Accessibility Features**: Screen reader optimization
5. **Quality Metrics**: Response appropriateness scoring