"""
Request models for Dr. OFF MCP tools.
Defines the structure of incoming requests for each tool.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class StandardToolRequest(BaseModel):
    """
    Standardized request schema for all Dr. OFF MCP tools.

    This model provides a consistent interface across all tools with flexible filters.

    Attributes:
        query (str): The main search term or identifier:
            - Drug name: "metformin", "Lipitor 20mg"
            - OHIP code or description: "A007A", "minor assessment billing"
            - Device name: "wheelchair", "hearing aid", "CPAP machine"

        k (int): Number of results to return (default: 10, range: 1-100)

        filters (Optional[Dict[str, Any]]): Tool-specific filters

            **schedule.get filters:**
            - codes (List[str]): Specific OHIP codes to lookup (e.g., ["A007A", "A001"])
            - include (List[str]): Fields to include, options:
                ["codes", "fee", "limits", "documentation", "commentary"]
                Default: ["codes", "fee", "limits", "documentation"]

            **odb.get filters:**
            - check_alternatives (bool): Check for interchangeable drugs (default: true)
            - include_lu (bool): Include Limited Use criteria (default: true)
            - formulary_only (bool): Only show formulary drugs (default: false)

            **adp.get filters:**
            - device (Dict): Device specification with:
                - category (str): "mobility", "hearing_devices", "respiratory", etc.
                - type (str): Specific device type (e.g., "wheelchair", "hearing aid")
            - check (List[str]): Aspects to check, options:
                ["eligibility", "exclusions", "funding", "cep"]
                Default: ["eligibility", "exclusions", "funding"]
            - use_case (Dict): Device usage details:
                - daily (bool): Used daily
                - location (str): Usage locations (e.g., "home+entry_exit")
                - independent_transfer (bool): Can transfer independently
            - patient_income (float): Patient income for CEP eligibility check

    Examples:
        # OHIP Schedule lookup
        StandardToolRequest(
            query="minor assessment",
            k=5,
            filters={"codes": ["A007A"], "include": ["fee", "limits"]}
        )

        # ODB drug lookup
        StandardToolRequest(
            query="metformin",
            k=10,
            filters={"check_alternatives": True, "include_lu": True}
        )

        # ADP device lookup
        StandardToolRequest(
            query="wheelchair for home use",
            k=5,
            filters={
                "device": {"category": "mobility", "type": "wheelchair"},
                "check": ["eligibility", "funding"],
                "use_case": {"daily": True, "location": "home"}
            }
        )
    """
    query: str = Field(..., description="The search query or identifier")
    k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Tool-specific filters (see class docstring)")


# Legacy request models deleted - use StandardToolRequest only