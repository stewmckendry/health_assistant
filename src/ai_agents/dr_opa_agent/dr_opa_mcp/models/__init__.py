"""
MCP model definitions for Dr. OPA agent.
"""

from .request import (
    SearchSectionsRequest,
    GetSectionRequest,
    PolicyCheckRequest,
    ProgramLookupRequest,
    IPACGuidanceRequest,
    FreshnessProbeRequest
)

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
    'SearchSectionsRequest',
    'GetSectionRequest',
    'PolicyCheckRequest',
    'ProgramLookupRequest',
    'IPACGuidanceRequest',
    'FreshnessProbeRequest',
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