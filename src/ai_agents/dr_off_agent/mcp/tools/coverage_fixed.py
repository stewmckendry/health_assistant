"""
Fixed Coverage.answer orchestrator - main entry point for Dr. OFF queries.
Routes to appropriate domain tools and synthesizes responses.
Fixes:
1. Multi-domain routing (detects multiple intents)
2. Returns expected response format (answer, tools_used, evidence)
3. Better intent classification
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from ..models.request import CoverageAnswerRequest
from ..models.response import (
    Citation,
    Conflict,
)

# Import domain tools
from .schedule import schedule_get
from .adp import adp_get
from .odb import odb_get

logger = logging.getLogger(__name__)


class MultiIntentClassifier:
    """Classify multiple intents from question text."""
    
    @staticmethod
    def classify(question: str, context: Dict[str, Any] = None) -> Set[str]:
        """
        Classify ALL intents in a clinical question.
        
        Args:
            question: Free-text question
            context: Optional context from request
        
        Returns:
            Set of intents: {'billing', 'device', 'drug'}
        """
        question_lower = question.lower()
        intents = set()
        
        # Keywords for billing/OHIP
        billing_keywords = [
            "bill", "code", "fee", "ohip", "schedule", "mrp",
            "discharge", "consult", "visit", "premium", "c124",
            "a135", "a935", "b998"
        ]
        
        # Keywords for devices/ADP
        device_keywords = [
            "walker", "wheelchair", "scooter", "mobility", "device",
            "adp", "assistive", "cep", "repair", "battery", "aac",
            "equipment", "covered"
        ]
        
        # Keywords for drugs/ODB
        drug_keywords = [
            "drug", "medication", "formulary", "odb",
            "prescription", "alternative", "generic", "ozempic",
            "januvia", "statin", "metformin", "jardiance",
            "lu", "limited use"
        ]
        
        # Check for each domain
        if any(kw in question_lower for kw in billing_keywords):
            intents.add("billing")
        
        if any(kw in question_lower for kw in device_keywords):
            # Special check: "what's covered" alone might be billing
            if not ("covered" in question_lower and len(intents) > 0):
                intents.add("device")
        
        if any(kw in question_lower for kw in drug_keywords):
            intents.add("drug")
        
        # Default to billing if no clear intent
        if not intents:
            intents.add("billing")
        
        return intents


class ImprovedQueryRouter:
    """Route queries to ALL appropriate domain tools."""
    
    @staticmethod
    async def route_query(
        intents: Set[str],
        request: CoverageAnswerRequest
    ) -> Dict[str, Dict[str, Any]]:
        """
        Route query to ALL appropriate tools based on multiple intents.
        
        Args:
            intents: Set of classified intents
            request: Original request
        
        Returns:
            Dictionary of tool results
        """
        results = {}
        tasks = []
        
        # Add billing tool if needed
        if "billing" in intents:
            # Extract potential codes from question
            codes = ImprovedQueryRouter._extract_codes(request.question)
            if codes:
                tasks.append(("schedule.get", schedule_get({
                    "q": request.question,
                    "codes": codes,
                    "include": ["codes", "fee", "limits", "documentation"],
                    "top_k": 6
                })))
            else:
                tasks.append(("schedule.get", schedule_get({
                    "q": request.question,
                    "include": ["codes", "fee", "limits", "documentation"],
                    "top_k": 6
                })))
        
        # Add device tool if needed
        if "device" in intents:
            # Extract device type from question
            device = ImprovedQueryRouter._extract_device(request.question)
            if device:
                device_request = {
                    "device": device,
                    "check": ["eligibility", "exclusions", "funding", "cep"]
                }
                
                # Add income if available
                if hasattr(request, 'context') and request.context:
                    if request.context.get('patient_income'):
                        device_request["patient_income"] = request.context['patient_income']
                
                tasks.append(("adp.get", adp_get(device_request)))
        
        # Add drug tool if needed
        if "drug" in intents:
            drug_name = ImprovedQueryRouter._extract_drug_name(request.question)
            if drug_name:
                tasks.append(("odb.get", odb_get({
                    "drug": drug_name,
                    "check_alternatives": "alternative" in request.question.lower() or "cheaper" in request.question.lower(),
                    "include_lu": True,
                    "top_k": 5
                })))
        
        # Execute tools in parallel
        if tasks:
            start_time = datetime.now()
            tool_results = await asyncio.gather(
                *[task[1] for task in tasks],
                return_exceptions=True
            )
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            for (tool_name, _), result in zip(tasks, tool_results):
                if isinstance(result, Exception):
                    logger.error(f"Tool {tool_name} failed: {result}")
                    results[tool_name] = {"error": str(result)}
                else:
                    result["duration_ms"] = duration / len(tasks)  # Approximate
                    results[tool_name] = result
        
        return results
    
    @staticmethod
    def _extract_codes(question: str) -> List[str]:
        """Extract OHIP codes from question."""
        codes = []
        # Look for patterns like C124, A135, etc.
        import re
        pattern = r'\b[A-Z]\d{3,4}\b'
        matches = re.findall(pattern, question.upper())
        return matches
    
    @staticmethod
    def _extract_device(question: str) -> Dict[str, str]:
        """Extract device type from question."""
        question_lower = question.lower()
        
        # Map keywords to device specs
        if "walker" in question_lower:
            return {"category": "mobility", "type": "walker"}
        elif "wheelchair" in question_lower:
            if "power" in question_lower or "electric" in question_lower:
                return {"category": "mobility", "type": "power_wheelchair"}
            else:
                return {"category": "mobility", "type": "manual_wheelchair"}
        elif "scooter" in question_lower:
            return {"category": "mobility", "type": "power_scooter"}
        elif "battery" in question_lower or "batteries" in question_lower:
            return {"category": "mobility", "type": "scooter_batteries"}
        
        # Default mobility device
        return {"category": "mobility", "type": "mobility_aid"}
    
    @staticmethod
    def _extract_drug_name(question: str) -> Optional[str]:
        """Extract drug name from question text."""
        question_lower = question.lower()
        
        # Common drug names
        drugs = [
            "januvia", "ozempic", "metformin", "lipitor", "crestor",
            "jardiance", "insulin", "advil", "tylenol", "aspirin",
            "atorvastatin", "rosuvastatin", "sitagliptin"
        ]
        
        for drug in drugs:
            if drug in question_lower:
                return drug.capitalize()
        
        return None


class ImprovedResponseSynthesizer:
    """Synthesize response in expected format."""
    
    @staticmethod
    def synthesize(
        intents: Set[str],
        tool_results: Dict[str, Dict[str, Any]],
        request: CoverageAnswerRequest
    ) -> Dict[str, Any]:
        """
        Synthesize response with expected fields.
        
        Returns dict with:
        - answer: Natural language response
        - tools_used: List of tools called
        - confidence: Aggregate confidence
        - evidence: List of evidence items
        - provenance: List of data sources
        """
        # Build answer from tool results
        answer_parts = []
        evidence = []
        all_citations = []
        confidence_scores = []
        provenance = []
        
        # Process schedule.get results
        if "schedule.get" in tool_results:
            result = tool_results["schedule.get"]
            if "error" not in result:
                if result.get("provenance"):
                    provenance.extend(result["provenance"])
                if result.get("confidence"):
                    confidence_scores.append(result["confidence"])
                
                if result.get("items"):
                    # Add billing answer
                    items = result["items"]
                    if items:
                        answer_parts.append(f"For billing, I found the following codes:")
                        for item in items[:3]:
                            answer_parts.append(
                                f"• {item['code']}: {item['description']} - ${item.get('fee', 'N/A')}"
                            )
                            evidence.append({
                                "type": "billing_code",
                                "data": item
                            })
        
        # Process adp.get results
        if "adp.get" in tool_results:
            result = tool_results["adp.get"]
            if "error" not in result:
                if result.get("provenance"):
                    provenance.extend(result["provenance"])
                if result.get("confidence"):
                    confidence_scores.append(result["confidence"])
                
                if result.get("funding"):
                    funding = result["funding"]
                    answer_parts.append(
                        f"\nFor device coverage, ADP covers {funding.get('adp_contribution', 0)}% "
                        f"and the client pays {funding.get('client_share_percent', 0)}%."
                    )
                    evidence.append({
                        "type": "device_funding",
                        "data": funding
                    })
                
                if result.get("cep") and result["cep"].get("eligible"):
                    answer_parts.append(
                        f"The patient is eligible for CEP (100% coverage) with income below "
                        f"${result['cep']['income_threshold']}."
                    )
                    evidence.append({
                        "type": "cep_eligibility",
                        "data": result["cep"]
                    })
        
        # Process odb.get results  
        if "odb.get" in tool_results:
            result = tool_results["odb.get"]
            if "error" not in result:
                if result.get("provenance"):
                    provenance.extend(result["provenance"])
                if result.get("confidence"):
                    confidence_scores.append(result["confidence"])
                
                if result.get("coverage"):
                    coverage = result["coverage"]
                    drug_name = coverage.get("generic_name") or coverage.get("brand_name") or "The drug"
                    answer_parts.append(
                        f"\n{drug_name} is {'covered' if coverage.get('covered') else 'not covered'} "
                        f"under ODB (DIN: {coverage.get('din', 'N/A')})."
                    )
                    if coverage.get("lu_required"):
                        answer_parts.append("Note: Limited Use criteria apply.")
                    evidence.append({
                        "type": "drug_coverage",
                        "data": coverage
                    })
        
        # Build final response
        answer = " ".join(answer_parts) if answer_parts else "I couldn't find specific information for your query."
        
        # Calculate aggregate confidence
        confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        return {
            "answer": answer,
            "tools_used": list(tool_results.keys()),
            "confidence": confidence,
            "evidence": evidence,
            "provenance": list(set(provenance)),
            "include_sources": request.include_sources if hasattr(request, 'include_sources') else False
        }


async def coverage_answer(request_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fixed main entry point for coverage.answer tool.
    
    Args:
        request_dict: Request dictionary with 'question' and optional 'context'
    
    Returns:
        Response dictionary with answer, tools_used, confidence, evidence
    """
    try:
        # Handle both old and new request formats
        if "question" in request_dict:
            question = request_dict["question"]
        else:
            # Fallback to first string value
            question = next((v for v in request_dict.values() if isinstance(v, str)), "")
        
        # Create request object (handle missing model gracefully)
        request = type('Request', (), {
            'question': question,
            'context': request_dict.get('context', {}),
            'include_sources': request_dict.get('include_sources', False)
        })()
        
        # Classify ALL intents (multi-domain)
        intents = MultiIntentClassifier.classify(question, request.context)
        logger.info(f"Classified intents: {intents}")
        
        # Route to ALL appropriate tools
        tool_results = await ImprovedQueryRouter.route_query(intents, request)
        logger.info(f"Called {len(tool_results)} tools: {list(tool_results.keys())}")
        
        # Synthesize response in expected format
        response = ImprovedResponseSynthesizer.synthesize(intents, tool_results, request)
        
        return response
        
    except Exception as e:
        logger.error(f"Error in coverage_answer: {e}", exc_info=True)
        return {
            "answer": f"An error occurred processing your request: {str(e)}",
            "tools_used": [],
            "confidence": 0.0,
            "evidence": [],
            "provenance": [],
            "error": str(e)
        }