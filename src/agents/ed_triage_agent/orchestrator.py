"""
Emergency Triage Orchestrator - coordinates multiple specialist agents.
Uses OpenAI Agents SDK pattern with agents.as_tool() for clean integration.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

try:
    from agents import Agent, Runner, RunResult
    from langfuse import Langfuse
except ImportError:
    # Fallback for development
    Agent = None
    Runner = None
    RunResult = None
    Langfuse = None

from .config_loader import load_agent_config, prepare_agent_context
from .triage_assessor import create_triage_assessor
from .red_flag_detector import create_red_flag_detector
from .workup_suggester import create_workup_suggester


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


def create_triage_orchestrator(
    hospital_name: Optional[str] = None,
    available_resources: Optional[list[str]] = None
) -> Agent:
    """
    Create the main triage orchestrator agent that coordinates specialist assessments.
    
    This orchestrator uses three specialist agents as tools:
    1. Red Flag Detector - Identifies critical symptoms
    2. CTAS Triage Assessor - Determines acuity level
    3. Workup Suggester - Recommends initial tests
    
    Args:
        hospital_name: Optional override for hospital name
        available_resources: Optional override for available resources
        
    Returns:
        Configured orchestrator Agent with specialist agents as tools
    """
    # Load configuration from YAML
    config = load_agent_config("triage_orchestrator")
    
    # Prepare context with overrides
    overrides = {}
    if hospital_name:
        overrides['hospital_name'] = hospital_name
    
    context = prepare_agent_context(config, overrides)
    
    # Format instructions with context
    instructions = config['instructions'].format(**context)
    
    if Agent is None:
        # Return a mock for development
        class MockOrchestrator:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
                    
            async def run(self, patient_data: str) -> TriageDecision:
                """Mock run method for development."""
                return TriageDecision(
                    final_ctas_level=3,
                    urgency="Urgent",
                    red_flags_identified=["Development mode - no actual assessment"],
                    initial_actions=["Complete patient registration"],
                    recommended_tests=["ECG", "CBC"],
                    estimated_wait_time="30 minutes",
                    disposition="Emergency treatment area - requires physician assessment",
                    clinical_summary="Mock triage decision for development",
                    confidence=0.85
                )
        
        return MockOrchestrator(
            name=config['name'],
            model=config['model'],
            instructions=instructions,
            output_type=TriageDecision,
            temperature=config.get('temperature', 0.3)
        )
    
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
    
    # Create the orchestrator agent with specialist agents as tools
    return Agent(
        name=config['name'],
        model=config['model'],
        instructions=instructions,
        tools=tools,  # Specialist agents as tools via as_tool()
        output_type=TriageDecision  # Structured final output
        # Note: temperature would be set via model_kwargs if needed
    )


async def run_triage_assessment(
    patient_data: Dict[str, Any],
    session_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    langfuse_enabled: bool = True,
    streaming: bool = False
) -> TriageDecision:
    """
    Run a complete triage assessment using the orchestrator and specialist agents.
    
    Args:
        patient_data: Patient information dictionary
        session_id: Optional session ID for tracking
        trace_id: Optional trace ID for Langfuse
        langfuse_enabled: Whether to enable Langfuse tracing
        
    Returns:
        Complete TriageDecision with all assessments
    """
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
    
    try:
        # Create the orchestrator
        orchestrator = create_triage_orchestrator()
        
        # Format patient data as string for the agent
        patient_info = _format_patient_data(patient_data)
        
        if Runner is None:
            # Development mode - return mock decision
            return TriageDecision(
                final_ctas_level=3,
                urgency="Urgent",
                red_flags_identified=["Development mode - no actual assessment"],
                initial_actions=["Complete patient registration", "Obtain vital signs"],
                recommended_tests=["ECG", "CBC", "Basic metabolic panel"],
                estimated_wait_time="30 minutes",
                disposition="Emergency treatment area - requires physician assessment",
                clinical_summary="Mock triage assessment in development mode",
                confidence=0.0
            )
        
        # Run the orchestrator with specialist tools
        result = await Runner.run(
            orchestrator,
            input=patient_info,
            max_turns=4  # 3 tool calls (one per specialist) + 1 final response
        )
        
        # Update Langfuse trace with results if available
        if langfuse_trace:
            langfuse_trace.update(
                output=result.final_output.model_dump() if hasattr(result.final_output, 'model_dump') else str(result.final_output),
                metadata={
                    "ctas_level": getattr(result.final_output, 'final_ctas_level', None),
                    "confidence": getattr(result.final_output, 'confidence', None),
                    "red_flags_count": len(getattr(result.final_output, 'red_flags_identified', [])),
                    "token_usage": getattr(result, 'usage', None)
                }
            )
        
        # Return the structured output
        if isinstance(result.final_output, TriageDecision):
            return result.final_output
        
        # Fallback if output isn't properly structured
        return TriageDecision(
            final_ctas_level=2,  # Default to emergent for safety
            urgency="Emergent",
            red_flags_identified=["Unable to complete full assessment"],
            initial_actions=["Immediate physician assessment required"],
            recommended_tests=["As per physician assessment"],
            estimated_wait_time="Immediate",
            disposition="Resuscitation area - immediate physician assessment",
            clinical_summary="Assessment incomplete - defaulting to high acuity for safety",
            confidence=0.0
        )
        
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
    
    finally:
        # Ensure Langfuse flushes
        if langfuse_enabled and Langfuse:
            try:
                langfuse = Langfuse()
                langfuse.flush()
            except:
                pass


def _format_patient_data(patient_data: Dict[str, Any]) -> str:
    """Format patient data dictionary into a readable string for the agents."""
    sections = []
    
    # Demographics
    if any(k in patient_data for k in ["age", "sex", "gender"]):
        demo = []
        if "age" in patient_data:
            demo.append(f"Age: {patient_data['age']}")
        if "sex" in patient_data:
            demo.append(f"Sex: {patient_data['sex']}")
        elif "gender" in patient_data:
            demo.append(f"Gender: {patient_data['gender']}")
        sections.append(f"DEMOGRAPHICS: {', '.join(demo)}")
    
    # Chief complaint
    if "chief_complaint" in patient_data:
        sections.append(f"CHIEF COMPLAINT: {patient_data['chief_complaint']}")
    
    # History of present illness
    if "history" in patient_data:
        sections.append(f"HISTORY OF PRESENT ILLNESS: {patient_data['history']}")
    
    # Vital signs
    if "vitals" in patient_data:
        vitals = patient_data["vitals"]
        vital_list = []
        if "blood_pressure" in vitals:
            vital_list.append(f"BP: {vitals['blood_pressure']}")
        if "heart_rate" in vitals:
            vital_list.append(f"HR: {vitals['heart_rate']}")
        if "respiratory_rate" in vitals:
            vital_list.append(f"RR: {vitals['respiratory_rate']}")
        if "temperature" in vitals:
            vital_list.append(f"Temp: {vitals['temperature']}°C")
        if "oxygen_saturation" in vitals:
            vital_list.append(f"SpO2: {vitals['oxygen_saturation']}%")
        if "pain_scale" in vitals:
            vital_list.append(f"Pain: {vitals['pain_scale']}/10")
        if vital_list:
            sections.append(f"VITAL SIGNS: {', '.join(vital_list)}")
    
    # Symptoms
    if "symptoms" in patient_data:
        if isinstance(patient_data["symptoms"], list):
            sections.append(f"SYMPTOMS: {', '.join(patient_data['symptoms'])}")
        else:
            sections.append(f"SYMPTOMS: {patient_data['symptoms']}")
    
    # Medical history
    if "medical_history" in patient_data:
        if isinstance(patient_data["medical_history"], list):
            sections.append(f"PAST MEDICAL HISTORY: {', '.join(patient_data['medical_history'])}")
        else:
            sections.append(f"PAST MEDICAL HISTORY: {patient_data['medical_history']}")
    
    # Medications
    if "medications" in patient_data:
        if isinstance(patient_data["medications"], list):
            sections.append(f"CURRENT MEDICATIONS: {', '.join(patient_data['medications'])}")
        else:
            sections.append(f"CURRENT MEDICATIONS: {patient_data['medications']}")
    
    # Allergies
    if "allergies" in patient_data:
        if isinstance(patient_data["allergies"], list):
            sections.append(f"ALLERGIES: {', '.join(patient_data['allergies'])}")
        else:
            sections.append(f"ALLERGIES: {patient_data['allergies']}")
    
    return "\n".join(sections)