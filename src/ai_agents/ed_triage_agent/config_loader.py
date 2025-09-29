"""
Configuration loader for clinical agents.
Loads agent configurations from YAML files.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


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


def load_ctas_config() -> Dict[str, Any]:
    """Load CTAS configuration."""
    return load_agent_config("ctas_config")


def format_ctas_levels_text(ctas_config: Dict[str, Any]) -> str:
    """
    Format CTAS levels into readable text for agent instructions.
    
    Args:
        ctas_config: CTAS configuration dictionary
        
    Returns:
        Formatted text describing CTAS levels
    """
    ctas_levels_text = ""
    for level, info in ctas_config.get('ctas_levels', {}).items():
        ctas_levels_text += f"\nLevel {level} - {info['name']}: {info['description']}"
        ctas_levels_text += f"\n  Target time: {info['target_time']}"
        examples = info.get('examples', [])[:3]  # First 3 examples
        if examples:
            ctas_levels_text += f"\n  Examples: {', '.join(examples)}"
    
    return ctas_levels_text


def format_critical_symptoms(ctas_config: Dict[str, Any]) -> str:
    """
    Format critical symptoms into readable text.
    
    Args:
        ctas_config: CTAS configuration dictionary
        
    Returns:
        Formatted text describing critical symptoms
    """
    symptoms_text = ""
    for category, symptoms in ctas_config.get('critical_symptoms', {}).items():
        symptoms_text += f"\n{category.upper()}:"
        for symptom in symptoms:
            symptoms_text += f"\n  - {symptom}"
    
    return symptoms_text


def format_workup_guidelines(ctas_config: Dict[str, Any]) -> str:
    """
    Format initial workup guidelines into readable text.
    
    Args:
        ctas_config: CTAS configuration dictionary
        
    Returns:
        Formatted text describing workup guidelines
    """
    workup_text = ""
    for presentation, workup in ctas_config.get('initial_workup', {}).items():
        workup_text += f"\n{presentation.replace('_', ' ').title()}:"
        if 'basic' in workup:
            workup_text += f"\n  Basic: {', '.join(workup['basic'])}"
        if 'additional' in workup:
            workup_text += f"\n  Additional: {', '.join(workup['additional'])}"
    
    return workup_text


def prepare_agent_context(
    config: Dict[str, Any],
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Prepare context variables for agent instructions.
    
    Args:
        config: Agent configuration dictionary
        overrides: Optional overrides for context variables
        
    Returns:
        Complete context dictionary for formatting instructions
    """
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
    
    # Format list fields as comma-separated strings
    if 'available_resources' in context and isinstance(context['available_resources'], list):
        context['available_resources'] = ', '.join(context['available_resources'])
    
    # Apply overrides if provided
    if overrides:
        context.update(overrides)
    
    return context