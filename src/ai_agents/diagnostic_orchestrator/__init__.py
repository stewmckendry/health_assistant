"""
The Chief - Clinical Intelligence Orchestrator

A medical diagnostic orchestrator inspired by Microsoft's MAI-DxO that coordinates
between Dr. OPA, Dr. OFF, and Agent 97 to provide comprehensive clinical guidance
for Ontario healthcare providers. Named "The Chief" after chief roles in medicine
(Chief Medical Officer, Chief of Staff).
"""

from .orchestrator_agent import DiagnosticOrchestrator, create_diagnostic_orchestrator
from .orchestrator_agent_http import ClinicalIntelligenceOrchestratorHTTP, create_orchestrator_http

__all__ = [
    'DiagnosticOrchestrator',
    'create_diagnostic_orchestrator',
    'ClinicalIntelligenceOrchestratorHTTP',
    'create_orchestrator_http'
]