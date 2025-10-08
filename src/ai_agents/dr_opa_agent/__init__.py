"""Dr. OPA (Ontario Practice Advice) AI Agent.

Provides Ontario-specific primary care and practice guidance to clinicians
by ingesting and retrieving from authoritative sources like CPSO, Ontario Health/CCO,
CEP, PHO, and MOH.
"""

from .openai_agent_http import create_dr_opa_agent

__all__ = ['create_dr_opa_agent']

__version__ = "0.1.0"