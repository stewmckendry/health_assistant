"""
Response models for Dr. OPA MCP tools.
Defines the structure of responses from each tool.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation reference for a piece of information."""
    source: str = Field(..., description="Source document name")
    source_org: str = Field(..., description="Organization (e.g., 'cpso', 'ontario_health')")
    loc: str = Field(..., description="Location reference (e.g., section, paragraph)")
    page: Optional[int] = Field(None, description="Page number if available")
    url: Optional[str] = Field(None, description="Source URL if available")


class Highlight(BaseModel):
    """Key point with citations."""
    point: str = Field(..., description="Key information point")
    citations: List[Citation] = Field(..., description="Supporting citations")
    policy_level: Optional[Literal["expectation", "advice"]] = Field(
        None, description="CPSO policy level if applicable"
    )


class Conflict(BaseModel):
    """Conflict between different sources or versions."""
    field: str = Field(..., description="Topic or field with conflict")
    source1: Dict[str, Any] = Field(..., description="First source information")
    source2: Dict[str, Any] = Field(..., description="Second source information")
    resolution: str = Field(..., description="How conflict was resolved (e.g., 'newer date preferred')")


class Update(BaseModel):
    """Recent update or change information."""
    topic: str = Field(..., description="Topic that was updated")
    date: str = Field(..., description="Date of update")
    source: str = Field(..., description="Source of update")
    summary: str = Field(..., description="Summary of changes")
    url: Optional[str] = Field(None, description="Link to updated guidance")


class Section(BaseModel):
    """Document section with metadata."""
    section_id: str = Field(..., description="Unique section identifier")
    document_id: str = Field(..., description="Parent document ID")
    heading: str = Field(..., description="Section heading")
    text: str = Field(..., description="Section content (may be truncated)")
    chunk_type: Literal["parent", "child"] = Field(..., description="Chunk hierarchy level")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to query")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Document(BaseModel):
    """Document metadata and summary."""
    document_id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., description="Document title")
    source_org: str = Field(..., description="Source organization")
    document_type: str = Field(..., description="Document type (policy, advice, etc.)")
    effective_date: Optional[str] = Field(None, description="Effective date")
    topics: List[str] = Field(default_factory=list, description="Document topics")
    url: Optional[str] = Field(None, description="Source URL")
    is_superseded: bool = Field(default=False, description="Whether document is superseded")


class SearchSectionsResponse(BaseModel):
    """Response model for opa.search_sections tool."""
    sections: List[Section] = Field(..., description="Matching sections ranked by relevance")
    documents: List[Document] = Field(..., description="Unique documents containing matches")
    provenance: List[str] = Field(..., description="Data sources used ['sql', 'vector']")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    highlights: List[Highlight] = Field(default_factory=list, description="Key points from results")
    conflicts: List[Conflict] = Field(default_factory=list, description="Conflicts if any")
    query_interpretation: Optional[str] = Field(None, description="How the query was understood")


class GetSectionResponse(BaseModel):
    """Response model for opa.get_section tool."""
    section: Section = Field(..., description="Requested section with full content")
    document: Document = Field(..., description="Parent document metadata")
    children: List[Section] = Field(default_factory=list, description="Child chunks if requested")
    context: List[Section] = Field(default_factory=list, description="Surrounding sections if requested")
    citations: List[Citation] = Field(..., description="Citations for the section")


class PolicyCheckResponse(BaseModel):
    """Response model for opa.policy_check tool."""
    policies: List[Document] = Field(..., description="Relevant CPSO policies")
    expectations: List[Highlight] = Field(default_factory=list, description="Must-meet expectations")
    advice: List[Highlight] = Field(default_factory=list, description="Advice to profession")
    related: List[Document] = Field(default_factory=list, description="Related documents")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in completeness")
    summary: str = Field(..., description="Executive summary of guidance")


class ProgramLookupResponse(BaseModel):
    """Response model for opa.program_lookup tool."""
    program: str = Field(..., description="Clinical program name")
    eligibility: Dict[str, Any] = Field(..., description="Eligibility criteria")
    intervals: Dict[str, str] = Field(..., description="Screening/treatment intervals")
    procedures: List[str] = Field(default_factory=list, description="Clinical procedures and services")
    followup: Dict[str, Any] = Field(default_factory=dict, description="Follow-up protocols")
    patient_specific: Optional[Dict[str, Any]] = Field(
        None, description="Patient-specific recommendations if age/risks provided"
    )
    citations: List[Citation] = Field(..., description="Supporting citations")
    last_updated: Optional[str] = Field(None, description="Last update date of guidelines")
    additional_info: Optional[Dict[str, Any]] = Field(
        None, description="Additional program information (locations, resources, overview)"
    )


class IPACGuidanceResponse(BaseModel):
    """Response model for opa.ipac_guidance tool."""
    setting: str = Field(..., description="Healthcare setting")
    topic: str = Field(..., description="IPAC topic addressed")
    guidelines: List[Highlight] = Field(..., description="Key IPAC guidelines")
    procedures: List[Dict[str, Any]] = Field(default_factory=list, description="Step-by-step procedures")
    checklists: List[Dict[str, Any]] = Field(default_factory=list, description="Practical checklists")
    pathogen_specific: Optional[Dict[str, Any]] = Field(
        None, description="Pathogen-specific guidance if applicable"
    )
    citations: List[Citation] = Field(..., description="PHO and other citations")
    resources: List[Dict[str, str]] = Field(default_factory=list, description="Additional resources")


class FreshnessProbeResponse(BaseModel):
    """Response model for opa.freshness_probe tool."""
    topic: str = Field(..., description="Topic checked")
    current_guidance: Document = Field(..., description="Current guidance in corpus")
    last_updated: str = Field(..., description="Last update date in corpus")
    updates_found: bool = Field(..., description="Whether newer updates were found")
    recent_updates: List[Update] = Field(default_factory=list, description="Recent updates if found")
    recommended_action: str = Field(..., description="Recommended action (e.g., 'corpus is current')")
    web_sources_checked: List[str] = Field(default_factory=list, description="Web sources checked")