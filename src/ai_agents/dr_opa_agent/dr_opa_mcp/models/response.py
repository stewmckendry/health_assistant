"""
Response models for Dr. OPA MCP tools.
Defines the structure of responses from each tool.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class RetrievedItem(BaseModel):
    """Standardized retrieved item for evaluation and observability."""
    id: str = Field(..., description="Unique identifier (section_id, statement_id, recommendation_id)")
    text: str = Field(..., description="Full text content of this item")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to query")
    source: str = Field(..., description="Source identifier (document_id, policy_name)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata (heading, type, org, etc.)")


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
    """Document section with metadata - Option A minimal schema."""
    id: str = Field(..., description="Unique section identifier")
    text: str = Field(..., description="Section content (may be truncated)")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to query")
    source: str = Field(..., description="Parent document ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="All domain-specific fields (section_id, document_id, heading, chunk_type, etc.)")


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
    items: List[Section] = Field(..., description="Matching sections ranked by relevance")
    documents: List[Document] = Field(..., description="Unique documents containing matches")
    provenance: List[str] = Field(..., description="Data sources used ['sql', 'vector']")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    highlights: List[Highlight] = Field(default_factory=list, description="Key points from results")
    conflicts: List[Conflict] = Field(default_factory=list, description="Conflicts if any")
    query_interpretation: Optional[str] = Field(None, description="How the query was understood")


class GetSectionResponse(BaseModel):
    """Response model for opa.get_section tool."""
    items: List[Section] = Field(..., description="Requested section plus children/context")
    document: Document = Field(..., description="Parent document metadata")
    citations: List[Citation] = Field(..., description="Citations for the section")


class PolicyCheckResponse(BaseModel):
    """Response model for opa.policy_check tool."""
    items: List[Section] = Field(..., description="All retrieved items (use chunk_type to filter: expectation, advice, policy_document)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in completeness")
    summary: str = Field(..., description="Executive summary of guidance")
    suggestions: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Suggested alternatives when no exact match found"
    )
    no_exact_match: bool = Field(
        default=False,
        description="True if no exact matches found, suggestions provided instead"
    )


class ProgramLookupResponse(BaseModel):
    """Response model for opa.program_lookup tool - Option A minimal schema."""
    items: List[Section] = Field(default_factory=list, description="Retrieved web sources used to build response (web_search results)")
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
    items: List[Section] = Field(..., description="All retrieved guidance chunks (Option A minimal schema)")
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


class QualityStatement(BaseModel):
    """Individual quality statement from Ontario Health - Option A minimal schema."""
    id: str = Field(..., description="Unique identifier for the statement (standard_title:statement_number)")
    text: str = Field(..., description="Full statement text with background")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to query")
    source: str = Field(..., description="Quality standard document title")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="All domain-specific fields (statement_number, title, brief_statement, full_text, indicators, for_patients, for_clinicians)")


class QualityStandardsResponse(BaseModel):
    """Response model for opa.quality_standards tool."""
    standard_title: Optional[str] = Field(None, description="Quality standard title if specific standard found")
    items: List[QualityStatement] = Field(..., description="Quality statements matching query")
    total_statements: int = Field(..., description="Total number of statements in standard")
    executive_summary: Optional[str] = Field(None, description="Executive summary if available")
    scope: Optional[str] = Field(None, description="Scope of the standard")
    year: Optional[int] = Field(None, description="Year published")
    citations: List[Citation] = Field(..., description="Source citations")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in match")
    suggestions: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Suggested alternatives when no exact match found"
    )
    no_exact_match: bool = Field(
        default=False,
        description="True if no exact matches found, suggestions provided instead"
    )


class ChoosingWiselyRecommendation(BaseModel):
    """Individual Choosing Wisely recommendation - Option A minimal schema."""
    id: str = Field(..., description="Unique identifier for the recommendation (specialty_recnum)")
    text: str = Field(..., description="Full explanation and rationale")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance to query")
    source: str = Field(..., description="Medical specialty this applies to")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata (recommendation_number, title, organization, references)")


class ChoosingWiselyResponse(BaseModel):
    """Response model for opa.choosing_wisely tool."""
    specialty_title: Optional[str] = Field(None, description="Medical specialty if specific one found")
    items: List[ChoosingWiselyRecommendation] = Field(..., description="Choosing Wisely recommendations")
    total_recommendations: int = Field(..., description="Total recommendations found")
    specialty_overview: Optional[str] = Field(None, description="Overview of specialty's approach to unnecessary care")
    organization: Optional[str] = Field(None, description="Organization that published recommendations")
    last_updated: Optional[str] = Field(None, description="When recommendations were last updated")
    citations: List[Citation] = Field(..., description="Source citations")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in match")
    query_interpretation: Optional[str] = Field(None, description="How the query was interpreted")
    suggestions: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Suggested alternatives when no exact match found"
    )
    no_exact_match: bool = Field(
        default=False,
        description="True if no exact matches found, suggestions provided instead"
    )