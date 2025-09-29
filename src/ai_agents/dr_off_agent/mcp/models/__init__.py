"""
Pydantic models for Dr. OFF MCP tools.
"""

from .request import (
    CoverageAnswerRequest,
    ScheduleGetRequest,
    ADPGetRequest,
    ODBGetRequest,
    SourcePassagesRequest,
    PatientContext,
    DeviceSpec,
    QueryHints,
    UseCase
)

from .response import (
    CoverageAnswerResponse,
    ScheduleGetResponse,
    ADPGetResponse,
    ODBGetResponse,
    SourcePassagesResponse,
    Citation,
    Highlight,
    Conflict,
    FollowUp,
    ToolTrace,
    ScheduleItem,
    Eligibility,
    Funding,
    CEPInfo,
    DrugCoverage,
    InterchangeableDrug,
    LowestCostDrug,
    SourcePassage
)

__all__ = [
    # Request models
    'CoverageAnswerRequest',
    'ScheduleGetRequest',
    'ADPGetRequest',
    'ODBGetRequest',
    'SourcePassagesRequest',
    'PatientContext',
    'DeviceSpec',
    'QueryHints',
    'UseCase',
    # Response models
    'CoverageAnswerResponse',
    'ScheduleGetResponse',
    'ADPGetResponse',
    'ODBGetResponse',
    'SourcePassagesResponse',
    'Citation',
    'Highlight',
    'Conflict',
    'FollowUp',
    'ToolTrace',
    'ScheduleItem',
    'Eligibility',
    'Funding',
    'CEPInfo',
    'DrugCoverage',
    'InterchangeableDrug',
    'LowestCostDrug',
    'SourcePassage'
]