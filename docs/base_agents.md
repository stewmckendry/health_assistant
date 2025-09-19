# Base Agents System Architecture

## Overview

The clinical decision support system implements a multi-agent architecture inspired by Microsoft's MAI-DxO framework, using the OpenAI Agents SDK to create collaborative AI agents that assist with medical triage and assessment. The system employs an orchestrator-specialist pattern where a main orchestrator agent coordinates multiple specialist agents to provide comprehensive clinical evaluations.

## Key Source Files

### Core Agent Implementations
- `src/agents/clinical/orchestrator.py` - Main orchestrator agent and coordination logic
- `src/agents/clinical/red_flag_detector.py` - Critical symptom detection agent
- `src/agents/clinical/triage_assessor.py` - CTAS level assessment agent  
- `src/agents/clinical/workup_suggester.py` - Diagnostic test recommendation agent
- `src/agents/clinical/config_loader.py` - YAML configuration and context management

### Configuration Files
- `configs/agents/templates/triage_orchestrator.yaml` - Orchestrator configuration
- `configs/agents/templates/red_flag_detector.yaml` - Red flag agent configuration
- `configs/agents/templates/triage_assessor.yaml` - CTAS assessment configuration
- `configs/agents/templates/workup_suggester.yaml` - Workup planning configuration
- `configs/agents/templates/ctas_config.yaml` - CTAS levels and guidelines

## Core Architecture Pattern

### Agents as Tools

The system uses the **"Agents as Tools"** pattern from the OpenAI Agents SDK, where specialist agents are exposed as callable tools to the orchestrator agent.

**Implementation in `src/agents/clinical/orchestrator.py:109-123`:**
```python
# Create the specialist agents
red_flag_detector = create_red_flag_detector()
triage_assessor = create_triage_assessor(
    hospital_name=hospital_name,
    available_resources=available_resources
)
workup_suggester = create_workup_suggester(
    available_resources=available_resources
)

# Convert specialist agents to tools using as_tool()
tools = [
    red_flag_detector.as_tool(
        tool_name="detect_red_flags",
        tool_description="Detect critical red flags and time-sensitive conditions in patient presentation"
    ),
    triage_assessor.as_tool(
        tool_name="assess_triage_level",
        tool_description="Assess patient's CTAS triage level based on their presentation"
    ),
    workup_suggester.as_tool(
        tool_name="suggest_initial_workup",
        tool_description="Suggest appropriate initial diagnostic workup based on presentation and acuity"
    )
]
```

This pattern enables:
- **Modular Design**: Each specialist agent focuses on a specific clinical domain
- **Parallel Processing**: Multiple agents can be consulted simultaneously
- **Dynamic Composition**: Different agent combinations for different use cases
- **Clear Separation of Concerns**: Each agent has distinct responsibilities

## Agent Hierarchy

### 1. Orchestrator Agent
- **Role**: Main coordinator that manages the assessment workflow
- **Model**: GPT-4.1 Mini (configurable)
- **Responsibilities**:
  - Gather and organize patient information
  - Coordinate specialist assessments via tool calls
  - Synthesize findings into final triage decisions
  - Apply clinical judgment to balance conflicting assessments

### 2. Specialist Agents

#### Red Flag Detector
- **Source**: `src/agents/clinical/red_flag_detector.py`
- **Purpose**: Identify critical symptoms requiring immediate attention
- **Output**: `RedFlagAssessment` with critical level, red flags, and time-sensitive conditions
- **Key Features**:
  - Scans for life-threatening conditions
  - Identifies "cannot miss" diagnoses
  - Provides immediate action recommendations

**Output Model Definition (`red_flag_detector.py:17-28`):**
```python
class RedFlagAssessment(BaseModel):
    """Structured output for red flag detection."""
    has_red_flags: bool = Field(description="Whether any red flags are present")
    critical_level: str = Field(
        description="Severity level",
        pattern="^(CRITICAL|HIGH|MODERATE|LOW|NONE)$"
    )
    red_flags: list[str] = Field(description="List of identified red flags")
    time_sensitive_conditions: list[str] = Field(description="Conditions requiring immediate intervention")
    recommended_actions: list[str] = Field(description="Immediate actions required")
    cannot_miss_diagnoses: list[str] = Field(description="Critical diagnoses to rule out")
```

#### CTAS Triage Assessor  
- **Source**: `src/agents/clinical/triage_assessor.py`
- **Purpose**: Evaluate patient acuity using Canadian Triage and Acuity Scale
- **Output**: `CTASAssessment` with CTAS level (1-5) and confidence score
- **Context-Aware**: Considers hospital resources and current ED status
- **Decision Framework**: Maps symptoms to standardized CTAS levels

**Output Model Definition (`triage_assessor.py:18-25`):**
```python
class CTASAssessment(BaseModel):
    """Structured output for CTAS assessment."""
    ctas_level: int = Field(description="CTAS level (1-5)", ge=1, le=5)
    urgency: str = Field(description="Urgency level name (Resuscitation/Emergent/Urgent/Less Urgent/Non-Urgent)")
    confidence: float = Field(description="Confidence score (0-1)", ge=0.0, le=1.0)
    reasoning: str = Field(description="Clinical reasoning for the assessment")
    key_factors: list[str] = Field(description="Key factors influencing the CTAS level")
```

#### Initial Workup Suggester
- **Source**: `src/agents/clinical/workup_suggester.py`
- **Purpose**: Recommend appropriate diagnostic tests based on presentation
- **Output**: `WorkupPlan` with categorized test recommendations
- **Cost-Conscious**: Provides cost estimates for workup plans
- **Prioritization**: Separates immediate vs urgent vs routine tests

**Output Model Definition (`workup_suggester.py:23-40`):**
```python
class WorkupPlan(BaseModel):
    """Structured output for initial workup recommendations."""
    immediate_tests: list[TestRecommendation] = Field(
        description="Tests needed within 15 minutes"
    )
    urgent_tests: list[TestRecommendation] = Field(
        description="Tests needed within 1 hour"
    )
    routine_tests: list[TestRecommendation] = Field(
        description="Tests that can wait if patient stable"
    )
    estimated_cost: str = Field(
        description="Rough estimate of workup cost",
        pattern="^(Low \(<\$500\)|Moderate \(\$500-1500\)|High \(>\$1500\))$"
    )
    clinical_pearls: list[str] = Field(
        description="Key clinical decision points or reminders"
    )
```

## Configuration System

### YAML-Based Configuration

Each agent is configured via YAML templates that define:
- Agent name and role
- Model selection (temperature, parameters)
- System instructions (with variable substitution)
- Context defaults (hospital, resources, etc.)
- Output schema specifications

**Example from `configs/agents/templates/triage_orchestrator.yaml`:**
```yaml
# Emergency Triage Orchestrator Agent Configuration
name: "Emergency Triage Orchestrator"
model: "gpt-4o-mini"
temperature: 0.3
role: "orchestrator"

# Agent instructions with context variables
instructions: |
  You are the Emergency Department Triage Orchestrator coordinating a comprehensive patient assessment.
  
  Assessment Process (IMPORTANT: Call each tool exactly ONCE):
  1. First, call detect_red_flags ONCE to identify any critical symptoms
  2. Then, call assess_triage_level ONCE to determine CTAS level  
  3. Finally, call suggest_initial_workup ONCE to recommend initial tests
  4. Synthesize all findings into a comprehensive triage report

# Default context variables
context:
  hospital_name: "Toronto General Hospital"
  current_ed_status: "Normal operations"
  available_beds: "Standard availability"
```

### Dynamic Context Loading

The `config_loader.py` module provides configuration management utilities.

**Configuration Loader Implementation (`src/agents/clinical/config_loader.py:11-30`):**
```python
def load_agent_config(agent_name: str) -> Dict[str, Any]:
    """
    Load agent configuration from YAML file.
    
    Args:
        agent_name: Name of the agent config file (without .yaml extension)
        
    Returns:
        Dictionary with agent configuration
    """
    config_dir = Path(__file__).parent.parent.parent.parent / "configs" / "agents" / "templates"
    config_path = config_dir / f"{agent_name}.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Agent configuration not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config
```

**Context Preparation with CTAS Integration (`config_loader.py:99-136`):**
```python
def prepare_agent_context(
    config: Dict[str, Any],
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Prepare context variables for agent instructions."""
    # Start with default context from config
    context = config.get('context', {}).copy()
    
    # Load and format CTAS-specific information
    try:
        ctas_config = load_ctas_config()
        context['ctas_levels_text'] = format_ctas_levels_text(ctas_config)
        context['critical_symptoms'] = format_critical_symptoms(ctas_config)
        context['workup_guidelines'] = format_workup_guidelines(ctas_config)
    except FileNotFoundError:
        # Fallback if CTAS config is not available
        context['ctas_levels_text'] = "CTAS levels 1-5 (Resuscitation to Non-Urgent)"
        context['critical_symptoms'] = "Standard critical symptoms"
        context['workup_guidelines'] = "Standard workup guidelines"
    
    # Apply overrides if provided
    if overrides:
        context.update(overrides)
    
    return context
```

## Data Flow

### 1. Input Processing

Patient data is formatted into structured text for agent consumption.

**Data Formatting Implementation (`src/agents/clinical/orchestrator.py:260-330`):**
```python
def _format_patient_data(patient_data: Dict[str, Any]) -> str:
    """Format patient data dictionary into a readable string for the agents."""
    sections = []
    
    # Demographics
    if "age" in patient_data:
        sections.append(f"DEMOGRAPHICS: Age: {patient_data['age']}")
    
    # Chief complaint
    if "chief_complaint" in patient_data:
        sections.append(f"CHIEF COMPLAINT: {patient_data['chief_complaint']}")
    
    # Vital signs
    if "vitals" in patient_data:
        vitals = patient_data["vitals"]
        vital_list = []
        if "blood_pressure" in vitals:
            vital_list.append(f"BP: {vitals['blood_pressure']}")
        if "heart_rate" in vitals:
            vital_list.append(f"HR: {vitals['heart_rate']}")
        # ... additional vitals
        sections.append(f"VITAL SIGNS: {', '.join(vital_list)}")
    
    return "\n".join(sections)
```

### 2. Orchestrator Workflow
```
Orchestrator → Tool Call: detect_red_flags → RedFlagAssessment
           → Tool Call: assess_triage_level → CTASAssessment  
           → Tool Call: suggest_initial_workup → WorkupPlan
           → Synthesize → TriageDecision
```

### 3. Output Structure

**TriageDecision Model (`src/agents/clinical/orchestrator.py:25-36`):**
```python
class TriageDecision(BaseModel):
    """Final triage decision combining all assessments."""
    final_ctas_level: int = Field(description="Final CTAS level after considering all assessments", ge=1, le=5)
    urgency: str = Field(description="Urgency category name")
    red_flags_identified: list[str] = Field(description="All red flags found across assessments")
    initial_actions: list[str] = Field(description="Immediate actions to take")
    recommended_tests: list[str] = Field(description="Top priority tests from workup")
    estimated_wait_time: str = Field(description="Expected wait time based on CTAS level")
    disposition: str = Field(description="Where patient should be directed")
    clinical_summary: str = Field(description="Brief summary of triage decision reasoning")
    confidence: float = Field(description="Overall confidence in the assessment", ge=0.0, le=1.0)
```

## Streaming Capabilities

### Real-Time Progress Updates

The system supports streaming responses using Server-Sent Events (SSE) for real-time progress updates during triage assessment.

**Streaming Orchestrator (`src/agents/clinical/orchestrator_streaming.py`):**
```python
async def run_triage_assessment_streaming(
    patient_data: Dict[str, Any],
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    langfuse_enabled: bool = True
) -> AsyncGenerator[StreamingUpdate, None]:
    """
    Run a triage assessment with streaming progress updates.
    
    Yields StreamingUpdate objects with progress information as the assessment proceeds.
    """
```

### StreamingUpdate Model
```python
class StreamingUpdate(BaseModel):
    """A streaming update from the triage assessment."""
    type: str = Field(description="Type of update: agent_change, tool_call, tool_result, progress, final")
    agent: Optional[str] = Field(default=None, description="Current agent name")
    tool: Optional[str] = Field(default=None, description="Tool being called")
    message: Optional[str] = Field(default=None, description="Update message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional data")
    progress: Optional[float] = Field(default=None, description="Progress percentage (0-100)")
```

### Event Types
1. **agent_change**: Switching between agents
2. **tool_call**: Invoking a specialist agent
3. **tool_result**: Results from specialist with human-readable summaries
4. **progress**: General progress updates
5. **final**: Complete assessment result

### Stream Processing
**Event Handling (`orchestrator_streaming.py:138-276`):**
```python
async for event in result.stream_events():
    if event.type == "agent_updated_stream_event":
        # Agent switch event
        current_agent = event.new_agent.name
        
    elif event.type == "run_item_stream_event":
        if event.item.type == "tool_call_item":
            # Extract tool name and track progress
            tool_name = event.item.raw_item.name
            
        elif event.item.type == "tool_call_output_item":
            # Parse tool output and create human-readable summary
            parsed = json.loads(event.item.output)
            if 'has_red_flags' in parsed:
                summary = f"⚠️ Red flags detected: {', '.join(parsed.get('red_flags', []))}"
            elif 'ctas_level' in parsed:
                summary = f"CTAS Level {parsed.get('ctas_level')}: {parsed.get('urgency', '')}"
```

### Tool Call Optimization
- **Single-Call Pattern**: Each specialist agent called exactly once
- **Max Turns**: Limited to 4 (3 tool calls + 1 synthesis)
- **Progress Tracking**: Uses set() to track unique tools called

## Integration Features

### 1. Tracing & Observability

**Langfuse Integration (`src/agents/clinical/orchestrator.py:155-171`):**
```python
# Initialize Langfuse if enabled
langfuse_trace = None
if langfuse_enabled and Langfuse:
    try:
        langfuse = Langfuse()
        langfuse_trace = langfuse.trace(
            name="triage_assessment",
            id=trace_id,
            metadata={
                "session_id": session_id,
                "chief_complaint": patient_data.get("chief_complaint"),
                "age": patient_data.get("age")
            }
        )
    except Exception as e:
        print(f"Failed to initialize Langfuse: {e}")
```

### 2. Fallback Mechanisms

**Error Handling with Safe Defaults (`orchestrator.py:229-248`):**
```python
except Exception as e:
    # Log error to Langfuse if available
    if langfuse_trace:
        langfuse_trace.update(
            level="ERROR",
            status_message=str(e)
        )
    
    # Return safe default on error
    return TriageDecision(
        final_ctas_level=1,  # Highest acuity for safety
        urgency="Resuscitation",
        red_flags_identified=[f"System error: {str(e)}"],
        initial_actions=["Immediate physician assessment", "Manual triage required"],
        recommended_tests=["As per physician assessment"],
        estimated_wait_time="Immediate",
        disposition="Resuscitation area - immediate physician assessment",
        clinical_summary=f"System error during assessment - defaulting to highest acuity",
        confidence=0.0
    )
```

### 3. Extensibility Points
- **Custom Agents**: Add new specialist agents via YAML templates
- **Tool Registration**: Dynamically register agents as tools
- **Context Override**: Runtime configuration of hospital resources
- **Output Customization**: Pydantic models for structured outputs

## Safety & Compliance

### Clinical Safety Features
- **No Diagnosis**: Explicitly positions as triage support, not diagnostic tool
- **Physician Requirement**: Always includes "requires physician assessment"
- **Conservative Defaults**: Errs on side of higher acuity when uncertain
- **Audit Trail**: Complete logging of all assessments and decisions

### Data Handling
- **Session Management**: Unique session IDs for tracking
- **Structured Logging**: JSON-formatted logs for analysis
- **Privacy Compliance**: No PII stored in base implementation
- **Configurable Retention**: Adjustable log retention policies

## Performance Characteristics

### Response Times
- **Target**: < 5 seconds for complete assessment
- **Optimization**: Parallel agent consultations where possible
- **Caching**: Template and configuration caching

### Resource Utilization
- **Model Selection**: GPT-4.1 Mini for cost-efficiency
- **Token Management**: Structured outputs to minimize tokens
- **Rate Limiting**: Built-in handling for API limits

## Future Architecture Enhancements

### Planned Extensions
1. **Additional Specialist Agents**: Radiology, laboratory, pharmacy agents
2. **Multi-Modal Support**: Image and lab result interpretation
3. **Collaborative Features**: Multi-practitioner consultation modes
4. **Learning Integration**: Outcome feedback loops

### Scalability Considerations
- **Microservice Ready**: Each agent deployable as separate service
- **Queue Management**: Support for async processing
- **Load Balancing**: Multiple orchestrator instances
- **Cache Layer**: Redis for session and result caching