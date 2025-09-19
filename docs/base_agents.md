# Base Agents System Architecture

## Overview

The clinical decision support system implements a multi-agent architecture inspired by Microsoft's MAI-DxO framework, using the OpenAI Agents SDK to create collaborative AI agents that assist with medical triage and assessment. The system employs an orchestrator-specialist pattern where a main orchestrator agent coordinates multiple specialist agents to provide comprehensive clinical evaluations.

## Core Architecture Pattern

### Agents as Tools

The system uses the **"Agents as Tools"** pattern from the OpenAI Agents SDK, where specialist agents are exposed as callable tools to the orchestrator agent:

```python
# Specialist agents converted to tools
tools = [
    red_flag_detector.as_tool(
        tool_name="detect_red_flags",
        tool_description="Detect critical red flags and time-sensitive conditions"
    ),
    triage_assessor.as_tool(
        tool_name="assess_triage_level", 
        tool_description="Assess patient's CTAS triage level"
    ),
    workup_suggester.as_tool(
        tool_name="suggest_initial_workup",
        tool_description="Suggest appropriate initial diagnostic workup"
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
- **Purpose**: Identify critical symptoms requiring immediate attention
- **Output**: `RedFlagAssessment` with critical level, red flags, and time-sensitive conditions
- **Key Features**:
  - Scans for life-threatening conditions
  - Identifies "cannot miss" diagnoses
  - Provides immediate action recommendations

#### CTAS Triage Assessor  
- **Purpose**: Evaluate patient acuity using Canadian Triage and Acuity Scale
- **Output**: `CTASAssessment` with CTAS level (1-5) and confidence score
- **Context-Aware**: Considers hospital resources and current ED status
- **Decision Framework**: Maps symptoms to standardized CTAS levels

#### Initial Workup Suggester
- **Purpose**: Recommend appropriate diagnostic tests based on presentation
- **Output**: `WorkupPlan` with categorized test recommendations
- **Cost-Conscious**: Provides cost estimates for workup plans
- **Prioritization**: Separates immediate vs urgent vs routine tests

## Configuration System

### YAML-Based Configuration

Each agent is configured via YAML templates that define:
- Agent name and role
- Model selection (temperature, parameters)
- System instructions (with variable substitution)
- Context defaults (hospital, resources, etc.)
- Output schema specifications

Example structure:
```yaml
name: "Emergency Triage Specialist"
model: "gpt-4o-mini"
temperature: 0.3
instructions: |
  You are an emergency department triage specialist.
  Hospital: {hospital_name}
  Available resources: {available_resources}
context:
  hospital_name: "Toronto General Hospital"
  available_resources: ["CT", "X-ray", "Basic labs", "ECG"]
```

### Dynamic Context Loading

The `config_loader.py` module provides:
- **Template Loading**: Reads YAML configurations from `configs/agents/templates/`
- **Context Preparation**: Merges defaults with runtime overrides
- **Dynamic Formatting**: Injects CTAS guidelines, critical symptoms, and workup protocols
- **Flexible Instantiation**: Creates agents with customized instructions

## Data Flow

### 1. Input Processing
```
Patient Data (Dict) → Format to structured text → Pass to orchestrator
```

### 2. Orchestrator Workflow
```
Orchestrator → Tool Call: detect_red_flags → RedFlagAssessment
           → Tool Call: assess_triage_level → CTASAssessment  
           → Tool Call: suggest_initial_workup → WorkupPlan
           → Synthesize → TriageDecision
```

### 3. Output Structure
The final `TriageDecision` includes:
- **final_ctas_level**: Definitive CTAS level (1-5)
- **urgency**: Category name (Resuscitation/Emergent/Urgent/Less Urgent/Non-Urgent)
- **red_flags_identified**: Consolidated critical findings
- **initial_actions**: Immediate steps to take
- **recommended_tests**: Priority diagnostic tests
- **disposition**: Where patient should be directed
- **confidence**: Overall assessment confidence (0-1)

## Integration Features

### 1. Tracing & Observability
- **Langfuse Integration**: Complete session tracing
- **Metadata Tracking**: Patient demographics, chief complaint, token usage
- **Error Handling**: Safe fallbacks to high-acuity defaults on failures

### 2. Fallback Mechanisms
- **Development Mode**: Mock agents for testing without API calls
- **Error Recovery**: Defaults to highest acuity for safety
- **Manual Override**: Always recommends physician assessment

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