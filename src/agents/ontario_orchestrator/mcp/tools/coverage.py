"""
Coverage.answer orchestrator - main entry point for Dr. OFF queries.
Routes to appropriate domain tools and synthesizes responses.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime

from ..models.request import CoverageAnswerRequest
from ..models.response import (
    CoverageAnswerResponse,
    Highlight,
    Citation,
    Conflict,
    FollowUp,
    ToolTrace
)
from ..utils.confidence import ConfidenceAggregator
from ..utils.conflicts import ConflictDetector

# Import domain tools (will be implemented separately)
from .schedule import schedule_get
from .adp import adp_get
from .odb import odb_get

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Classify user intent from question text."""
    
    @staticmethod
    def classify(question: str, hints: Dict[str, Any]) -> str:
        """
        Classify the intent of a clinical question.
        
        Args:
            question: Free-text question
            hints: Optional hints from request
        
        Returns:
            Intent: 'billing', 'device', or 'drug'
        """
        question_lower = question.lower()
        
        # Check hints first
        if hints:
            if hints.get("codes"):
                return "billing"
            if hints.get("device"):
                return "device"
            if hints.get("drug"):
                return "drug"
        
        # Keywords for billing/OHIP
        billing_keywords = [
            "bill", "code", "fee", "ohip", "schedule", "mrp",
            "discharge", "consult", "visit", "premium", "c124"
        ]
        
        # Keywords for devices/ADP
        device_keywords = [
            "walker", "wheelchair", "scooter", "mobility", "device",
            "adp", "assistive", "cep", "repair", "battery", "aac"
        ]
        
        # Keywords for drugs/ODB
        drug_keywords = [
            "drug", "medication", "covered", "formulary", "odb",
            "prescription", "alternative", "generic", "ozempic",
            "januvia", "statin", "lu", "limited use"
        ]
        
        # Count keyword matches
        billing_score = sum(1 for kw in billing_keywords if kw in question_lower)
        device_score = sum(1 for kw in device_keywords if kw in question_lower)
        drug_score = sum(1 for kw in drug_keywords if kw in question_lower)
        
        # Return highest scoring intent
        if billing_score >= max(device_score, drug_score):
            return "billing"
        elif device_score >= drug_score:
            return "device"
        else:
            return "drug"


class QueryRouter:
    """Route queries to appropriate domain tools."""
    
    @staticmethod
    async def route_query(
        intent: str,
        request: CoverageAnswerRequest
    ) -> Dict[str, Dict[str, Any]]:
        """
        Route query to appropriate tools based on intent.
        
        Args:
            intent: Classified intent
            request: Original request
        
        Returns:
            Dictionary of tool results
        """
        results = {}
        tasks = []
        
        # Determine which tools to call
        if intent == "billing":
            # OHIP billing query
            if request.hints and request.hints.codes:
                tasks.append(("schedule.get", schedule_get({
                    "q": request.question,
                    "codes": request.hints.codes,
                    "include": ["codes", "fee", "limits", "documentation"],
                    "top_k": 6
                })))
            else:
                tasks.append(("schedule.get", schedule_get({
                    "q": request.question,
                    "include": ["codes", "fee", "limits", "documentation"],
                    "top_k": 6
                })))
            
            # Check if device also mentioned
            if request.hints and request.hints.device:
                tasks.append(("adp.get", adp_get({
                    "device": request.hints.device.dict(),
                    "check": ["eligibility", "funding"],
                    "patient_income": request.patient.income if request.patient else None
                })))
        
        elif intent == "device":
            # ADP device query
            if request.hints and request.hints.device:
                device_request = {
                    "device": request.hints.device.dict(),
                    "check": ["eligibility", "exclusions", "funding"],
                }
                
                # Add CEP check if income mentioned
                if request.patient and request.patient.income:
                    device_request["check"].append("cep")
                    device_request["patient_income"] = request.patient.income
                
                tasks.append(("adp.get", adp_get(device_request)))
        
        elif intent == "drug":
            # ODB drug query
            drug_name = None
            if request.hints and request.hints.drug:
                drug_name = request.hints.drug
            else:
                # Try to extract drug name from question
                drug_name = QueryRouter._extract_drug_name(request.question)
            
            if drug_name:
                tasks.append(("odb.get", odb_get({
                    "drug": drug_name,
                    "check_alternatives": "alternative" in request.question.lower(),
                    "include_lu": True,
                    "top_k": 5
                })))
        
        # Execute tools in parallel
        if tasks:
            tool_results = await asyncio.gather(
                *[task[1] for task in tasks],
                return_exceptions=True
            )
            
            for (tool_name, _), result in zip(tasks, tool_results):
                if isinstance(result, Exception):
                    logger.error(f"Tool {tool_name} failed: {result}")
                    results[tool_name] = {"error": str(result)}
                else:
                    results[tool_name] = result
        
        return results
    
    @staticmethod
    def _extract_drug_name(question: str) -> Optional[str]:
        """Extract drug name from question text."""
        # Common drug names (simplified - would use NER in production)
        common_drugs = [
            "januvia", "ozempic", "metformin", "lipitor", "crestor",
            "atorvastatin", "rosuvastatin", "sitagliptin", "empagliflozin"
        ]
        
        question_lower = question.lower()
        for drug in common_drugs:
            if drug in question_lower:
                return drug
        
        return None


class ResponseSynthesizer:
    """Synthesize final response from tool results."""
    
    @staticmethod
    def synthesize(
        intent: str,
        tool_results: Dict[str, Dict[str, Any]],
        request: CoverageAnswerRequest
    ) -> CoverageAnswerResponse:
        """
        Synthesize final response from tool results.
        
        Args:
            intent: Classified intent
            tool_results: Results from domain tools
            request: Original request
        
        Returns:
            Synthesized response
        """
        # Extract data from results
        highlights = []
        citations_seen = set()
        conflicts = []
        followups = []
        traces = []
        
        # Track provenance
        provenance_sources = set()
        confidence_scores = []
        
        # Process each tool result
        for tool_name, result in tool_results.items():
            if "error" in result:
                continue
            
            # Record trace
            traces.append(ToolTrace(
                tool=tool_name,
                args=ResponseSynthesizer._get_tool_args(tool_name, request),
                duration_ms=result.get("duration_ms")
            ))
            
            # Collect provenance
            if "provenance" in result:
                provenance_sources.update(result["provenance"])
            
            # Collect confidence scores
            if "confidence" in result:
                confidence_scores.append(result["confidence"])
            
            # Extract highlights based on tool type
            tool_highlights = ResponseSynthesizer._extract_highlights(
                tool_name, result
            )
            highlights.extend(tool_highlights)
            
            # Collect conflicts
            if "conflicts" in result:
                conflicts.extend(result["conflicts"])
        
        # Determine decision
        decision = ResponseSynthesizer._determine_decision(
            intent, tool_results, request
        )
        
        # Generate summary
        summary = ResponseSynthesizer._generate_summary(
            intent, tool_results, decision, request
        )
        
        # Calculate aggregate confidence
        confidence = ConfidenceAggregator.aggregate(confidence_scores) if confidence_scores else 0.5
        
        # Check if more info needed
        if decision == "needs_more_info":
            followups = ResponseSynthesizer._generate_followups(
                intent, tool_results, request
            )
        
        # Build provenance summary
        provenance_summary = "+".join(sorted(provenance_sources)) if provenance_sources else "none"
        
        return CoverageAnswerResponse(
            decision=decision,
            summary=summary,
            provenance_summary=provenance_summary,
            confidence=confidence,
            highlights=highlights,
            conflicts=conflicts,
            followups=followups,
            trace=traces
        )
    
    @staticmethod
    def _get_tool_args(tool_name: str, request: CoverageAnswerRequest) -> Dict[str, Any]:
        """Get the arguments that were passed to a tool."""
        # Reconstruct args based on tool and request
        if tool_name == "schedule.get":
            args = {"q": request.question}
            if request.hints and request.hints.codes:
                args["codes"] = request.hints.codes
        elif tool_name == "adp.get":
            args = {}
            if request.hints and request.hints.device:
                args["device"] = request.hints.device.dict()
        elif tool_name == "odb.get":
            args = {}
            if request.hints and request.hints.drug:
                args["drug"] = request.hints.drug
        else:
            args = {}
        
        return args
    
    @staticmethod
    def _extract_highlights(tool_name: str, result: Dict[str, Any]) -> List[Highlight]:
        """Extract highlights from tool result."""
        highlights = []
        
        if tool_name == "schedule.get" and "items" in result:
            for item in result["items"][:2]:  # Top 2 items
                highlight = Highlight(
                    point=f"{item['code']}: {item['description']} - ${item.get('fee', 'N/A')}",
                    citations=[Citation(
                        source="schedule_of_benefits.pdf",
                        loc=item['code'],
                        page=item.get('page_num')
                    )]
                )
                highlights.append(highlight)
        
        elif tool_name == "adp.get":
            if "funding" in result and result["funding"]:
                funding = result["funding"]
                highlight = Highlight(
                    point=f"ADP covers {funding['adp_contribution']}%, client pays {funding['client_share_percent']}%",
                    citations=result.get("citations", [])
                )
                highlights.append(highlight)
            
            if "cep" in result and result["cep"] and result["cep"]["eligible"]:
                highlight = Highlight(
                    point="CEP eligible - 100% coverage (no client share)",
                    citations=result.get("citations", [])
                )
                highlights.append(highlight)
        
        elif tool_name == "odb.get":
            if "coverage" in result and result["coverage"]:
                coverage = result["coverage"]
                point = f"{coverage['brand_name']} ({coverage['generic_name']}) is {'covered' if coverage['covered'] else 'not covered'}"
                if coverage.get("lu_required"):
                    point += " - Limited Use authorization required"
                
                highlight = Highlight(
                    point=point,
                    citations=result.get("citations", [])
                )
                highlights.append(highlight)
            
            if "lowest_cost" in result and result["lowest_cost"]:
                lowest = result["lowest_cost"]
                highlight = Highlight(
                    point=f"Lowest cost: {lowest['brand']} at ${lowest['price']:.2f} (saves ${lowest['savings']:.2f})",
                    citations=result.get("citations", [])
                )
                highlights.append(highlight)
        
        return highlights
    
    @staticmethod
    def _determine_decision(
        intent: str,
        tool_results: Dict[str, Dict[str, Any]],
        request: CoverageAnswerRequest
    ) -> Literal["billable", "eligible", "covered", "needs_more_info"]:
        """Determine the primary decision."""
        # Check for errors or empty results
        if not tool_results or all("error" in r for r in tool_results.values()):
            return "needs_more_info"
        
        # Intent-specific decision logic
        if intent == "billing":
            schedule_result = tool_results.get("schedule.get", {})
            if "items" in schedule_result and schedule_result["items"]:
                return "billable"
            else:
                return "needs_more_info"
        
        elif intent == "device":
            adp_result = tool_results.get("adp.get", {})
            if "eligibility" in adp_result:
                eligibility = adp_result["eligibility"]
                if eligibility and all(v for v in eligibility.values() if v is not None):
                    return "eligible"
            return "needs_more_info"
        
        elif intent == "drug":
            odb_result = tool_results.get("odb.get", {})
            if "coverage" in odb_result and odb_result["coverage"]:
                return "covered" if odb_result["coverage"]["covered"] else "needs_more_info"
            return "needs_more_info"
        
        return "needs_more_info"
    
    @staticmethod
    def _generate_summary(
        intent: str,
        tool_results: Dict[str, Dict[str, Any]],
        decision: str,
        request: CoverageAnswerRequest
    ) -> str:
        """Generate clinician-facing summary."""
        summaries = []
        
        # Add decision statement
        if decision == "billable":
            summaries.append("The requested service/code is billable under OHIP.")
        elif decision == "eligible":
            summaries.append("The patient is eligible for ADP funding.")
        elif decision == "covered":
            summaries.append("The medication is covered under ODB.")
        elif decision == "needs_more_info":
            summaries.append("Additional information is needed for a definitive answer.")
        
        # Add tool-specific details
        for tool_name, result in tool_results.items():
            if "error" in result:
                continue
            
            if tool_name == "schedule.get" and "items" in result:
                items = result["items"]
                if items:
                    item = items[0]
                    summaries.append(
                        f"Code {item['code']} ({item['description']}) "
                        f"has a fee of ${item.get('fee', 'N/A')}."
                    )
            
            elif tool_name == "adp.get":
                if "funding" in result and result["funding"]:
                    funding = result["funding"]
                    summaries.append(
                        f"ADP covers {funding['adp_contribution']}% "
                        f"with client paying {funding['client_share_percent']}%."
                    )
                if "cep" in result and result["cep"] and result["cep"]["eligible"]:
                    summaries.append("Patient qualifies for CEP (100% coverage).")
            
            elif tool_name == "odb.get":
                if "coverage" in result and result["coverage"]:
                    coverage = result["coverage"]
                    summaries.append(
                        f"{coverage['brand_name']} is {'covered' if coverage['covered'] else 'not covered'}."
                    )
                if "lowest_cost" in result and result["lowest_cost"]:
                    lowest = result["lowest_cost"]
                    summaries.append(
                        f"Consider {lowest['brand']} as lowest-cost alternative "
                        f"(saves ${lowest['savings']:.2f} per unit)."
                    )
        
        return " ".join(summaries)
    
    @staticmethod
    def _generate_followups(
        intent: str,
        tool_results: Dict[str, Dict[str, Any]],
        request: CoverageAnswerRequest
    ) -> List[FollowUp]:
        """Generate follow-up questions."""
        followups = []
        
        if intent == "billing":
            # Check if MRP status needed
            if not request.patient or not hasattr(request.patient, "mrp_status"):
                followups.append(FollowUp(
                    ask="Are you the Most Responsible Physician (MRP)?",
                    reason="MRP status affects billing eligibility for certain codes"
                ))
            
            # Check if length of stay needed
            if "discharge" in request.question.lower():
                followups.append(FollowUp(
                    ask="What was the exact length of stay (in hours)?",
                    reason="Length of stay determines applicable discharge codes"
                ))
        
        elif intent == "device":
            # Check if prescription available
            followups.append(FollowUp(
                ask="Does the patient have a valid prescription from an authorized prescriber?",
                reason="ADP requires valid prescription for funding"
            ))
        
        elif intent == "drug":
            # Check if tried alternatives
            followups.append(FollowUp(
                ask="Has the patient tried other first-line treatments?",
                reason="Some drugs require trial of alternatives for coverage"
            ))
        
        return followups


async def coverage_answer(request_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for coverage.answer tool.
    
    Args:
        request_dict: Request dictionary
    
    Returns:
        Response dictionary
    """
    try:
        # Parse request
        request = CoverageAnswerRequest(**request_dict)
        
        # Classify intent
        intent = request.intent or IntentClassifier.classify(
            request.question,
            request.hints.dict() if request.hints else {}
        )
        
        logger.info(f"Classified intent: {intent}")
        
        # Route to appropriate tools
        tool_results = await QueryRouter.route_query(intent, request)
        
        logger.info(f"Called {len(tool_results)} tools: {list(tool_results.keys())}")
        
        # Synthesize response
        response = ResponseSynthesizer.synthesize(intent, tool_results, request)
        
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in coverage_answer: {e}", exc_info=True)
        return {
            "decision": "needs_more_info",
            "summary": f"An error occurred processing your request: {str(e)}",
            "provenance_summary": "error",
            "confidence": 0.0,
            "highlights": [],
            "conflicts": [],
            "followups": [],
            "trace": []
        }