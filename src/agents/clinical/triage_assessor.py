"""
CTAS Triage Assessment Agent - evaluates patient acuity level.
Uses OpenAI Agents SDK pattern with YAML configuration.
"""

from typing import Optional
from pydantic import BaseModel, Field

try:
    from agents import Agent
except ImportError:
    # Fallback for development without the SDK installed
    Agent = None

from .config_loader import load_agent_config, prepare_agent_context


class CTASAssessment(BaseModel):
    """Structured output for CTAS assessment."""
    ctas_level: int = Field(description="CTAS level (1-5)", ge=1, le=5)
    urgency: str = Field(description="Urgency level name (Resuscitation/Emergent/Urgent/Less Urgent/Non-Urgent)")
    confidence: float = Field(description="Confidence score (0-1)", ge=0.0, le=1.0)
    reasoning: str = Field(description="Clinical reasoning for the assessment")
    key_factors: list[str] = Field(description="Key factors influencing the CTAS level")


def create_triage_assessor(
    hospital_name: Optional[str] = None,
    available_resources: Optional[list[str]] = None
) -> Agent:
    """
    Create the CTAS triage assessment agent from YAML configuration.
    
    Args:
        hospital_name: Optional override for hospital name
        available_resources: Optional override for available resources
        
    Returns:
        Configured Agent instance for triage assessment
    """
    # Load configuration from YAML
    config = load_agent_config("triage_assessor")
    
    # Prepare context with overrides
    overrides = {}
    if hospital_name:
        overrides['hospital_name'] = hospital_name
    if available_resources:
        overrides['available_resources'] = ', '.join(available_resources)
    
    context = prepare_agent_context(config, overrides)
    
    # Format instructions with context
    instructions = config['instructions'].format(**context)
    
    if Agent is None:
        # Return a mock agent for development
        class MockAgent:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        return MockAgent(
            name=config['name'],
            model=config['model'],
            instructions=instructions,
            output_type=CTASAssessment,
            temperature=config.get('temperature', 0.3)
        )
    
    return Agent(
        name=config['name'],
        model=config['model'],
        instructions=instructions,
        output_type=CTASAssessment
        # Note: temperature would be set via model_kwargs if needed
    )