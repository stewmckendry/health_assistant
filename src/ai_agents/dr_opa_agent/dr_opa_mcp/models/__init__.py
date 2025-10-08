"""
MCP model definitions for Dr. OPA agent.
"""

from .request import StandardToolRequest

from .response import (
    SearchSectionsResponse,
    GetSectionResponse,
    PolicyCheckResponse,
    ProgramLookupResponse,
    IPACGuidanceResponse,
    FreshnessProbeResponse,
    Section,
    Document,
    Citation,
    Highlight,
    Conflict,
    Update
)

__all__ = [
    # Requests
    'StandardToolRequest',
    # Responses
    'SearchSectionsResponse',
    'GetSectionResponse',
    'PolicyCheckResponse',
    'ProgramLookupResponse',
    'IPACGuidanceResponse',
    'FreshnessProbeResponse',
    # Shared models
    'Section',
    'Document',
    'Citation',
    'Highlight',
    'Conflict',
    'Update'
]