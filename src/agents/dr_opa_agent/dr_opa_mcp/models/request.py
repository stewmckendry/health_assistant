"""
Request models for Dr. OPA MCP tools.
Defines the structure of incoming requests for each tool.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class SearchSectionsRequest(BaseModel):
    """Request model for opa.search_sections tool."""
    query: str = Field(..., description="Clinical query or practice question")
    sources: Optional[List[Literal["cpso", "ontario_health", "cep", "pho", "moh"]]] = Field(
        None, description="Specific sources to search (default: all)"
    )
    doc_types: Optional[List[Literal["policy", "advice", "guideline", "standard", "tool"]]] = Field(
        None, description="Document types to include"
    )
    topics: Optional[List[str]] = Field(
        None, description="Topics to filter by (e.g., 'prescribing', 'screening')"
    )
    date_range: Optional[Dict[str, str]] = Field(
        None, description="Date range filter {from: 'YYYY-MM-DD', to: 'YYYY-MM-DD'}"
    )
    top_k: int = Field(default=10, ge=1, le=20, description="Number of results to return")
    include_superseded: bool = Field(
        default=False, description="Include superseded documents"
    )


class GetSectionRequest(BaseModel):
    """Request model for opa.get_section tool."""
    section_id: str = Field(..., description="Section ID to retrieve")
    include_children: bool = Field(
        default=True, description="Include child chunks for detailed content"
    )
    include_context: bool = Field(
        default=True, description="Include surrounding sections for context"
    )


class PolicyCheckRequest(BaseModel):
    """Request model for opa.policy_check tool."""
    topic: str = Field(..., description="Clinical topic or practice area")
    situation: Optional[str] = Field(
        None, description="Specific situation or context"
    )
    policy_level: Optional[Literal["expectation", "advice", "both"]] = Field(
        default="both", description="CPSO policy level to retrieve"
    )
    include_related: bool = Field(
        default=True, description="Include related policies and advice"
    )


class ProgramLookupRequest(BaseModel):
    """Request model for opa.program_lookup tool."""
    program: Literal["breast", "cervical", "colorectal", "lung", "hpv"] = Field(
        ..., description="Screening program to lookup"
    )
    patient_age: Optional[int] = Field(
        None, description="Patient age for eligibility check"
    )
    risk_factors: Optional[List[str]] = Field(
        None, description="Risk factors (e.g., 'family_history', 'smoking')"
    )
    info_needed: List[Literal["eligibility", "intervals", "procedures", "followup"]] = Field(
        default=["eligibility", "intervals"],
        description="Information to retrieve"
    )


class IPACGuidanceRequest(BaseModel):
    """Request model for opa.ipac_guidance tool."""
    setting: Literal["clinic", "hospital", "community", "ltc"] = Field(
        ..., description="Healthcare setting"
    )
    topic: str = Field(..., description="IPAC topic (e.g., 'hand hygiene', 'PPE', 'sterilization')")
    pathogen: Optional[str] = Field(
        None, description="Specific pathogen if applicable"
    )
    include_checklists: bool = Field(
        default=True, description="Include practical checklists"
    )


class FreshnessProbeRequest(BaseModel):
    """Request model for opa.freshness_probe tool."""
    topic: str = Field(..., description="Topic to check for updates")
    current_date: Optional[str] = Field(
        None, description="Reference date for checking updates (YYYY-MM-DD)"
    )
    sources: Optional[List[str]] = Field(
        None, description="Specific sources to check for updates"
    )
    check_web: bool = Field(
        default=True, description="Check web for recent updates"
    )