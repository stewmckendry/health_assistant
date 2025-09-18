# OpenAI Agents SDK Cheatsheet for MAI-DxO Implementation

## Quick Reference for Clinical Decision Support Development

### Installation & Setup

```bash
# Install the SDK (v0.3.1+)
pip install openai-agents

# Required environment variables
export OPENAI_API_KEY="sk-..."
export LANGFUSE_PUBLIC_KEY="pk-..."  # For tracing
export LANGFUSE_SECRET_KEY="sk-..."
```

### Core Dependencies

```python
from agents import (
    Agent,           # Core agent class
    Runner,          # Runs agents and workflows
    Session,         # Session management
    function_tool,   # Decorator for function tools
    handoff,         # Create agent handoffs
    RunResult,       # Result from Runner.run
    RunContextWrapper, # Context for agents
)
from agents.models import OpenAIResponsesModel
from agents.tool import FunctionTool, WebSearchTool
from agents.guardrail import InputGuardrail, OutputGuardrail
from agents.tracing import LangfuseTracing
```

## Key Classes & Methods

### 1. Agent Class

```python
from agents import Agent
from typing import Optional, List, Any

class Agent:
    def __init__(
        self,
        name: str,                          # Agent identifier
        model: str = "gpt-4o-mini",        # Model to use
        instructions: str = "",              # System instructions
        tools: List[Tool] = None,           # Available tools
        handoffs: List[Agent | Handoff] = None,  # Agent handoffs
        input_guardrails: List[InputGuardrail] = None,
        output_guardrails: List[OutputGuardrail] = None,
        context_variables: dict = None,     # Shared context
        output_type: type = None,           # Expected output schema
        hooks: AgentHooks = None,           # Lifecycle callbacks
    ):
        pass
```

### 2. Runner Class - Core Execution

```python
from agents import Runner, RunResult

# Basic agent run
result: RunResult = await Runner.run(
    starting_agent=agent,
    input="Patient presents with chest pain",
    context={"hospital": "Toronto General"},
    max_turns=10,                          # Max AI invocations
    session=session,                       # Optional session
)

# Access results
print(result.final_output)                 # Final agent output
print(result.usage)                        # Token usage
print(result.messages)                     # Conversation history
```

### 3. Function Tools - Agents as Tools Pattern (MAI-DxO)

```python
from agents import function_tool, FunctionTool
from typing import Literal

# Method 1: Decorator approach
@function_tool
async def consult_specialist(
    specialty: Literal["cardiology", "neurology", "emergency"],
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

# Method 2: FunctionTool class
specialist_tool = FunctionTool(
    fn=consult_specialist,
    name="specialist_consultation",
    description="Get specialist opinion on patient case"
)
```

### 4. Sessions - Conversation History

```python
from agents.memory.session import Session
from agents.memory.in_memory import InMemoryStore

# Create session with memory
store = InMemoryStore()
session = Session(
    session_id="triage-12345",
    store=store
)

# Run agent with session (maintains history)
result = await Runner.run(
    agent=triage_agent,
    input="Patient, 45yo male, chest pain",
    session=session
)

# Continue conversation in same session
followup = await Runner.run(
    agent=triage_agent,
    input="Pain radiates to left arm",
    session=session  # Same session preserves context
)
```

### 5. Handoffs - Multi-Agent Collaboration

```python
from agents import Agent, handoff

# Create specialist agents
hypothesis_agent = Agent(name="Dr. Hypothesis")
test_chooser_agent = Agent(name="Dr. Test-Chooser")
challenger_agent = Agent(name="Dr. Challenger")

# Orchestrator with handoffs
orchestrator = Agent(
    name="Clinical Orchestrator",
    instructions="Coordinate diagnostic workflow",
    handoffs=[
        hypothesis_agent,
        handoff(
            test_chooser_agent,
            tool_name_override="request_test_selection",
            input_filter=lambda x: {"patient": x["patient"], "hypothesis": x["hypothesis"]}
        ),
        challenger_agent
    ]
)
```

## MAI-DxO Specific Patterns

### Clinical Agent Template System

```python
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import yaml

@dataclass
class ClinicalAgentTemplate:
    """Template for creating specialized clinical agents"""
    name: str
    role: str
    model: str = "gpt-4o-mini"
    instructions_template: str = ""
    tools: List[Any] = None
    context_variables: Dict[str, Any] = None
    
    def create_agent(self, **runtime_context) -> Agent:
        """Instantiate agent with runtime context"""
        context = {**(self.context_variables or {}), **runtime_context}
        instructions = self.instructions_template.format(**context)
        
        return Agent(
            name=self.name,
            model=self.model,
            instructions=instructions,
            tools=self.tools or []
        )

# Load from YAML
def load_agent_config(yaml_path: str) -> ClinicalAgentTemplate:
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    return ClinicalAgentTemplate(**config)
```

### Emergency Triage Orchestrator (Phase 1)

```python
from agents import Agent, Runner, function_tool
import asyncio

class TriageOrchestrator:
    """Emergency Department Triage Assistant"""
    
    def __init__(self):
        # Load specialist configurations
        self.ctas_agent = self._create_ctas_agent()
        self.red_flag_agent = self._create_red_flag_agent()
        self.workup_agent = self._create_workup_agent()
        
        # Main orchestrator
        self.orchestrator = Agent(
            name="ED Triage Orchestrator",
            model="gpt-4o",
            instructions="""
            You are an emergency department triage coordinator.
            Assess patient acuity using CTAS scale (1-5).
            Identify red flags and suggest initial workup.
            Always prioritize patient safety.
            """,
            tools=[
                self._assess_ctas,
                self._check_red_flags,
                self._suggest_workup
            ]
        )
    
    @function_tool
    async def _assess_ctas(self, symptoms: str, vitals: dict) -> dict:
        """Assess CTAS level (Canadian Triage and Acuity Scale)"""
        result = await Runner.run(
            self.ctas_agent,
            input=f"Symptoms: {symptoms}\nVitals: {vitals}"
        )
        return {"ctas_level": result.final_output}
    
    @function_tool
    async def _check_red_flags(self, presentation: str) -> list:
        """Check for critical red flags"""
        result = await Runner.run(
            self.red_flag_agent,
            input=presentation
        )
        return result.final_output
    
    async def triage(self, patient_data: dict) -> dict:
        """Run triage assessment"""
        result = await Runner.run(
            self.orchestrator,
            input=str(patient_data),
            max_turns=5
        )
        return {
            "ctas_level": result.final_output.get("ctas_level"),
            "red_flags": result.final_output.get("red_flags"),
            "initial_workup": result.final_output.get("workup"),
            "rationale": result.final_output.get("rationale")
        }
```

### Cost-Aware Test Selection

```python
@function_tool
async def select_tests_with_budget(
    symptoms: List[str],
    differential: List[str],
    budget_cap: float = 500.00,
    available_tests: List[dict] = None
) -> dict:
    """Select tests optimizing diagnostic yield vs cost"""
    
    # OHIP billing codes and costs
    test_costs = {
        "CBC": 25.00,
        "Troponin": 35.00,
        "ECG": 40.00,
        "Chest X-ray": 75.00,
        "CT Head": 250.00,
        "MRI Brain": 450.00
    }
    
    # Create cost optimization agent
    stewardship_agent = Agent(
        name="Dr. Stewardship",
        instructions=f"""
        Select diagnostic tests that maximize information gain
        while staying under ${budget_cap} CAD.
        Consider local availability: {available_tests}
        Use evidence-based testing strategies.
        """
    )
    
    result = await Runner.run(
        stewardship_agent,
        input={
            "symptoms": symptoms,
            "differential": differential,
            "test_costs": test_costs,
            "budget": budget_cap
        }
    )
    
    return result.final_output
```

## Lifecycle & Tracing

### Full Agent Lifecycle

```python
# 1. Initialize
agent = Agent(name="Clinical Assistant")

# 2. Configure
agent.instructions = load_prompt("clinical_assistant.yaml")
agent.tools = [web_search_tool, test_database_tool]

# 3. Run with tracing
from agents.tracing import LangfuseTracing

tracing = LangfuseTracing(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY")
)

result = await Runner.run(
    agent,
    input="Patient query",
    hooks=RunHooks(on_trace=tracing.trace)
)

# 4. Inspect results
print(f"Output: {result.final_output}")
print(f"Tokens used: {result.usage.total_tokens}")
print(f"Trace URL: {tracing.get_trace_url()}")
```

### Multi-Turn Conversations

```python
# Initialize session
session = Session(session_id="patient-123")

# Turn 1: Initial assessment
result1 = await Runner.run(
    triage_agent,
    input="Chest pain for 2 hours",
    session=session
)

# Turn 2: Follow-up questions
result2 = await Runner.run(
    triage_agent,
    input="Pain is 7/10, crushing sensation",
    session=session  # Maintains context
)

# Turn 3: Test results
result3 = await Runner.run(
    diagnostic_agent,
    input="Troponin elevated at 0.5",
    session=session
)

# Session contains full history
history = session.get_messages()
```

## Guardrails & Safety

### Input/Output Validation

```python
from agents.guardrail import InputGuardrail, OutputGuardrail

class EmergencyDetector(InputGuardrail):
    async def __call__(self, input_text: str) -> str | None:
        """Return None to allow, or message to block"""
        if any(word in input_text.lower() for word in ["suicide", "overdose"]):
            return "EMERGENCY: Route to crisis intervention"
        return None

class DiagnosisBlocker(OutputGuardrail):
    async def __call__(self, output: str) -> str:
        """Modify output to ensure safety"""
        forbidden = ["you have", "diagnosis is", "you should take"]
        for phrase in forbidden:
            if phrase in output.lower():
                return output + "\n\n⚠️ Reminder: Consult healthcare provider for diagnosis."
        return output

# Apply to agent
safe_agent = Agent(
    name="Patient Assistant",
    input_guardrails=[EmergencyDetector()],
    output_guardrails=[DiagnosisBlocker()]
)
```

## Common Commands & Debugging

```bash
# Run with debug logging
AGENTS_DEBUG=1 python your_script.py

# Test agent in REPL
python -m agents.repl

# View Langfuse traces
# Go to: https://cloud.langfuse.com/
```

### Debug Pattern

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Add hooks for debugging
from agents.lifecycle import RunHooks

hooks = RunHooks(
    on_turn_start=lambda ctx: print(f"Turn {ctx.turn}: Starting"),
    on_tool_call=lambda ctx, tool, args: print(f"Tool: {tool} with {args}"),
    on_handoff=lambda ctx, next_agent: print(f"Handoff to: {next_agent.name}")
)

result = await Runner.run(agent, input="test", hooks=hooks)
```

## YAML Configuration Example

```yaml
# configs/agents/triage_agent.yaml
name: "Emergency Triage Specialist"
role: "triage"
model: "gpt-4o-mini"
instructions_template: |
  You are an emergency department triage specialist at {hospital_name}.
  
  Your responsibilities:
  - Assess patient acuity using CTAS scale (1-5)
  - Identify red flags requiring immediate attention
  - Recommend initial diagnostic workup
  - Consider available resources: {available_resources}
  
  Current ED wait time: {wait_time}
  
  Always prioritize patient safety over efficiency.

context_variables:
  hospital_name: "Toronto General Hospital"
  available_resources:
    - "CT Scanner"
    - "X-ray"
    - "Point-of-care ultrasound"
    - "Basic labs (CBC, Chem, Troponin)"
    - "ECG"
  wait_time: "2 hours"

tools:
  - "ctas_calculator"
  - "red_flag_checker"
  - "initial_workup_suggester"
```

## Quick Start for Phase 1

```python
# main.py - Emergency Triage Assistant
import asyncio
from agents import Agent, Runner

async def main():
    # Create triage orchestrator
    orchestrator = Agent(
        name="ED Triage Assistant",
        model="gpt-4o-mini",
        instructions="Assess emergency patients using CTAS scale"
    )
    
    # Run triage
    patient = {
        "age": 65,
        "chief_complaint": "chest pain",
        "vitals": {"bp": "150/90", "hr": 95}
    }
    
    result = await Runner.run(
        orchestrator,
        input=str(patient)
    )
    
    print(f"CTAS Level: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Key Differences from Anthropic SDK

| Feature | OpenAI Agents SDK | Anthropic SDK |
|---------|------------------|---------------|
| Multi-agent | Native support via handoffs | Manual orchestration |
| Tools | Function tools + hosted tools | Tool use via API |
| Sessions | Built-in session management | Manual tracking |
| Tracing | Integrated (Langfuse, etc.) | External setup |
| Streaming | Native async/await | Stream responses |
| Guardrails | Built-in system | Custom implementation |

## Resources

- [Official Docs](https://openai.github.io/openai-agents-python/)
- [GitHub Repo](https://github.com/openai/openai-agents-python)
- [Examples](https://github.com/openai/openai-agents-python/tree/main/examples)
- [API Reference](https://openai.github.io/openai-agents-python/ref/)