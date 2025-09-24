# Guardrails Documentation

## Overview

The Health Assistant system implements a comprehensive multi-layer guardrail system to ensure patient safety and appropriate medical information delivery. The system consists of two main components: **LLMGuardrails** (intelligent AI-based safety checks) and **ResponseGuardrails** (regex-based fallback patterns).

## Architecture

```
User Query
    ↓
Input Guardrails (LLMGuardrails.check_input)
    ↓
BaseAssistant.query (if safe)
    ↓
Output Guardrails (LLMGuardrails.check_output)
    ↓
Response Guardrails (regex fallback)
    ↓
Safe Response to User
```

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

### Input Guardrails

#### `check_input(query: str, session_id: Optional[str] = None) -> Dict[str, Any]`

Check user input for emergencies, crises, or out-of-scope requests before main LLM call.

**Purpose:**
- Detect medical emergencies requiring immediate intervention
- Identify mental health crises needing crisis resources
- Catch out-of-scope requests (diagnosis, medication advice)
- Prevent unnecessary API calls for clearly unsafe queries

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

#### Input Guardrail Triggers

**1. Emergency Detection (Severity: Critical)**
Queries like: "I'm having chest pain and can't breathe"

**Response:**
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

**2. Mental Health Crisis (Severity: Critical)**
Queries like: "I want to end my life"

**Response:**
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

**3. Out-of-Scope Request (Severity: Medium)**
Queries like: "What medication dose should I take?"

**Response:**
```
⚠️ I can't provide that safely. This requires a licensed clinician who knows your medical history.

For general educational context about this topic, I can share that medication dosing 
is determined by healthcare providers based on individual factors including medical 
history, other medications, and specific conditions.

Please consult with your healthcare provider for personalized guidance.
```

### Output Guardrails

#### `check_output(response: str, citations: List[Dict], session_id: Optional[str], tool_calls: List[Dict]) -> Dict[str, Any]`

Check assistant output for quality and safety after main LLM call.

**Purpose:**
- Verify medical claims are properly cited
- Ensure responses don't contain diagnosis or treatment advice
- Check that web tools were used for medical queries
- Validate citations come from trusted domains

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

## Violation Types (14 Categories)

### Critical Violations (Block Response)

#### 1. DIAGNOSIS
**Definition:** Response suggests specific diagnosis
**Example:** "You have diabetes" or "This sounds like appendicitis"
**Action:** Block response, return safe educational alternative

#### 2. TREATMENT
**Definition:** Recommends specific treatments or medications
**Example:** "Take 2 aspirin daily" or "You should get surgery"
**Action:** Block response, provide general treatment information

#### 3. DOSING
**Definition:** Provides medication dosing or adjustment advice
**Example:** "Increase your dose to 10mg" or "Take one pill every 6 hours"
**Action:** Block response, refer to healthcare provider

#### 4. LAB_INTERPRETATION
**Definition:** Interprets personal lab results or imaging
**Example:** "Your cholesterol of 250 means..." or "This X-ray shows..."
**Action:** Block response, advise clinical interpretation

#### 5. CONTRADICTS_EMERGENCY
**Definition:** Downplays potential emergency symptoms
**Example:** "Chest pain is usually nothing serious"
**Action:** Block response, include emergency guidance

### Moderate Violations (Modify Response)

#### 6. MEDICAL_ADVICE
**Definition:** Provides personalized advice vs general education
**Example:** "You should avoid gluten" → "People with celiac disease typically avoid gluten"
**Action:** Generalize advice, add disclaimers

#### 7. MISSING_DISCLAIMER
**Definition:** Lacks appropriate medical disclaimers
**Action:** Add standard medical disclaimer about educational purposes

#### 8. NO_CITATIONS
**Definition:** Makes medical claims without citations
**Action:** Add warning about unverified information

#### 9. UNTRUSTED_SOURCES
**Definition:** Cites non-trusted domains
**Action:** Remove untrusted citations, add trusted source requirement

#### 10. OUTDATED_INFO
**Definition:** Uses information >5 years old without noting age
**Action:** Add date context and currency warning

### Quality Issues (Enhance Response)

#### 11. UNCLEAR_LANGUAGE
**Definition:** Uses complex medical jargon without explanation
**Action:** Suggest simpler alternatives, define terms

#### 12. SPECULATION
**Definition:** Makes probability statements without evidence
**Example:** "You probably have..." → "Common causes include..."
**Action:** Replace speculation with evidence-based statements

#### 13. INCOMPLETE_SAFETY
**Definition:** Doesn't mention when to seek medical care
**Action:** Add appropriate "when to see a doctor" guidance

#### 14. REGIONAL_ASSUMPTION
**Definition:** Assumes US/Canada context without checking
**Action:** Acknowledge geographic limitations

## Output Guardrail Responses

### No Trusted Sources
```
⚠️ **Note**: The following information needs to be verified with trusted medical sources.

[Original response content about medical topic]

⚠️ **Important**: Please consult verified medical sources or healthcare providers for accurate information.
```

### Diagnosis Detected
```
I apologize, but I cannot provide that information as it may contain medical advice 
that should only come from a healthcare provider. Please consult with a medical 
professional for personalized guidance.
```

### Missing Disclaimer
```
⚠️ **Medical Disclaimer**: This information is for educational purposes only 
and is not a substitute for professional medical advice, diagnosis, or treatment. 
Always seek the advice of your physician or other qualified health provider.

[Original response content]

💡 **Remember**: This information is educational only. Please consult with a 
healthcare provider for personalized medical advice. If you are experiencing 
a medical emergency, call 911 or your local emergency number immediately.
```

## ResponseGuardrails (Regex Fallback)

### Class: `ResponseGuardrails`
**Location:** `src/utils/guardrails.py`

Regex-based safety filters and modifications to AI responses (fallback system).

#### `apply(response: str, session_id: Optional[str] = None) -> Dict[str, Any]`

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

#### `check_forbidden_phrases(response: str) -> List[str]`
Checks for diagnostic or treatment language using regex patterns.

**Forbidden Phrases:**
- "you have" → diagnostic language
- "you should take" → medication advice
- "diagnosis is" → explicit diagnosis
- "treatment plan" → treatment recommendations

#### `detect_emergency_content(text: str) -> bool`
Detects medical emergency keywords using pattern matching.

#### `detect_mental_health_crisis(text: str) -> bool`
Detects mental health crisis indicators using keyword patterns.

#### `sanitize_response(response: str) -> str`
Removes or replaces forbidden phrases with safe alternatives.

#### `apply_disclaimers(response: str) -> str`
Adds appropriate medical disclaimers based on content type.

## Guardrail Modes

### 1. LLM Mode ("llm")
- Uses Claude Haiku for intelligent analysis
- Most accurate violation detection
- Context-aware emergency assessment
- Slightly slower but more precise

### 2. Regex Mode ("regex")
- Pattern-based keyword matching
- Fastest response time
- Less context awareness
- Good for basic safety checks

### 3. Hybrid Mode ("hybrid") - Default
- Primary: LLM-based analysis
- Fallback: Regex patterns if LLM fails
- Best balance of accuracy and reliability
- Recommended for production use

## Configuration

### Guardrail Prompts
**Location:** `src/config/guardrail_prompts.yaml`

Contains sophisticated prompts for LLM-based guardrails:

```yaml
input_guardrail:
  system_prompt: |
    You are a medical safety system analyzing user queries before they reach a medical AI assistant...
    
output_guardrail:
  system_prompt: |
    You are a medical safety reviewer evaluating AI assistant responses...
```

### Trusted Domains
**Location:** `src/config/domains.yaml`

97 trusted medical domains used for citation validation:
- Government health sites (.gov)
- Major medical institutions
- Academic medical centers
- Professional medical organizations

## Testing

### Unit Tests
```bash
# Test guardrail functionality
pytest tests/unit/test_llm_guardrails.py
pytest tests/unit/test_guardrails.py

# Test specific violation types
pytest tests/unit/test_guardrails.py::test_diagnosis_detection
pytest tests/unit/test_guardrails.py::test_emergency_detection
```

### Integration Tests
```bash
# Test end-to-end guardrail behavior
pytest tests/integration/test_guardrails_integration.py
```

## Performance Characteristics

- **Input Guardrail Latency**: ~500ms (LLM mode)
- **Output Guardrail Latency**: ~700ms (LLM mode)
- **Regex Fallback**: <50ms
- **False Positive Rate**: <2% (LLM mode)
- **False Negative Rate**: <1% (critical violations)

## Usage Examples

### Basic Guardrail Usage
```python
from src.utils.llm_guardrails import LLMGuardrails

guardrails = LLMGuardrails(mode="hybrid")

# Check input before processing
input_result = guardrails.check_input(
    "I'm having chest pain",
    session_id="user-123"
)

if input_result["should_block"]:
    return emergency_response(input_result["intervention_type"])

# Process query with main assistant
response = assistant.query(query)

# Check output after processing
output_result = guardrails.check_output(
    response["content"],
    response["citations"],
    session_id="user-123",
    tool_calls=response["tool_calls"]
)

if not output_result["passes_guardrails"]:
    return output_result["modified_response"]
```

### Emergency Detection
```python
# This triggers input guardrail
result = guardrails.check_input("I'm having a heart attack")
print(result["intervention_type"])  # "emergency"
print(result["should_block"])       # True
```

### Violation Detection
```python
# This triggers output guardrail
result = guardrails.check_output(
    "You have diabetes and should take metformin",
    citations=[],
    session_id="test",
    tool_calls=[]
)
print(result["violations"])  # ["DIAGNOSIS", "TREATMENT", "NO_CITATIONS"]
```

## Security Considerations

1. **Defense in Depth**: Multiple guardrail layers
2. **Fail-Safe Design**: Blocks on uncertainty
3. **Emergency Priority**: Immediate crisis resource provision
4. **No Personal Data**: Doesn't store user information
5. **Audit Trail**: All decisions logged
6. **Regular Updates**: Patterns updated based on new violations

## Future Enhancements

1. **Machine Learning Models**: Custom safety classifiers
2. **Context Windows**: Multi-turn conversation safety
3. **Risk Scoring**: Probabilistic safety assessment
4. **Dynamic Thresholds**: Adaptive sensitivity based on context
5. **Real-time Monitoring**: Live safety metric dashboards