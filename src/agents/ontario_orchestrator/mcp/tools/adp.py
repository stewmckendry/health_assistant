"""
ADP (Assistive Devices Program) dual-path retrieval tool.
Always runs SQL and vector search in parallel for device funding queries.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.request import ADPGetRequest
from ..models.response import (
    ADPGetResponse,
    Eligibility,
    Funding,
    CEPInfo,
    Citation,
    Conflict
)
from ..retrieval import SQLClient, VectorClient
from ..utils import ConfidenceScorer, ConflictDetector

logger = logging.getLogger(__name__)

# CEP income thresholds (2024 values)
CEP_THRESHOLDS = {
    "single": 28000,
    "family": 39000
}


class ADPTool:
    """
    ADP device funding tool with dual-path execution.
    Always runs SQL and vector queries in parallel.
    """
    
    def __init__(
        self,
        sql_client: Optional[SQLClient] = None,
        vector_client: Optional[VectorClient] = None
    ):
        """
        Initialize ADP tool with retrieval clients.
        
        Args:
            sql_client: SQL client instance (creates default if None)
            vector_client: Vector client instance (creates default if None)
        """
        self.sql_client = sql_client or SQLClient(db_path="data/ohip.db", timeout_ms=500)
        self.vector_client = vector_client or VectorClient(persist_directory="data/processed/dr_off/chroma", timeout_ms=1000)
        self.confidence_scorer = ConfidenceScorer()
        self.conflict_detector = ConflictDetector()
        
        logger.info("ADP tool initialized with dual-path retrieval")
    
    async def execute(self, request: ADPGetRequest) -> ADPGetResponse:
        """
        Execute ADP query with dual-path retrieval.
        
        Args:
            request: ADPGetRequest with device and use case details
            
        Returns:
            ADPGetResponse with eligibility, funding, and citations
        """
        start_time = datetime.now()
        
        # Always run SQL and vector in parallel
        sql_task = self._sql_query(request)
        vector_task = self._vector_search(request)
        
        sql_result, vector_result = await asyncio.gather(
            sql_task,
            vector_task,
            return_exceptions=True
        )
        
        # Track which sources succeeded
        provenance = []
        if not isinstance(sql_result, Exception):
            provenance.append("sql")
        else:
            logger.warning(f"SQL query failed: {sql_result}")
            sql_result = {"funding": [], "exclusions": []}
            
        if not isinstance(vector_result, Exception):
            provenance.append("vector")
        else:
            logger.warning(f"Vector search failed: {vector_result}")
            vector_result = []
        
        # Process results based on what was requested
        eligibility = None
        exclusions = []
        funding = None
        cep = None
        citations = []
        conflicts = []
        
        if "eligibility" in request.check:
            eligibility = await self._assess_eligibility(sql_result, vector_result, request)
        
        if "exclusions" in request.check:
            exclusions = await self._check_exclusions(sql_result, vector_result, request)
        
        if "funding" in request.check:
            funding, funding_conflicts = await self._determine_funding(sql_result, vector_result, request)
            conflicts.extend(funding_conflicts)
        
        if "cep" in request.check:
            cep = await self._check_cep(sql_result, vector_result, request)
        
        # Extract citations from vector results
        citations = self._extract_citations(vector_result)
        
        # Calculate confidence
        sql_hits = len(sql_result) if not isinstance(sql_result, Exception) and "sql" in provenance else 0
        vector_hits = len(vector_result) if not isinstance(vector_result, Exception) and "vector" in provenance else 0
        
        confidence = self.confidence_scorer.calculate(
            sql_hits=sql_hits,
            vector_matches=vector_hits,
            has_conflict=len(conflicts) > 0
        )
        
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"ADP query completed in {elapsed_ms:.1f}ms: confidence={confidence:.2f}")
        
        return ADPGetResponse(
            provenance=provenance,
            confidence=confidence,
            eligibility=eligibility,
            exclusions=exclusions,
            funding=funding,
            cep=cep,
            citations=citations,
            conflicts=conflicts
        )
    
    async def _sql_query(self, request: ADPGetRequest) -> Dict[str, Any]:
        """
        Execute SQL queries for ADP funding and exclusions.
        
        Args:
            request: ADP request parameters
            
        Returns:
            Dictionary with funding and exclusion results
        """
        try:
            # Build device search term
            device_search = f"{request.device.category} {request.device.type}"
            
            # Run funding and exclusion queries in parallel
            funding_task = self.sql_client.query_adp_funding(
                device_category=request.device.category,
                scenario_search=request.device.type
            )
            
            exclusion_task = self.sql_client.query_adp_exclusions(
                search_term=request.device.type
            )
            
            funding_results, exclusion_results = await asyncio.gather(
                funding_task,
                exclusion_task,
                return_exceptions=True
            )
            
            # Handle any errors in sub-queries
            if isinstance(funding_results, Exception):
                logger.warning(f"Funding query failed: {funding_results}")
                funding_results = []
            
            if isinstance(exclusion_results, Exception):
                logger.warning(f"Exclusion query failed: {exclusion_results}")
                exclusion_results = []
            
            logger.debug(f"SQL: {len(funding_results)} funding rules, {len(exclusion_results)} exclusions")
            
            return {
                "funding": funding_results,
                "exclusions": exclusion_results
            }
            
        except asyncio.TimeoutError:
            logger.warning("SQL queries timed out")
            raise
        except Exception as e:
            logger.error(f"SQL query error: {e}")
            raise
    
    async def _vector_search(self, request: ADPGetRequest) -> List[Dict[str, Any]]:
        """
        Execute vector search for ADP manual context.
        
        Args:
            request: ADP request parameters
            
        Returns:
            List of vector search results
        """
        try:
            # Build comprehensive search query
            query_parts = [
                request.device.type,
                request.device.category
            ]
            
            # Add use case context if provided
            if request.use_case:
                if request.use_case.daily:
                    query_parts.append("daily use")
                if request.use_case.location:
                    query_parts.append(request.use_case.location)
                if request.use_case.independent_transfer is False:
                    query_parts.append("cannot transfer independently")
            
            # Add specific check types to query
            if "cep" in request.check:
                query_parts.append("CEP client eligibility program")
            if "funding" in request.check:
                query_parts.append("funding percentage coverage")
            
            search_query = " ".join(query_parts)
            
            # Search ADP manual chunks
            results = await self.vector_client.search_adp(
                query=search_query,
                device_category=request.device.category,
                n_results=8  # Get more results for comprehensive context
            )
            
            logger.debug(f"Vector search returned {len(results)} ADP chunks")
            return results
            
        except asyncio.TimeoutError:
            logger.warning("Vector search timed out")
            raise
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            raise
    
    async def _assess_eligibility(
        self,
        sql_result: Dict[str, Any],
        vector_results: List[Dict[str, Any]],
        request: ADPGetRequest
    ) -> Optional[Eligibility]:
        """
        Assess device eligibility based on SQL and vector evidence.
        
        Returns:
            Eligibility assessment or None
        """
        # Check exclusions first
        exclusions = sql_result.get("exclusions", [])
        device_type = request.device.type.lower()
        
        # Check if device or component is excluded
        for exclusion in exclusions:
            phrase = exclusion.get("phrase", "").lower()
            if phrase in device_type:
                # Device is explicitly excluded
                return Eligibility(
                    basic_mobility=False,
                    ontario_resident=None,
                    valid_prescription=None,
                    other_criteria={"excluded": True}
                )
        
        # Extract eligibility criteria from vector results
        criteria = {
            "basic_mobility": None,
            "ontario_resident": None,
            "valid_prescription": None,
            "car_substitute": None
        }
        
        for vector_item in vector_results:
            text = vector_item.get("text", "").lower()
            
            # Check for basic mobility need
            if "basic mobility" in text:
                if "not" in text and "car substitute" in text:
                    criteria["car_substitute"] = False
                else:
                    criteria["basic_mobility"] = True
            
            # Check for prescription requirements
            if "prescriber" in text or "prescription" in text:
                criteria["valid_prescription"] = True
            
            # Check for Ontario residency
            if "ontario resident" in text or "valid health card" in text:
                criteria["ontario_resident"] = True
            
            # Special checks for car substitute concern
            if request.use_case:
                if request.use_case.location and "outdoor_only" in str(request.use_case.location):
                    if "car substitute" in text:
                        criteria["car_substitute"] = False
                        criteria["basic_mobility"] = False
        
        # Build eligibility response
        other_criteria = {}
        if criteria["car_substitute"] is not None:
            other_criteria["not_car_substitute"] = criteria["car_substitute"]
        
        return Eligibility(
            basic_mobility=criteria["basic_mobility"],
            ontario_resident=criteria["ontario_resident"],
            valid_prescription=criteria["valid_prescription"],
            other_criteria=other_criteria if other_criteria else None
        )
    
    async def _check_exclusions(
        self,
        sql_result: Dict[str, Any],
        vector_results: List[Dict[str, Any]],
        request: ADPGetRequest
    ) -> List[str]:
        """
        Check for applicable exclusions.
        
        Returns:
            List of exclusion descriptions
        """
        exclusions = []
        device_type = request.device.type.lower()
        
        # Process SQL exclusions
        for exclusion in sql_result.get("exclusions", []):
            phrase = exclusion.get("phrase", "")
            applies_to = exclusion.get("applies_to", "")
            
            # Check if exclusion applies to this device
            if phrase.lower() in device_type or device_type in phrase.lower():
                exclusions.append(f"{phrase}: {applies_to}")
        
        # Extract exclusions from vector context
        for vector_item in vector_results:
            text = vector_item.get("text", "")
            
            if "not cover" in text.lower() or "exclusion" in text.lower():
                # Extract specific exclusions mentioned
                if "batteries" in text.lower() and "batteries" in device_type:
                    exclusions.append("Batteries are not covered by ADP")
                elif "repairs" in text.lower() and "repair" in device_type:
                    exclusions.append("Repairs and maintenance are not covered")
                elif "replacement parts" in text.lower():
                    exclusions.append("Replacement parts are not covered")
        
        return list(set(exclusions))  # Remove duplicates
    
    async def _determine_funding(
        self,
        sql_result: Dict[str, Any],
        vector_results: List[Dict[str, Any]],
        request: ADPGetRequest
    ) -> tuple[Optional[Funding], List[Conflict]]:
        """
        Determine funding percentages from SQL and vector evidence.
        
        Returns:
            Tuple of (Funding info, conflicts)
        """
        conflicts = []
        
        # Get funding from SQL
        sql_funding = None
        for rule in sql_result.get("funding", []):
            scenario = rule.get("scenario", "").lower()
            device_type = request.device.type.lower()
            
            # Find matching funding rule
            if device_type in scenario or request.device.category in scenario:
                sql_funding = {
                    "client_share": rule.get("client_share_percent", 25),
                    "adp_share": rule.get("adp_share_percent", 75)
                }
                break
        
        # Extract funding from vector
        vector_funding = None
        for vector_item in vector_results:
            text = vector_item.get("text", "")
            
            # Look for percentage mentions
            if "75%" in text and "ADP" in text:
                vector_funding = {"adp_share": 75, "client_share": 25}
            elif "50%" in text and "ADP" in text:
                vector_funding = {"adp_share": 50, "client_share": 50}
            
            if vector_funding:
                break
        
        # Check for conflicts
        if sql_funding and vector_funding:
            if sql_funding["adp_share"] != vector_funding["adp_share"]:
                conflicts.append(Conflict(
                    field="adp_coverage_percent",
                    sql_value=sql_funding["adp_share"],
                    vector_value=vector_funding["adp_share"],
                    resolution="Using SQL value as authoritative for percentages"
                ))
        
        # Use SQL as primary source for percentages
        if sql_funding:
            funding = Funding(
                client_share_percent=sql_funding["client_share"],
                adp_contribution=sql_funding["adp_share"],
                max_contribution=None,
                repair_coverage="Not covered"
            )
        elif vector_funding:
            funding = Funding(
                client_share_percent=vector_funding["client_share"],
                adp_contribution=vector_funding["adp_share"],
                max_contribution=None,
                repair_coverage="Not covered"
            )
        else:
            # Default funding split
            funding = Funding(
                client_share_percent=25.0,
                adp_contribution=75.0,
                max_contribution=None,
                repair_coverage="Not covered"
            )
        
        return funding, conflicts
    
    async def _check_cep(
        self,
        sql_result: Dict[str, Any],
        vector_results: List[Dict[str, Any]],
        request: ADPGetRequest
    ) -> Optional[CEPInfo]:
        """
        Check CEP (Client Eligibility Program) eligibility.
        
        Returns:
            CEP eligibility information or None
        """
        # Determine income threshold (use single person default)
        threshold = CEP_THRESHOLDS["single"]
        
        # Check for CEP information in vector results
        for vector_item in vector_results:
            text = vector_item.get("text", "")
            
            if "CEP" in text or "client eligibility program" in text.lower():
                # Extract threshold if mentioned
                if "$28,000" in text or "28000" in text:
                    threshold = 28000
                elif "$39,000" in text or "39000" in text:
                    threshold = 39000
                break
        
        # Determine eligibility based on income if provided
        eligible = False
        if request.patient_income is not None:
            eligible = request.patient_income < threshold
        
        return CEPInfo(
            income_threshold=threshold,
            eligible=eligible,
            client_share=0.0 if eligible else 25.0
        )
    
    def _extract_citations(self, vector_results: List[Dict[str, Any]]) -> List[Citation]:
        """Extract citations from vector search results."""
        citations = []
        seen = set()
        
        for result in vector_results:
            metadata = result.get("metadata", {})
            
            source = metadata.get("source", "")
            if "mobility" in source.lower():
                source = "mobility-manual"
            elif "comm" in source.lower():
                source = "comm-aids-manual"
            else:
                source = "adp-manual"
            
            loc = metadata.get("section_ref", metadata.get("section", ""))
            page = metadata.get("page")
            
            # Create unique key to avoid duplicates
            key = f"{source}:{loc}:{page}"
            if key not in seen:
                seen.add(key)
                citations.append(Citation(
                    source=source,
                    loc=loc,
                    page=page
                ))
        
        return citations


async def adp_get(
    request: Dict[str, Any],
    sql_client: Optional[SQLClient] = None,
    vector_client: Optional[VectorClient] = None
) -> Dict[str, Any]:
    """
    MCP tool entry point for adp.get.
    
    Args:
        request: Raw request dictionary
        sql_client: Optional SQL client (for testing)
        vector_client: Optional vector client (for testing)
        
    Returns:
        Response dictionary
    """
    # Parse request
    parsed_request = ADPGetRequest(**request)
    
    # Create tool instance
    tool = ADPTool(sql_client=sql_client, vector_client=vector_client)
    
    # Execute query
    response = await tool.execute(parsed_request)
    
    # Return as dictionary
    return response.model_dump()