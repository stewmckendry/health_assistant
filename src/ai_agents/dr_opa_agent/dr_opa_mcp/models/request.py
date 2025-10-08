"""
Request models for Dr. OPA MCP tools.
Defines the structure of incoming requests for each tool.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class StandardToolRequest(BaseModel):
    """
    Standardized request schema for all Dr. OPA MCP tools.

    This model provides a consistent interface across all tools with flexible filters.

    Attributes:
        query (str): The main search term or clinical question:
            - Clinical question: "prescribing opioids guidance", "hand hygiene protocol"
            - Policy topic: "telemedicine standards", "medical assistance in dying"
            - Screening program: "cervical cancer screening", "lung cancer screening"
            - Quality standard: "diabetes management", "hip fracture care"
            - Choosing Wisely: "unnecessary imaging for low back pain"

        k (int): Number of results to return (default: 10, range: 1-100)

        filters (Optional[Dict[str, Any]]): Tool-specific filters

            **opa_search_sections filters:**
            - sources (List[str]): Sources to search: ["cpso", "pho", "cep", "ontario_health"]
            - doc_types (List[str]): Document types: ["policy", "guideline", "tool", "standard"]
            - topics (List[str]): Topics to filter by (e.g., ["prescribing", "screening"])
            - date_range (Dict): Date filter: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
            - include_superseded (bool): Include superseded documents (default: false)

            **opa_policy_check filters:**
            - policy_level (str): CPSO policy level: "expectation", "advice", "both" (default: "both")
            - include_related (bool): Include related policies (default: true)

            **opa_program_lookup filters:**
            - patient_age (int): Patient age for eligibility
            - risk_factors (List[str]): Risk factors (e.g., ["smoking", "family_history"])
            - info_needed (List[str]): Info types: ["eligibility", "intervals", "procedures", "followup"]

            **opa_ipac_guidance filters:**
            - setting (str): Healthcare setting: "clinic", "hospital", "community", "ltc"
            - pathogen (str): Specific pathogen if applicable
            - include_checklists (bool): Include practical checklists (default: true)

            **opa_clinical_tools filters:**
            - tool_type (str): Tool category (e.g., "calculator", "algorithm")
            - feature_type (str): Clinical feature type
            - include_sections (bool): Include section summaries (default: false)

            **opa_quality_standards filters:**
            - retrieve_all_statements (bool): Get all statements for a standard (default: false)
            - statement_type (str): Content type: "overview", "statement", "all" (default: "all")

            **opa_choosing_wisely filters:**
            - specialty (str): Medical specialty (e.g., "Family Medicine", "Cardiology")
            - all_specialty_recommendations (bool): Return ALL specialty recommendations (default: false)
            - recommendation_type (str): Content type: "overview", "recommendation", "all" (default: "all")

    Examples:
        # Search for CPSO policies
        StandardToolRequest(
            query="prescribing opioids",
            k=10,
            filters={"sources": ["cpso"], "doc_types": ["policy", "advice"]}
        )

        # Quality standards for diabetes
        StandardToolRequest(
            query="diabetes",
            k=15,
            filters={"retrieve_all_statements": True, "statement_type": "all"}
        )

        # Choosing Wisely recommendations
        StandardToolRequest(
            query="imaging for low back pain",
            k=5,
            filters={"specialty": "Family Medicine"}
        )
    """
    query: str = Field(..., description="The search query or identifier")
    k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Tool-specific filters (see class docstring)")


