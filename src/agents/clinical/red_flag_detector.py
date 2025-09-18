"""
Red Flag Detector Agent - identifies critical symptoms requiring immediate attention.
Uses OpenAI Agents SDK pattern with YAML configuration.
"""

from typing import Optional
from pydantic import BaseModel, Field

try:
    from agents import Agent
except ImportError:
    Agent = None

from .config_loader import load_agent_config, prepare_agent_context


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


def create_red_flag_detector() -> Agent:
    """
    Create the red flag detection agent from YAML configuration.
    
    Returns:
        Configured Agent instance for red flag detection
    """
    # Load configuration from YAML
    config = load_agent_config("red_flag_detector")
    
    # Prepare context
    context = prepare_agent_context(config)
    
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
            output_type=RedFlagAssessment,
            temperature=config.get('temperature', 0.2)
        )
    
    return Agent(
        name=config['name'],
        model=config['model'],
        instructions=instructions,
        output_type=RedFlagAssessment,
        temperature=config.get('temperature', 0.2)
    )