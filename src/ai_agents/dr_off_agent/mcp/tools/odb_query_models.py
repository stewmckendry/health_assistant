"""
Data models for ODB query understanding and processing.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class QueryModifiers(BaseModel):
    """Modifiers that affect query processing."""
    formulation: Optional[str] = Field(None, description="Specific formulation requested (e.g., 'extended release')")
    cost_focused: bool = Field(False, description="Query is focused on cost/pricing")
    authorization_focused: bool = Field(False, description="Query is about authorization/LU requirements")


class QueryIntent(BaseModel):
    """
    Structured representation of user's query intent.
    Extracted via LLM from natural language query.
    """
    query_type: Literal[
        "coverage",           # "Is X covered?"
        "alternatives",       # "alternatives to X"
        "lu_criteria",        # "what are LU requirements for X"
        "cost",              # "cheapest X" or "price of X"
        "class_search",      # "diabetes medications"
        "yes_no",            # "does X need authorization"
        "general"            # catch-all
    ] = Field(..., description="Type of query being asked")

    drug_names: List[str] = Field(
        default_factory=list,
        description="Explicit drug names mentioned (brand or generic)"
    )

    drug_classes: List[str] = Field(
        default_factory=list,
        description="Therapeutic drug classes mentioned"
    )

    clinical_terms: List[str] = Field(
        default_factory=list,
        description="Clinical terminology (e.g., 'GLP-1 agonist', 'ACE inhibitor')"
    )

    modifiers: QueryModifiers = Field(
        default_factory=QueryModifiers,
        description="Query modifiers"
    )

    expects_yes_no: bool = Field(
        False,
        description="User expects a yes/no answer"
    )

    context: Optional[str] = Field(
        None,
        description="Additional context (condition, indication, etc.)"
    )

    original_query: str = Field(..., description="Original user query")


class RetrievalResult(BaseModel):
    """Results from SQL + Vector retrieval."""
    sql_results: List[Dict[str, Any]] = Field(default_factory=list)
    vector_results: List[Dict[str, Any]] = Field(default_factory=list)
    sql_success: bool = Field(True)
    vector_success: bool = Field(True)


class LUCriteriaExtraction(BaseModel):
    """Extracted Limited Use criteria information."""
    lu_required: bool = Field(..., description="Whether LU authorization is required")
    criteria: Optional[str] = Field(None, description="Specific LU criteria in plain language")
    exceptions: List[str] = Field(default_factory=list, description="Exceptions to LU requirements")
    documentation_required: List[str] = Field(
        default_factory=list,
        description="Documentation physician must submit"
    )
    reference: Optional[str] = Field(None, description="Section of formulary referenced")


class YesNoAnswer(BaseModel):
    """Answer to yes/no question about coverage."""
    answer: Literal["yes", "no", "conditional"] = Field(..., description="Yes/no/conditional answer")
    explanation: str = Field(..., description="Brief explanation of answer")
    conditions: List[str] = Field(default_factory=list, description="Conditions or restrictions")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in answer")


class TherapeuticAlternative(BaseModel):
    """Information about a therapeutic alternative drug."""
    drug_name: str = Field(..., description="Generic drug name")
    brand_names: List[str] = Field(default_factory=list, description="Brand names")
    reason: str = Field(..., description="Why this is an alternative")
    covered: bool = Field(..., description="Whether covered by ODB")
    price: Optional[float] = Field(None, description="Unit price if available")
    din: Optional[str] = Field(None, description="Drug Identification Number")


class EnrichedResult(BaseModel):
    """
    Results after LLM enrichment.
    Contains structured information extracted from retrieval results.
    """
    intent: QueryIntent
    retrieval: RetrievalResult

    # Extracted structured data (populated based on query type)
    lu_criteria: Optional[LUCriteriaExtraction] = None
    yes_no_answer: Optional[YesNoAnswer] = None
    therapeutic_alternatives: List[TherapeuticAlternative] = Field(default_factory=list)
    coverage_explanation: Optional[str] = None

    # Metadata
    enrichment_method: Literal["sql_only", "vector_only", "llm_extraction", "hybrid"] = "hybrid"
    processing_notes: List[str] = Field(default_factory=list, description="Notes about processing")
