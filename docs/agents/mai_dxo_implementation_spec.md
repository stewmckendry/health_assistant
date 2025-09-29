# MAI-DxO-Inspired Clinical Decision Support Framework Implementation Specification

## Vision

Build a simplified version of Microsoft's MAI-DxO (MAI Diagnostic Orchestrator) framework using OpenAI Agents SDK to create a multi-agent clinical decision support system that can:
- Orchestrate multiple specialized medical agents to collaboratively solve complex diagnostic challenges
- Balance diagnostic accuracy with cost-efficiency of tests and procedures
- Support multiple Canadian healthcare use cases while maintaining adaptability for different clinical scenarios
- Integrate seamlessly with the existing health assistant platform

## Architecture Overview

### Core Concepts from MAI-DxO

Based on the Microsoft research paper, MAI-DxO achieves superior diagnostic performance through:

1. **Virtual Panel of Physicians**: Simulating multiple specialized clinical personas working collaboratively
2. **Sequential Diagnosis**: Iterative refinement of hypotheses through strategic information gathering
3. **Cost-Aware Decision Making**: Balancing diagnostic yield against resource utilization
4. **Structured Reasoning**: Explicit hypothesis tracking and systematic test selection

### OpenAI Agents SDK Integration

The OpenAI Agents SDK provides the perfect framework for implementing MAI-DxO-like functionality:

1. **Agents as Tools Pattern**: Main orchestrator agent calls specialist agents as tools
2. **Handoffs**: Seamless transfer of control between agents for specialized tasks
3. **Sessions**: Built-in conversation history management
4. **Tracing**: Comprehensive observability for debugging and optimization

## User Stories & Canadian Healthcare Use Cases

### 1. Emergency Department Triage Assistant
**User Story**: As an ED triage nurse in a busy Toronto hospital, I need help prioritizing patients and determining initial diagnostic workup to optimize patient flow and resource allocation.

**Implementation**: 
- Triage Orchestrator agent manages workflow
- Risk Stratification agent evaluates patient acuity
- Initial Workup agent suggests appropriate tests
- Integration with CTAS (Canadian Triage and Acuity Scale)

### 2. Primary Care Diagnostic Support
**User Story**: As a family physician in rural Ontario, I need assistance with complex differential diagnoses when specialist consultations are limited.

**Implementation**:
- Primary Care Orchestrator coordinates assessment
- Differential Diagnosis agent generates hypotheses
- Test Selection agent optimizes investigations based on local availability
- Referral Advisor suggests appropriate specialist consultations

### 3. Multi-Disciplinary Cancer Team Support
**User Story**: As part of a cancer care team at Princess Margaret Hospital, we need help coordinating complex diagnostic workups and treatment planning across specialties.

**Implementation**:
- Cancer Care Orchestrator manages multi-specialty workflow
- Pathology agent interprets diagnostic results
- Imaging agent analyzes radiological findings
- Treatment Planning agent synthesizes recommendations

### 4. Mental Health Assessment Framework
**User Story**: As a mental health practitioner in a CAMH clinic, I need support for comprehensive psychiatric assessments and treatment planning.

**Implementation**:
- Mental Health Orchestrator coordinates assessment
- Symptom Analysis agent evaluates presenting concerns
- Risk Assessment agent identifies safety considerations
- Treatment Recommendation agent suggests evidence-based interventions

### 5. Long COVID Assessment Protocol
**User Story**: As a physician in a post-COVID clinic, I need help managing complex multi-system evaluations for long COVID patients.

**Implementation**:
- Long COVID Orchestrator manages comprehensive assessment
- System Review agents (Respiratory, Cardiac, Neurological)
- Test Prioritization agent optimizes diagnostic approach
- Symptom Tracking agent monitors progression

## Technical Design

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Application Layer                     │
│         (FastAPI - Extended with new Agent pages)            │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
┌──────────────────────────┐  ┌────────────────────────────┐
│  Existing Assistant API   │  │  NEW: Agent Support API    │
│  (Anthropic-based)       │  │  (OpenAI Agents SDK)       │
└──────────────────────────┘  └────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  Agent Orchestration Layer                    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Main Orchestrator Agent                    │   │
│  │    (Calls specialist agents as tools via SDK)       │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│              ┌───────────┴───────────┐                      │
│              ▼ Agents as Tools       ▼                      │
│  ┌─────────────────────────────────────────────────┐       │
│  │         Specialist Agent Panel                   │       │
│  │  (Dynamically configured per use case)          │       │
│  │  • Triage Agent    • Differential Agent         │       │
│  │  • Test Agent      • Risk Assessment Agent      │       │
│  │  • Cost Agent      • Specialist Referral Agent  │       │
│  └─────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Shared Infrastructure                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Langfuse │  │ Session  │  │   YAML   │  │  Guard-  │   │
│  │ Tracing  │  │ Storage  │  │  Configs │  │  rails   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Agent Pattern: Agents as Tools vs Handoffs

Given the collaborative panel approach from MAI-DxO, we'll use the **Agents as Tools** pattern:

```python
from agents import Agent, Runner, function_tool
import asyncio

# Template for specialist agents as tools
@function_tool
async def consult_specialist(
    specialty: str,
    patient_context: str,
    specific_question: str
) -> str:
    """Consult a specialist agent for expert opinion"""
    specialist = get_specialist_agent(specialty)
    result = await Runner.run(
        specialist,
        input=f"Context: {patient_context}\nQuestion: {specific_question}"
    )
    return result.final_output

class OrchestratorAgent(Agent):
    """Main orchestrator that uses specialists as tools"""
    
    def __init__(self, use_case_config: dict):
        # Load use-case specific configuration
        specialists = self._load_specialists(use_case_config)
        
        super().__init__(
            name=use_case_config['orchestrator']['name'],
            model=use_case_config['orchestrator']['model'],
            instructions=use_case_config['orchestrator']['instructions'],
            tools=[
                consult_specialist,
                request_test,
                calculate_cost,
                check_guidelines
            ]
        )
```

### Agent Template System

```python
# src/agents/clinical/templates.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from agents import Agent

@dataclass
class AgentTemplate:
    """Flexible template for creating specialized agents"""
    name: str
    role: str
    model: str = "gpt-4.1-mini"
    instructions_template: str = ""
    tools: List[Any] = None
    context_variables: Dict[str, Any] = None
    
    def create_agent(self, **kwargs) -> Agent:
        """Create an agent instance from template"""
        # Merge template context with runtime context
        context = {**(self.context_variables or {}), **kwargs}
        
        # Format instructions with context
        instructions = self.instructions_template.format(**context)
        
        return Agent(
            name=self.name,
            model=self.model,
            instructions=instructions,
            tools=self.tools or []
        )

# Example: Load from YAML
def load_agent_template(yaml_path: str) -> AgentTemplate:
    """Load agent template from YAML configuration"""
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    return AgentTemplate(**config)
```

### YAML Configuration Structure

```yaml
# configs/agents/templates/triage_agent.yaml
name: "Emergency Triage Specialist"
role: "triage"
model: "gpt-4.1-mini"
instructions_template: |
  You are an emergency department triage specialist.
  
  Your responsibilities:
  - Assess patient acuity using CTAS scale (1-5)
  - Identify red flags requiring immediate attention
  - Recommend initial diagnostic workup
  
  Context:
  - Hospital: {hospital_name}
  - Available resources: {available_resources}
  - Current ED wait time: {wait_time}
  
  Always prioritize patient safety.

context_variables:
  hospital_name: "Toronto General Hospital"
  available_resources: ["CT", "X-ray", "Basic labs", "ECG"]
  wait_time: "2 hours"

tools:
  - "ctas_calculator"
  - "red_flag_checker"
  - "initial_workup_suggester"
```

### Integration Points

#### 1. Separate from Existing Assistant Classes
```python
# src/agents/clinical/base.py
from agents import Agent, Runner
from langfuse import Langfuse

class ClinicalAgent:
    """Base class for clinical agents - separate from BaseAssistant"""
    
    def __init__(self, template_path: str):
        self.template = load_agent_template(template_path)
        self.agent = self.template.create_agent()
        self.langfuse = Langfuse()  # Shared tracing
        
    async def consult(self, context: dict) -> dict:
        """Run agent consultation with tracing"""
        with self.langfuse.trace(name=f"agent_{self.template.role}"):
            result = await Runner.run(self.agent, input=context)
            return self._format_response(result)
```

#### 2. Web Application Extension
```python
# src/web/api/clinical_agents.py
from fastapi import APIRouter
from src.agents.clinical import get_orchestrator

router = APIRouter(prefix="/api/agents")

@router.post("/diagnose")
async def run_diagnosis(
    use_case: str,
    patient_data: dict
):
    """New endpoint for agent-based diagnosis"""
    orchestrator = get_orchestrator(use_case)
    result = await orchestrator.diagnose(patient_data)
    return result

# Add to existing main.py
app.include_router(clinical_agents.router)
```

## Project Repository Structure

```
health_assistant/
├── src/
│   ├── agents/              # NEW: Agent implementations
│   │   ├── clinical/        # Clinical decision support agents
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py    # Main MAI-DxO orchestrator
│   │   │   ├── hypothesis.py      # Hypothesis tracking agent
│   │   │   ├── test_chooser.py    # Test selection agent
│   │   │   ├── challenger.py      # Devil's advocate agent
│   │   │   └── stewardship.py     # Cost optimization agent
│   │   ├── tools/           # Agent tools
│   │   │   ├── __init__.py
│   │   │   ├── test_database.py   # Canadian test database
│   │   │   ├── cost_calculator.py # OHIP cost calculations
│   │   │   └── clinical_kb.py     # Clinical knowledge base
│   │   └── base.py          # Base agent classes
│   ├── workflows/           # NEW: Use case workflows
│   │   ├── __init__.py
│   │   ├── emergency_triage.py
│   │   ├── primary_care.py
│   │   ├── cancer_team.py
│   │   ├── mental_health.py
│   │   └── long_covid.py
│   ├── evaluation/          # EXTEND: Agent evaluation
│   │   └── agent_evaluator.py
│   └── web/                 # EXTEND: New endpoints
│       └── api/
│           └── clinical_support.py
├── tests/
│   └── agents/              # NEW: Agent tests
│       ├── test_orchestrator.py
│       └── test_agents.py
├── configs/                 # NEW: Agent configurations
│   ├── agents/
│   │   ├── default.yaml
│   │   └── use_cases/
│   │       ├── emergency.yaml
│   │       └── primary_care.yaml
│   └── prompts/
│       └── agents/          # Agent-specific prompts
└── data/                    # NEW: Clinical data
    ├── test_database.json   # Canadian test catalog
    └── case_studies/        # Validation cases
```

## Dependencies

### Core Dependencies
```toml
# pyproject.toml or requirements.txt
[dependencies]
# OpenAI SDK and Agents
openai = "^1.0.0"              # OpenAI API client
agents-sdk = "^0.1.0"           # OpenAI Agents SDK (when available)

# Existing infrastructure
anthropic = "^0.67.0"           # For comparison/fallback
langfuse = "^2.0.0"             # Shared tracing infrastructure
fastapi = "^0.100.0"            # Web framework
pydantic = "^2.0.0"             # Data validation
pyyaml = "^6.0.0"               # YAML configurations

# Canadian healthcare integrations
fhir-parser = "^0.1.0"          # FHIR standard support
hl7apy = "^1.3.4"               # HL7 message parsing

# Testing and evaluation
pytest = "^7.0.0"               # Testing framework
pytest-asyncio = "^0.21.0"      # Async test support
httpx = "^0.24.0"               # API testing

# Monitoring and observability
prometheus-client = "^0.17.0"   # Metrics collection
structlog = "^23.0.0"           # Structured logging
```

### Environment Variables
```bash
# Required API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...

# Optional configurations
OPENAI_ORG_ID=org-...
DEFAULT_MODEL=gpt-4-turbo-preview
MAX_AGENT_ITERATIONS=10
COST_LIMIT_PER_SESSION=50.00
```

## Implementation Phases

### Phase 1: Emergency Triage Assistant (Week 1-2)
**Deliverable**: Working ED triage assistant with CTAS scoring

- [ ] Set up OpenAI Agents SDK environment and dependencies
- [ ] Create base `ClinicalAgent` class (separate from BaseAssistant)
- [ ] Implement Emergency Triage Orchestrator using agents-as-tools
- [ ] Build CTAS Assessment Agent (Canadian Triage and Acuity Scale)
- [ ] Create Red Flag Detection Agent for critical symptoms
- [ ] Implement Initial Workup Suggester Agent
- [ ] Add YAML configuration for triage workflow
- [ ] Integrate Langfuse tracing for monitoring
- [ ] Create FastAPI endpoint: `/api/agents/triage`
- [ ] Build simple web UI for triage assessment
- [ ] Test with 10 real ED presentation scenarios
- [ ] Deploy as standalone microservice

**Success Criteria**: 
- Correctly assigns CTAS levels for 8/10 test cases
- Response time <5 seconds
- Clear audit trail in Langfuse

### Phase 2: Primary Care Diagnostic Support (Week 2-3)
**Deliverable**: Primary care assistant for differential diagnosis

- [ ] Create Primary Care Orchestrator with panel approach
- [ ] Implement Differential Diagnosis Agent
- [ ] Build Test Selection Agent with Canadian test catalog
- [ ] Create Cost Optimization Agent with OHIP billing codes
- [ ] Add Referral Recommendation Agent
- [ ] Implement agent template system for customization
- [ ] Create YAML configurations for common conditions
- [ ] Add budget constraints and cost tracking
- [ ] Create FastAPI endpoint: `/api/agents/primary-care`
- [ ] Build interactive differential diagnosis UI
- [ ] Test with 20 common primary care scenarios
- [ ] Add export functionality for EMR integration

**Success Criteria**:
- Generates appropriate differentials for 15/20 cases
- Average cost per workup <$300 CAD
- Includes evidence-based citations

### Phase 3: Mental Health Assessment Framework (Week 3-4)
**Deliverable**: Mental health screening and assessment tool

- [ ] Create Mental Health Orchestrator
- [ ] Implement PHQ-9/GAD-7 Screening Agent
- [ ] Build Risk Assessment Agent with safety protocols
- [ ] Create Treatment Recommendation Agent
- [ ] Add Crisis Detection Agent with escalation paths
- [ ] Implement privacy-preserving logging
- [ ] Create specialized YAML configs for mental health
- [ ] Add CAMH and provincial guidelines integration
- [ ] Create FastAPI endpoint: `/api/agents/mental-health`
- [ ] Build sensitive, user-friendly assessment UI
- [ ] Test with standardized mental health vignettes
- [ ] Implement mandatory reporter protocols

**Success Criteria**:
- 100% detection of crisis scenarios
- Appropriate escalation for high-risk cases
- Compliance with privacy regulations

### Phase 4: Long COVID Assessment Protocol (Week 4-5)
**Deliverable**: Comprehensive long COVID evaluation system

- [ ] Create Long COVID Orchestrator
- [ ] Implement Multi-System Review Agents:
  - Respiratory Assessment Agent
  - Cardiac Evaluation Agent
  - Neurological Screening Agent
  - Fatigue/PEM Assessment Agent
- [ ] Build Symptom Clustering Agent
- [ ] Create Test Prioritization Agent
- [ ] Add Longitudinal Tracking Agent
- [ ] Implement patient-reported outcome measures
- [ ] Create FastAPI endpoint: `/api/agents/long-covid`
- [ ] Build symptom tracking dashboard
- [ ] Test with published long COVID case studies
- [ ] Add export for research databases

**Success Criteria**:
- Comprehensive multi-system assessment
- Appropriate test ordering based on symptoms
- Longitudinal tracking capabilities

### Phase 5: Multi-Disciplinary Cancer Team Support (Week 5-6)
**Deliverable**: Cancer care coordination platform

- [ ] Create Cancer Care Orchestrator
- [ ] Implement Tumor Board Agents:
  - Medical Oncology Agent
  - Radiation Oncology Agent
  - Surgical Oncology Agent
  - Pathology Interpretation Agent
- [ ] Build Staging Calculator Agent
- [ ] Create Treatment Planning Agent
- [ ] Add Clinical Trial Matching Agent
- [ ] Implement CCO guidelines integration
- [ ] Create FastAPI endpoint: `/api/agents/cancer-care`
- [ ] Build collaborative decision UI
- [ ] Test with anonymized tumor board cases
- [ ] Add integration with provincial cancer registry

**Success Criteria**:
- Aligns with CCO treatment guidelines
- Appropriate staging calculations
- Identifies relevant clinical trials

### Phase 6: Evaluation & Production Readiness (Week 6-7)
**Deliverable**: Production-ready platform with all use cases

- [ ] Create comprehensive evaluation framework:
  - Diagnostic accuracy metrics
  - Cost-effectiveness analysis
  - Safety event tracking
  - User satisfaction surveys
- [ ] Implement production infrastructure:
  - Rate limiting and quotas
  - Circuit breakers and fallbacks
  - Error handling and recovery
  - Audit logging for compliance
- [ ] Add monitoring and alerting:
  - Prometheus metrics
  - Custom Langfuse dashboards
  - Cost tracking alerts
  - Performance monitoring
- [ ] Create documentation:
  - API documentation
  - Clinical user guides
  - Technical architecture docs
  - Compliance documentation
- [ ] Conduct security review:
  - PHIPA/PIPEDA compliance audit
  - Penetration testing
  - Data privacy assessment
- [ ] Prepare for deployment:
  - Docker containerization
  - Kubernetes manifests
  - CI/CD pipelines
  - Rollback procedures

**Success Criteria**:
- All 5 use cases operational
- >90% test coverage
- <1% error rate in production
- Full compliance documentation

## Success Metrics

### Technical Metrics
- Diagnostic accuracy on test cases: >70%
- Average cost per diagnosis: <$500 CAD
- Response time: <30 seconds for initial assessment
- System uptime: 99.9%

### Clinical Metrics
- Clinician satisfaction score: >4/5
- Time saved per case: >10 minutes
- Appropriate test ordering rate: >80%
- Safety event rate: <0.1%

### Business Metrics
- User adoption rate: >50% of target clinicians
- Cost savings per case: >$200 CAD
- Reduction in unnecessary tests: >30%
- ROI within 6 months

## Risk Mitigation

### Technical Risks
- **API Rate Limits**: Implement caching and request queuing
- **Model Costs**: Use tiered model selection (gpt-4.1-mini for simple tasks)
- **Latency**: Parallelize agent calls where possible
- **Reliability**: Implement circuit breakers and fallbacks

### Clinical Risks
- **Safety**: Maintain strict guardrails and disclaimers
- **Liability**: Clear documentation of decision support (not diagnosis)
- **Privacy**: Ensure PHIPA/PIPEDA compliance
- **Validation**: Require clinical review before production use

### Regulatory Considerations
- Align with Health Canada medical device regulations
- Ensure compliance with provincial privacy laws
- Document as clinical decision support (Class II device)
- Maintain audit trails for all recommendations

## Future Enhancements

### Phase 7+: Advanced Features
- Multi-modal support (imaging, lab results)
- Integration with EMR systems (Epic, Cerner)
- Real-time collaboration features
- Predictive analytics and risk scoring
- Continuous learning from outcomes

### Scalability Considerations
- Microservices architecture for agent deployment
- Kubernetes orchestration for scaling
- Redis caching for session management
- PostgreSQL for audit logging
- CDN for static assets

## Conclusion

This specification provides a comprehensive roadmap for implementing a MAI-DxO-inspired clinical decision support system using modern AI agent architectures. By leveraging the OpenAI Agents SDK and building upon the existing health assistant infrastructure, we can create a powerful tool that enhances clinical decision-making while maintaining cost-effectiveness and safety standards appropriate for the Canadian healthcare context.