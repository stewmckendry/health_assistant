"""
Data models for OHIP Schedule query understanding and processing.

Adapted from ODB query processor pattern for OHIP billing codes and fees.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class QueryModifiers(BaseModel):
    """Modifiers that affect billing query processing."""
    time_based: bool = Field(False, description="Query involves time/date considerations")
    eligibility_focused: bool = Field(False, description="Query is about billing eligibility")
    cost_focused: bool = Field(False, description="Query is about fees/pricing")
    location_specific: bool = Field(False, description="Query mentions specific location (ER, LTC, office)")


class BillingQueryIntent(BaseModel):
    """
    Structured representation of clinician's billing query intent.
    Extracted via LLM from natural language query.
    """
    query_type: Literal[
        "code_lookup",        # "What is code K013?"
        "service_discovery",  # "house call billing codes"
        "eligibility_check",  # "Can I bill X as MRP?"
        "fee_inquiry",        # "How much for consultation?"
        "specialty_search",   # "internist ER consultation"
        "premium_modifier",   # "What premiums apply?"
        "yes_no",            # "Can I bill this?"
        "general"            # catch-all
    ] = Field(..., description="Type of billing query")

    billing_codes: List[str] = Field(
        default_factory=list,
        description="Explicit OHIP fee codes mentioned (e.g., 'C124', 'K013')"
    )

    service_types: List[str] = Field(
        default_factory=list,
        description="Service types mentioned (e.g., 'consultation', 'house call', 'discharge')"
    )

    clinical_terms: List[str] = Field(
        default_factory=list,
        description="Clinical/billing terminology (e.g., 'MRP', 'comprehensive geriatric assessment')"
    )

    specialty: Optional[str] = Field(
        None,
        description="Medical specialty mentioned (e.g., 'internist', 'family practice', 'surgery')"
    )

    location: Optional[str] = Field(
        None,
        description="Care location (e.g., 'ER', 'emergency', 'long-term care', 'LTC', 'office', 'hospital')"
    )

    modifiers: QueryModifiers = Field(
        default_factory=QueryModifiers,
        description="Query modifiers"
    )

    expects_yes_no: bool = Field(
        False,
        description="User expects a yes/no answer"
    )

    time_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Time-related context (admission/discharge times, duration, etc.)"
    )

    patient_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Patient context (age, condition, admission length, etc.)"
    )

    original_query: str = Field(..., description="Original user query")


class RetrievalResult(BaseModel):
    """Results from SQL + Vector retrieval."""
    sql_results: List[Dict[str, Any]] = Field(default_factory=list)
    vector_results: List[Dict[str, Any]] = Field(default_factory=list)
    sql_success: bool = Field(True)
    vector_success: bool = Field(True)


class BillingEligibility(BaseModel):
    """Extracted billing eligibility information."""
    code: str = Field(..., description="OHIP fee code")
    eligible: bool = Field(..., description="Whether billing is allowed for this scenario")
    explanation: str = Field(..., description="Clear explanation of eligibility")
    requirements: List[str] = Field(
        default_factory=list,
        description="Requirements to bill this code (e.g., 'Must be MRP', 'Requires 3-day admission')"
    )
    exclusions: List[str] = Field(
        default_factory=list,
        description="Situations where billing is not allowed"
    )
    documentation_required: List[str] = Field(
        default_factory=list,
        description="Documentation physician must provide"
    )
    specialty_restrictions: Optional[str] = Field(
        None,
        description="Specialty-specific restrictions"
    )
    time_requirements: Optional[str] = Field(
        None,
        description="Time-based requirements (e.g., 'After 48 hours', 'Same-day billing')"
    )
    reference: Optional[str] = Field(
        None,
        description="Section of OHIP schedule referenced"
    )


class YesNoAnswer(BaseModel):
    """Answer to yes/no question about billing eligibility."""
    answer: Literal["yes", "no", "conditional"] = Field(..., description="Yes/no/conditional answer")
    explanation: str = Field(..., description="Brief explanation of answer")
    conditions: List[str] = Field(
        default_factory=list,
        description="Conditions or restrictions for billing"
    )
    applicable_codes: List[str] = Field(
        default_factory=list,
        description="Relevant OHIP codes"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in answer")


class PremiumModifier(BaseModel):
    """Information about applicable premiums or modifiers."""
    code: str = Field(..., description="Premium/modifier code")
    description: str = Field(..., description="What this premium is for")
    amount: Optional[float] = Field(None, description="Premium amount")
    eligibility: str = Field(..., description="When this premium applies")


class EnrichedBillingResult(BaseModel):
    """
    Results after LLM enrichment.
    Contains structured billing information extracted from retrieval results.
    """
    intent: BillingQueryIntent
    retrieval: RetrievalResult

    # Extracted structured data (populated based on query type)
    eligibility: Optional[BillingEligibility] = None
    yes_no_answer: Optional[YesNoAnswer] = None
    premiums: List[PremiumModifier] = Field(default_factory=list)
    billing_explanation: Optional[str] = None

    # Metadata
    enrichment_method: Literal["sql_only", "vector_only", "llm_extraction", "hybrid"] = "hybrid"
    processing_notes: List[str] = Field(
        default_factory=list,
        description="Notes about query processing"
    )
