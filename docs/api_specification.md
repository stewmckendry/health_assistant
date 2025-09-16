# Health Assistant API Specification

## Overview
The Health Assistant system provides AI-powered medical education and information through a modular architecture with strict safety guardrails. The system uses Anthropic's Claude API with web_search and web_fetch capabilities to provide evidence-based medical information from trusted sources.

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

## BaseAssistant

### Class: `BaseAssistant`
**Location:** `src/assistants/base.py`

Base class for all assistant implementations, handling core Anthropic API interactions.

#### Constructor
```python
BaseAssistant(config: Optional[AssistantConfig] = None)
```

**Parameters:**
- `config`: Optional configuration object. If not provided, uses default settings.

**Configuration (AssistantConfig):**
- `model`: Claude model to use (default: "claude-3-5-sonnet-latest")
- `max_tokens`: Maximum response tokens (default: 1500)
- `temperature`: Model temperature 0.0-1.0 (default: 0.7)
- `system_prompt`: System instruction for the model
- `trusted_domains`: List of allowed domains for web_fetch (97 medical domains)
- `enable_web_fetch`: Enable/disable web fetching (default: True)
- `citations_enabled`: Include citations in responses (default: True)
- `max_web_fetch_uses`: Max web fetches per query (default: 5)

#### Methods

##### `query(query: str, session_id: Optional[str] = None, user_id: Optional[str] = None, session_logger: Optional[Any] = None, message_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]`
Send a query to the Anthropic API with support for multi-turn conversations.

**Parameters:**
- `query`: User's question or query text
- `session_id`: Optional session identifier for logging
- `user_id`: Optional user identifier for tracking
- `session_logger`: Optional SessionLogger instance for detailed logging
- `message_history`: Optional conversation history for multi-turn support (list of alternating user/assistant messages)

**Returns:**
```python
{
    "content": str,           # Response text with citations if enabled
    "model": str,             # Model used for generation
    "usage": {
        "input_tokens": int,  # Input token count
        "output_tokens": int  # Output token count
    },
    "citations": List[Dict],  # List of citations from web_fetch
    "tool_calls": List[Dict], # Tool calls made (web_search, web_fetch)
    "session_id": str,        # Session identifier
    "user_id": str            # User identifier
}
```

**Multi-Turn Conversation Support:**
The `message_history` parameter enables Claude to maintain context across multiple conversation turns:
```python
# Example message history format
message_history = [
    {"role": "user", "content": "What are flu symptoms?"},
    {"role": "assistant", "content": "Flu symptoms include fever, cough..."},
    {"role": "user", "content": "How long do they last?"}  # Claude understands "they" = flu symptoms
]
```

**Raises:**
- `ValueError`: If ANTHROPIC_API_KEY is not set
- `Exception`: If API call fails

#### Internal Methods

##### `_build_messages(query: str, message_history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]`
Constructs the message list for the API request, including conversation history for multi-turn support.

##### `_build_tools() -> Optional[List[Dict[str, Any]]]`
Configures the web_search and web_fetch tools with allowed domains.

##### `_extract_citations(response: Message) -> List[Dict[str, str]]`
Extracts citations from the API response.

##### `_format_response_with_citations(content: str, citations: List[Dict]) -> str`
Formats the response with citation links.

## PatientAssistant

### Class: `PatientAssistant`
**Location:** `src/assistants/patient.py`

Specialized assistant for patient education with enhanced safety features.

#### Constructor
```python
PatientAssistant(guardrail_mode: str = "hybrid")
```

**Parameters:**
- `guardrail_mode`: Guardrail checking mode - "llm", "regex", or "hybrid" (default: "hybrid")

Automatically configures itself using patient-specific settings from configuration files.

#### Enhanced System Prompt Features

The patient assistant uses a comprehensive 4.7KB system prompt with:

**Core Boundaries:**
- Never diagnose, prescribe, or provide treatment plans
- Cite at least one trusted source for every medical claim
- State disagreements between sources and advise clinical follow-up

**Geographic Prioritization:**
- Prefers Canadian/Ontario health guidance when relevant
- Falls back to US CDC/NIH, WHO, major academic centers
- Acknowledges geographic limitations for region-specific queries

**Emergency Detection (Immediate 911 Redirect):**
- Chest pain or crushing pressure
- Difficulty breathing or shortness of breath  
- Stroke symptoms (FAST protocol)
- Severe abdominal pain with fever/vomiting
- Signs of anaphylaxis or sepsis
- Suicidal ideation or self-harm
- Severe bleeding or traumatic injury
- Loss of consciousness

**Out of Scope Handling:**
- Diagnosis requests
- Medication dosing or adjustments
- Controlled substances guidance
- Personal lab/imaging interpretation
- Prior authorization or disability letters

**Special Modes:**
- **Chronic Conditions**: Acknowledges user's likely familiarity
- **Information Currency**: Prefers sources <5 years old
- **Pressed Beyond Scope**: Requires explicit user acknowledgment
- **Multilingual Support**: 7 languages (EN, FR, ES, ZH, AR, HI, PT)

#### Methods

##### `query(query: str, session_id: Optional[str] = None) -> Dict[str, Any]`
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

**Safety Features:**
1. **Pre-query checks (Input Guardrails):**
   - Emergency detection with severity levels (critical/high/medium/low)
   - Mental health crisis detection (suicide, self-harm)
   - Out-of-scope request detection
   - Returns appropriate resources without querying API

2. **Post-response guardrails (Output Guardrails):**
   - **Critical Violations** (block response):
     - Diagnosis suggestions
     - Treatment recommendations
     - Medication dosing
     - Lab interpretation
     - Emergency downplaying
   - **Moderate Violations** (modify response):
     - Personalized medical advice
     - Missing disclaimers
     - No citations
     - Untrusted sources
     - Outdated information (>5 years)
   - **Quality Issues** (enhance response):
     - Complex medical jargon
     - Speculation without evidence
     - Missing safety guidance
     - Regional assumptions

3. **Error handling:**
   - Returns safe error messages
   - Includes emergency contact information
   - Maintains session continuity

## LLMGuardrails

### Class: `LLMGuardrails`
**Location:** `src/utils/llm_guardrails.py`

Intelligent LLM-based guardrails that act as tripwires before and after the main LLM call.

#### Constructor
```python
LLMGuardrails(mode: str = "llm", model: str = "claude-3-5-haiku-latest")
```

**Parameters:**
- `mode`: Checking mode - "llm", "regex", or "hybrid"
- `model`: Model to use for guardrail checks (faster/cheaper model recommended)

#### Methods

##### `check_input(query: str, session_id: Optional[str] = None) -> Dict[str, Any]`
Check user input for emergencies, crises, or out-of-scope requests before main LLM call.

**Returns:**
```python
{
    "requires_intervention": bool,       # True if emergency/crisis/out-of-scope detected
    "intervention_type": str,           # "emergency", "mental_health_crisis", "out_of_scope", or "none"
    "explanation": str,                  # LLM's reasoning for decision
    "severity": str,                    # "critical", "high", "medium", or "low"
    "should_block": bool                # Whether to block the query
}
```

##### `check_output(response: str, citations: List[Dict], session_id: Optional[str], tool_calls: List[Dict]) -> Dict[str, Any]`
Check assistant output for quality and safety after main LLM call.

**Returns:**
```python
{
    "passes_guardrails": bool,          # False if any critical violations
    "violations": List[str],            # List of violations found (14 types)
    "severity": str,                    # "critical", "moderate", "minor", or "none"
    "explanation": str,                  # Explanation of issues
    "suggested_action": str,             # "block_response", "remove_content", "add_disclaimer", "enhance_citations", or "pass"
    "specific_fixes": List[str],        # Specific content to remove/modify
    "modified_response": str,            # Modified safe response
    "web_search_performed": bool,       # Whether web search was used
    "has_trusted_citations": bool       # Whether citations are from trusted domains
}
```

**Key Features:**
1. **Code-based verification**: Checks that web_search/web_fetch tools were called
2. **Trusted domain validation**: Ensures citations come from 97 whitelisted medical domains
3. **Medical content detection**: Identifies responses requiring sources
4. **LLM review**: Intelligent analysis for diagnosis, treatment advice, disclaimers
5. **Hybrid mode**: Falls back to regex patterns if LLM fails

**Violation Types (14 categories):**

**Critical Violations:**
- `DIAGNOSIS`: Response suggests specific diagnosis
- `TREATMENT`: Recommends specific treatments or medications
- `DOSING`: Provides medication dosing or adjustment advice
- `LAB_INTERPRETATION`: Interprets personal lab results or imaging
- `CONTRADICTS_EMERGENCY`: Downplays potential emergency symptoms

**Moderate Violations:**
- `MEDICAL_ADVICE`: Provides personalized advice vs general education
- `MISSING_DISCLAIMER`: Lacks appropriate medical disclaimers
- `NO_CITATIONS`: Makes medical claims without citations
- `UNTRUSTED_SOURCES`: Cites non-trusted domains
- `OUTDATED_INFO`: Uses information >5 years old without noting age

**Quality Issues:**
- `UNCLEAR_LANGUAGE`: Uses complex medical jargon without explanation
- `SPECULATION`: Makes probability statements without evidence
- `INCOMPLETE_SAFETY`: Doesn't mention when to seek medical care
- `REGIONAL_ASSUMPTION`: Assumes US/Canada context without checking

## ResponseGuardrails

### Class: `ResponseGuardrails`
**Location:** `src/utils/guardrails.py`

Regex-based safety filters and modifications to AI responses (fallback system).

#### Methods

##### `apply(response: str, session_id: Optional[str] = None) -> Dict[str, Any]`
Apply all guardrails to a response.

**Parameters:**
- `response`: Original AI response text
- `session_id`: Optional session identifier

**Returns:**
```python
{
    "original_response": str,       # Original unmodified response
    "content": str,                 # Modified safe response
    "guardrails_triggered": bool,   # Whether any guardrails activated
    "violations": List[str],        # List of policy violations detected
    "emergency_detected": bool,     # Emergency content detected
    "mental_health_crisis": bool,   # Mental health crisis detected
    "session_id": str               # Session identifier
}
```

### Utility Functions

##### `check_forbidden_phrases(response: str) -> List[str]`
Checks for diagnostic or treatment language.

##### `detect_emergency_content(text: str) -> bool`
Detects medical emergency keywords.

##### `detect_mental_health_crisis(text: str) -> bool`
Detects mental health crisis indicators.

##### `sanitize_response(response: str) -> str`
Removes or replaces forbidden phrases.

##### `apply_disclaimers(response: str) -> str`
Adds appropriate medical disclaimers.

## Configuration

### Settings Management
**Location:** `src/config/settings.py`

The system uses Pydantic settings with YAML configuration files:

- **prompts.yaml**: Comprehensive system prompts for different modes
  - Patient prompt: 4.7KB with 9 major sections
  - Includes decision flow priority and escalation handling
- **disclaimers.yaml**: Medical disclaimers and emergency resources
  - Multilingual support (7 languages)
  - Chronic condition acknowledgments
  - Out-of-scope and pressed-beyond-scope templates
  - Canadian and US emergency numbers
- **domains.yaml**: 97 trusted medical domains for web_fetch
  - Government health sites (.gov)
  - Major medical institutions
  - Academic medical centers
- **guardrail_prompts.yaml**: Enhanced LLM prompts for guardrails
  - Input guardrail with severity levels
  - Output guardrail with 14 violation types
  - Critical/moderate/minor categorization

### Environment Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...        # Required: Anthropic API key
PRIMARY_MODEL=claude-3-opus-20240229 # Primary Claude model
ASSISTANT_MODE=patient               # Mode: patient or physician
ENABLE_GUARDRAILS=true              # Enable safety guardrails
ENABLE_WEB_FETCH=true               # Enable web search
```

## API Flow Diagram

```mermaid
graph TD
    A[User Query] --> B[PatientAssistant.query]
    B --> C[LLMGuardrails.check_input]
    C --> D{Input Guardrail Check}
    D -->|Emergency| E[Return Emergency Resources]
    D -->|Crisis| F[Return Mental Health Resources]
    D -->|Safe| G[BaseAssistant.query]
    G --> H[Build Messages + Tools]
    H --> I[Anthropic API Call with web_search/web_fetch]
    I --> J[Extract Response + Citations + Tool Calls]
    J --> K[LLMGuardrails.check_output]
    K --> L{Output Guardrail Check}
    L -->|No Trusted Sources| M[Add Warning + Modify Response]
    L -->|Violations| N[Apply Suggested Action]
    L -->|Pass| O[Add Disclaimers if Needed]
    M --> P[Return Modified Response]
    N --> P
    O --> Q[Return Safe Response]
```

## Guardrail Behavior

### Input Guardrail Triggers

When the input guardrail detects an emergency or crisis:

1. **Emergency Detection** (e.g., "I'm having chest pain right now"):
   - The LLM guardrail immediately blocks the query (severity: critical)
   - No API call is made to the main assistant
   - **User receives this message:**
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

2. **Mental Health Crisis** (e.g., "I want to end my life"):
   - Query is blocked before processing (severity: critical)
   - **User receives this message:**
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

3. **Out-of-Scope Request** (e.g., "What medication dose should I take?"):
   - Query is blocked (severity: medium)
   - **User receives this message:**
     ```
     ⚠️ I can't provide that safely. This requires a licensed clinician who knows your medical history.
     
     For general educational context about this topic, I can share that medication dosing 
     is determined by healthcare providers based on individual factors including medical 
     history, other medications, and specific conditions.
     
     Please consult with your healthcare provider for personalized guidance.
     ```

### Output Guardrail Triggers

When the output guardrail detects violations:

1. **No Trusted Sources** (medical info without citations):
   - Adds warning wrapper to response
   - **User receives modified message:**
     ```
     ⚠️ **Note**: The following information needs to be verified with trusted medical sources.
     
     [Original response content about medical topic]
     
     ⚠️ **Important**: Please consult verified medical sources or healthcare providers for accurate information.
     ```

2. **Diagnosis Detected** (e.g., response contains "You have diabetes"):
   - If severe violation, **user receives:**
     ```
     I apologize, but I cannot provide that information as it may contain medical advice 
     that should only come from a healthcare provider. Please consult with a medical 
     professional for personalized guidance.
     ```
   - If mild violation, diagnostic language is replaced:
     - "you have" → "this may indicate"
     - "your symptoms" → "these symptoms"
     - User sees the modified educational content

3. **Missing Disclaimer**:
   - **User receives response with added disclaimers:**
     ```
     ⚠️ **Medical Disclaimer**: This information is for educational purposes only 
     and is not a substitute for professional medical advice, diagnosis, or treatment. 
     Always seek the advice of your physician or other qualified health provider.
     
     [Original response content]
     
     💡 **Remember**: This information is educational only. Please consult with a 
     healthcare provider for personalized medical advice. If you are experiencing 
     a medical emergency, call 911 or your local emergency number immediately.
     ```

5. **Chronic Condition Context** (e.g., "I've had diabetes for 10 years..."):
   - Response acknowledges user's experience:
     ```
     📝 You may already be aware of this information given your experience with 
     this condition, but from vetted medical sources:
     
     [Educational content about diabetes management]
     
     Please confirm any changes to your management plan with your healthcare provider.
     ```

6. **Pressed Beyond Scope** (user insists after initial decline):
   - Requires explicit acknowledgment:
     ```
     🛑 **Important Acknowledgment Required**:
     You are asking me to go beyond my safe boundaries. I can provide general 
     educational information, but you must acknowledge that:
     • This is NOT personalized medical advice
     • You MUST review this with a qualified healthcare provider  
     • This is for educational purposes only
     
     Do you acknowledge and accept these limitations?
     ```

4. **Treatment Recommendations** (e.g., "Take 2 aspirin daily"):
   - Specific advice is removed
   - **User receives generalized message:**
     ```
     ⚠️ **Medical Disclaimer**: This information is for educational purposes only 
     and is not a substitute for professional medical advice.
     
     Common treatments for this condition are typically prescribed by healthcare providers 
     based on individual patient needs. These may include various medications and therapies 
     that should be discussed with your doctor.
     
     💡 **Remember**: Please consult with a healthcare provider for personalized medical advice.
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

## Error Handling

All methods include comprehensive error handling:

1. **API Errors**: Caught and logged, safe error message returned
2. **Configuration Errors**: Validated at startup with clear messages
3. **Emergency Situations**: Immediately redirected without API call
4. **Network Issues**: Graceful degradation with user-friendly messages

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
    "mode": "patient"
}
```

Log files are stored in `logs/health_assistant.log` with automatic rotation.

## Testing

Comprehensive test coverage includes:

- **Unit Tests**: All classes and methods
- **Integration Tests**: API interactions
- **Safety Tests**: Guardrail effectiveness
- **Emergency Tests**: Crisis detection accuracy

Run tests with:
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

## Security Considerations

1. **API Key Protection**: Never log or expose API keys
2. **Input Validation**: All user input sanitized
3. **Output Filtering**: Multiple layers of safety checks
4. **Domain Restriction**: Only trusted medical sources
5. **No Diagnosis**: Strictly educational content only
6. **Session Isolation**: No cross-session data leakage

## Performance

- **Response Time**: Typically 2-5 seconds
- **Token Limits**: 1500 tokens per response (configurable)
- **Web Fetch**: Max 5 fetches per query (configurable)
- **Caching**: Not implemented (stateless design)

## Future Enhancements

1. **Physician Mode (Phase 5)**: Technical language and extended sources
2. **Multi-Agent Orchestration (Phase 6)**: MAI-DxO pattern for complex queries
3. **Evaluation Framework (Phase 2)**: Langfuse integration for quality metrics
4. **Web Application (Phase 3)**: FastAPI/Next.js interface
5. **Advanced Configuration (Phase 4)**: Runtime configuration switching
6. **Internationalization**: Expanded from current 7 languages