"""
Request models for Dr. OFF MCP tools.
Defines the structure of incoming requests for each tool.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class PatientContext(BaseModel):
    """Patient context information for coverage determination."""
    age: Optional[int] = Field(None, description="Patient age in years")
    setting: Optional[Literal["acute", "community", "ltc"]] = Field(
        None, description="Care setting"
    )
    plan: Optional[Literal["ODB", "private", "none"]] = Field(
        None, description="Insurance plan type"
    )
    income: Optional[float] = Field(None, description="Annual income for CEP eligibility")


class DeviceSpec(BaseModel):
    """Device specification for ADP queries."""
    category: Literal["mobility", "comm_aids"] = Field(
        ..., description="Device category"
    )
    type: str = Field(..., description="Specific device type (e.g., walker, power_wheelchair)")


class QueryHints(BaseModel):
    """Optional hints to guide the query processing."""
    codes: Optional[List[str]] = Field(None, description="OHIP fee codes mentioned")
    device: Optional[DeviceSpec] = Field(None, description="Device specification")
    drug: Optional[str] = Field(None, description="Drug name or ingredient")


class CoverageAnswerRequest(BaseModel):
    """Request model for coverage.answer orchestrator."""
    intent: Optional[Literal["billing", "device", "drug"]] = Field(
        None, description="Detected intent (auto-classified if not provided)"
    )
    patient: Optional[PatientContext] = Field(
        default_factory=PatientContext, description="Patient context"
    )
    question: str = Field(..., description="Free-text clinician question")
    hints: Optional[QueryHints] = Field(
        default_factory=QueryHints, description="Optional hints for processing"
    )


class ScheduleGetRequest(BaseModel):
    """Request model for schedule.get tool."""
    q: str = Field(..., description="Query text for OHIP schedule search")
    codes: Optional[List[str]] = Field(None, description="Specific fee codes to lookup")
    include: List[Literal["codes", "fee", "limits", "documentation", "commentary"]] = Field(
        default=["codes", "fee", "limits", "documentation"],
        description="Fields to include in response"
    )
    top_k: int = Field(default=6, ge=1, le=20, description="Number of results to return")


class UseCase(BaseModel):
    """Device use case for eligibility determination."""
    daily: Optional[bool] = Field(None, description="Used daily")
    location: Optional[str] = Field(
        None, description="Usage locations (e.g., 'home+entry_exit')"
    )
    independent_transfer: Optional[bool] = Field(
        None, description="Can transfer independently"
    )


class ADPGetRequest(BaseModel):
    """Request model for adp.get tool."""
    device: DeviceSpec = Field(..., description="Device specification")
    check: List[Literal["eligibility", "exclusions", "funding", "cep"]] = Field(
        default=["eligibility", "exclusions", "funding"],
        description="Aspects to check"
    )
    use_case: Optional[UseCase] = Field(None, description="Device use case details")
    patient_income: Optional[float] = Field(
        None, description="Patient income for CEP eligibility"
    )


class ODBGetRequest(BaseModel):
    """Request model for odb.get tool."""
    drug: str = Field(..., description="Drug name, brand, or ingredient")
    check_alternatives: bool = Field(
        default=True, description="Check for interchangeable alternatives"
    )
    include_lu: bool = Field(
        default=True, description="Include Limited Use criteria if applicable"
    )
    top_k: int = Field(default=5, ge=1, le=10, description="Number of alternatives to return")


class SourcePassagesRequest(BaseModel):
    """Request model for source.passages tool."""
    chunk_ids: List[str] = Field(..., description="Chunk IDs to retrieve")
    highlight_terms: Optional[List[str]] = Field(
        None, description="Terms to highlight in passages"
    )