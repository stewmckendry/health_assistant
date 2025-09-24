"""
Response models for Dr. OFF MCP tools.
Defines the structure of responses from each tool.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation reference for a piece of information."""
    source: str = Field(..., description="Source document name")
    loc: str = Field(..., description="Location reference (e.g., section, code)")
    page: Optional[int] = Field(None, description="Page number if available")


class Highlight(BaseModel):
    """Key point with citations."""
    point: str = Field(..., description="Key information point")
    citations: List[Citation] = Field(..., description="Supporting citations")


class Conflict(BaseModel):
    """Conflict between SQL and vector evidence."""
    field: str = Field(..., description="Field with conflicting values")
    sql_value: Any = Field(..., description="Value from SQL source")
    vector_value: Any = Field(..., description="Value from vector source")
    resolution: str = Field(..., description="How conflict was resolved")


class FollowUp(BaseModel):
    """Follow-up question to clarify ambiguity."""
    ask: str = Field(..., description="Question to ask the user")
    reason: Optional[str] = Field(None, description="Why this information is needed")


class ToolTrace(BaseModel):
    """Record of a tool call made during processing."""
    tool: str = Field(..., description="Tool name that was called")
    args: Dict[str, Any] = Field(..., description="Arguments passed to the tool")
    duration_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if tool failed")


class CoverageAnswerResponse(BaseModel):
    """Response model for coverage.answer orchestrator."""
    decision: Literal["billable", "eligible", "covered", "needs_more_info"] = Field(
        ..., description="Primary decision/determination"
    )
    summary: str = Field(..., description="One-paragraph clinician-facing answer")
    provenance_summary: str = Field(
        ..., description="Data sources used (e.g., 'sql+vector')"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    highlights: List[Highlight] = Field(
        default_factory=list, description="Key points with citations"
    )
    conflicts: List[Conflict] = Field(
        default_factory=list, description="Conflicts between evidence sources"
    )
    followups: List[FollowUp] = Field(
        default_factory=list, description="Follow-up questions if needed"
    )
    trace: List[ToolTrace] = Field(
        default_factory=list, description="Tool calls made during processing"
    )


class ScheduleItem(BaseModel):
    """OHIP schedule fee item."""
    code: str = Field(..., description="Fee code")
    description: str = Field(..., description="Service description")
    fee: Optional[float] = Field(None, description="Fee amount")
    requirements: Optional[str] = Field(None, description="Billing requirements")
    limits: Optional[str] = Field(None, description="Service limits")
    page_num: Optional[int] = Field(None, description="Page number in schedule")


class ScheduleGetResponse(BaseModel):
    """Response model for schedule.get tool."""
    provenance: List[str] = Field(..., description="Data sources used ['sql', 'vector']")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    items: List[ScheduleItem] = Field(
        default_factory=list, description="Matching schedule items"
    )
    citations: List[Citation] = Field(
        default_factory=list, description="Source citations"
    )
    conflicts: List[Conflict] = Field(
        default_factory=list, description="Conflicts if any"
    )


class Eligibility(BaseModel):
    """ADP eligibility criteria."""
    basic_mobility: Optional[bool] = Field(None, description="Meets basic mobility need")
    ontario_resident: Optional[bool] = Field(None, description="Ontario resident status")
    valid_prescription: Optional[bool] = Field(None, description="Has valid prescription")
    other_criteria: Optional[Dict[str, bool]] = Field(
        None, description="Additional eligibility criteria"
    )


class Funding(BaseModel):
    """ADP funding details."""
    client_share_percent: float = Field(..., description="Client share percentage")
    adp_contribution: float = Field(..., description="ADP contribution percentage")
    max_contribution: Optional[float] = Field(None, description="Maximum ADP contribution")
    repair_coverage: Optional[str] = Field(None, description="Repair coverage details")


class CEPInfo(BaseModel):
    """Chronic Care Expansion Program information."""
    income_threshold: float = Field(..., description="Income threshold for eligibility")
    eligible: bool = Field(..., description="Whether patient is CEP eligible")
    client_share: float = Field(..., description="Client share under CEP (usually 0)")


class ADPGetResponse(BaseModel):
    """Response model for adp.get tool."""
    provenance: List[str] = Field(..., description="Data sources used")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    eligibility: Optional[Eligibility] = Field(None, description="Eligibility assessment")
    exclusions: List[str] = Field(
        default_factory=list, description="Applicable exclusions"
    )
    funding: Optional[Funding] = Field(None, description="Funding details")
    cep: Optional[CEPInfo] = Field(None, description="CEP eligibility information")
    citations: List[Citation] = Field(
        default_factory=list, description="Source citations"
    )
    conflicts: List[Conflict] = Field(
        default_factory=list, description="Conflicts if any"
    )


class DrugCoverage(BaseModel):
    """Drug coverage information."""
    covered: bool = Field(..., description="Whether drug is covered")
    din: str = Field(..., description="Drug Identification Number")
    brand_name: str = Field(..., description="Brand name")
    generic_name: str = Field(..., description="Generic/ingredient name")
    strength: str = Field(..., description="Drug strength")
    lu_required: bool = Field(..., description="Limited Use authorization required")
    lu_criteria: Optional[str] = Field(None, description="Limited Use criteria if applicable")


class InterchangeableDrug(BaseModel):
    """Interchangeable drug option."""
    din: str = Field(..., description="Drug Identification Number")
    brand: str = Field(..., description="Brand name")
    price: float = Field(..., description="Unit price")
    lowest_cost: bool = Field(..., description="Is this the lowest cost option")


class LowestCostDrug(BaseModel):
    """Lowest cost drug information."""
    din: str = Field(..., description="DIN of lowest cost option")
    brand: str = Field(..., description="Brand name")
    price: float = Field(..., description="Unit price")
    savings: float = Field(..., description="Savings vs requested drug")


class ODBGetResponse(BaseModel):
    """Response model for odb.get tool."""
    provenance: List[str] = Field(..., description="Data sources used")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    coverage: Optional[DrugCoverage] = Field(None, description="Coverage information")
    interchangeable: List[InterchangeableDrug] = Field(
        default_factory=list, description="Interchangeable alternatives"
    )
    lowest_cost: Optional[LowestCostDrug] = Field(
        None, description="Lowest cost option if available"
    )
    citations: List[Citation] = Field(
        default_factory=list, description="Source citations"
    )
    conflicts: List[Conflict] = Field(
        default_factory=list, description="Conflicts if any"
    )


class SourcePassage(BaseModel):
    """Retrieved source passage."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    text: str = Field(..., description="Passage text")
    source: str = Field(..., description="Source document")
    page: Optional[int] = Field(None, description="Page number")
    section: Optional[str] = Field(None, description="Section reference")
    highlights: Optional[List[str]] = Field(None, description="Highlighted terms")


class SourcePassagesResponse(BaseModel):
    """Response model for source.passages tool."""
    passages: List[SourcePassage] = Field(..., description="Retrieved passages")
    total_chunks: int = Field(..., description="Total number of chunks retrieved")