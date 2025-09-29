"""
Initial Workup Suggester Agent - recommends appropriate diagnostic tests.
Uses OpenAI Agents SDK pattern with YAML configuration.
"""

from typing import Optional
from pydantic import BaseModel, Field

try:
    from agents import Agent
except ImportError:
    Agent = None

from .config_loader import load_agent_config, prepare_agent_context


class TestRecommendation(BaseModel):
    """Individual test recommendation with rationale."""
    test: str = Field(description="Name of the test")
    rationale: str = Field(description="Reason for ordering this test")


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


def create_workup_suggester(
    available_resources: Optional[list[str]] = None
) -> Agent:
    """
    Create the initial workup suggester agent from YAML configuration.
    
    Args:
        available_resources: Optional override for available resources
        
    Returns:
        Configured Agent instance for workup suggestions
    """
    # Load configuration from YAML
    config = load_agent_config("workup_suggester")
    
    # Prepare context with overrides
    overrides = {}
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
            output_type=WorkupPlan,
            temperature=config.get('temperature', 0.4)
        )
    
    return Agent(
        name=config['name'],
        model=config['model'],
        instructions=instructions,
        output_type=WorkupPlan
        # Note: temperature would be set via model_kwargs if needed
    )