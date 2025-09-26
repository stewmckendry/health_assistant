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
from .adp_device_extractor import get_device_extractor
import openai
import os

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
        self.vector_client = vector_client or VectorClient(persist_directory="data/dr_off_agent/processed/dr_off/chroma", timeout_ms=1000)
        self.confidence_scorer = ConfidenceScorer()
        self.conflict_detector = ConflictDetector()
        
        logger.info("ADP tool initialized with dual-path retrieval")
        
        # Initialize OpenAI client for LLM reranking
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = openai.OpenAI(api_key=api_key)
        else:
            self.openai_client = None
            logger.warning("No OpenAI API key - LLM reranking disabled")
    
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
            
            # Extract keywords from device type for exclusion search
            device_keywords = self._extract_device_keywords(request.device.type)
            exclusion_task = self.sql_client.query_adp_exclusions(
                search_term=device_keywords
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
                n_results=12  # Get more results for reranking
            )
            
            # Apply LLM reranking for better relevance
            reranked_results = await self._rerank_vector_results(
                query=request.device.type,
                vector_results=results,
                device_category=request.device.category
            )
            
            # Return top results after reranking
            final_results = reranked_results[:8]
            
            logger.debug(f"Vector search returned {len(results)} ADP chunks, reranked to {len(final_results)}")
            return final_results
            
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
        
        # Extract eligibility criteria from vector results using rich metadata
        criteria = {
            "basic_mobility": None,
            "ontario_resident": None,
            "valid_prescription": None,
            "car_substitute": None
        }
        
        # Use metadata to prioritize results with eligibility topics
        eligibility_results = []
        for vector_item in vector_results:
            metadata = vector_item.get("metadata", {})
            topics = metadata.get("topics", "[]")
            
            # Parse topics JSON if it's a string
            if isinstance(topics, str):
                try:
                    import json
                    topics_list = json.loads(topics)
                    if "eligibility" in topics_list or "requirements" in topics_list:
                        eligibility_results.append(vector_item)
                except:
                    pass
            
            # Fallback: check if metadata indicates eligibility content
            title = metadata.get("title", "").lower()
            if "eligib" in title or "requir" in title or "criteria" in title:
                eligibility_results.append(vector_item)
        
        # If no eligibility-specific results, use all results
        if not eligibility_results:
            eligibility_results = vector_results
        
        # Process eligibility results
        for vector_item in eligibility_results:
            text = vector_item.get("text", "").lower()
            metadata = vector_item.get("metadata", {})
            
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
            
            # Use metadata to enhance criteria detection
            section_id = metadata.get("section_id", "")
            if section_id and "eligib" in section_id.lower():
                # This is an eligibility section, give it more weight
                if "mobility" in text:
                    criteria["basic_mobility"] = True
                if "resident" in text:
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
        
        # Enhanced exclusions from vector context using metadata
        exclusion_results = []
        for vector_item in vector_results:
            metadata = vector_item.get("metadata", {})
            exclusion_count = metadata.get("exclusion_count", 0)
            topics = metadata.get("topics", "[]")
            
            # Prioritize results with exclusions
            if exclusion_count > 0:
                exclusion_results.append(vector_item)
            elif isinstance(topics, str):
                try:
                    import json
                    topics_list = json.loads(topics)
                    if "exclusions" in topics_list or "not covered" in topics_list:
                        exclusion_results.append(vector_item)
                except:
                    pass
        
        # Process exclusion-specific results first, then fallback to all results
        search_results = exclusion_results if exclusion_results else vector_results
        
        for vector_item in search_results:
            text = vector_item.get("text", "")
            metadata = vector_item.get("metadata", {})
            
            if "not cover" in text.lower() or "exclusion" in text.lower():
                # Extract specific exclusions mentioned with context
                if "batteries" in text.lower() and "batteries" in device_type:
                    policy_ref = metadata.get("policy_uid", "ADP Policy")
                    exclusions.append(f"Batteries are not covered by ADP ({policy_ref})")
                elif "repairs" in text.lower() and "repair" in device_type:
                    policy_ref = metadata.get("policy_uid", "ADP Policy") 
                    exclusions.append(f"Repairs and maintenance are not covered ({policy_ref})")
                elif "replacement parts" in text.lower():
                    policy_ref = metadata.get("policy_uid", "ADP Policy")
                    exclusions.append(f"Replacement parts are not covered ({policy_ref})")
                elif "accessories" in text.lower() and any(word in device_type for word in ["accessor", "cushion", "bag"]):
                    policy_ref = metadata.get("policy_uid", "ADP Policy")
                    exclusions.append(f"Device accessories may not be covered ({policy_ref})")
            
            # Look for device-specific exclusions in metadata
            section_id = metadata.get("section_id", "")
            if "exclus" in section_id.lower() and any(word in text.lower() for word in device_type.split()):
                title = metadata.get("title", "Exclusion")
                exclusions.append(f"{title} - See {section_id}")
        
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
        
        # Enhanced funding extraction from vector using metadata
        vector_funding = None
        funding_context = []
        
        # Prioritize results with funding information
        funding_results = []
        for vector_item in vector_results:
            metadata = vector_item.get("metadata", {})
            funding_count = metadata.get("funding_count", 0)
            topics = metadata.get("topics", "[]")
            
            if funding_count > 0:
                funding_results.append(vector_item)
            elif isinstance(topics, str):
                try:
                    import json
                    topics_list = json.loads(topics)
                    if "funding" in topics_list or "coverage" in topics_list:
                        funding_results.append(vector_item)
                except:
                    pass
        
        # Process funding-specific results
        search_results = funding_results if funding_results else vector_results
        
        for vector_item in search_results:
            text = vector_item.get("text", "")
            metadata = vector_item.get("metadata", {})
            
            # Look for percentage mentions with context
            if "75%" in text and "ADP" in text:
                vector_funding = {"adp_share": 75, "client_share": 25}
                policy_ref = metadata.get("policy_uid", "")
                funding_context.append(f"75% ADP coverage mentioned in {policy_ref}")
            elif "50%" in text and "ADP" in text:
                vector_funding = {"adp_share": 50, "client_share": 50}
                policy_ref = metadata.get("policy_uid", "")
                funding_context.append(f"50% ADP coverage mentioned in {policy_ref}")
            elif "25%" in text and ("client" in text.lower() or "patient" in text.lower()):
                if not vector_funding:  # Don't override existing funding
                    vector_funding = {"adp_share": 75, "client_share": 25}
                policy_ref = metadata.get("policy_uid", "")
                funding_context.append(f"25% client share mentioned in {policy_ref}")
            
            # Look for specific funding amounts or caps
            import re
            dollar_amounts = re.findall(r'\$[\d,]+', text)
            if dollar_amounts:
                policy_ref = metadata.get("policy_uid", "ADP Policy")
                funding_context.append(f"Funding amounts mentioned: {', '.join(dollar_amounts)} ({policy_ref})")
            
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
        
        # Use SQL as primary source for percentages, enhance with vector context
        funding_notes = []
        if funding_context:
            funding_notes.extend(funding_context)
        
        if sql_funding:
            # Add SQL source context
            scenario = sql_result.get("funding", [{}])[0].get("scenario", "")
            if scenario:
                funding_notes.append(f"SQL rule: {scenario}")
            
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
            funding_notes.append("Using standard ADP funding split")
            funding = Funding(
                client_share_percent=25.0,
                adp_contribution=75.0,
                max_contribution=None,
                repair_coverage="Not covered"
            )
        
        # Add funding context as a conflict if there are multiple sources
        if len(funding_notes) > 1:
            conflicts.append(Conflict(
                field="funding_context",
                sql_value="SQL database rules", 
                vector_value="Policy document references",
                resolution=f"Additional context: {'; '.join(funding_notes[:2])}"
            ))
        
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
    
    def _extract_device_keywords(self, device_type: str) -> str:
        """
        Extract keywords from compound device types for exclusion matching.
        
        Examples:
            "scooter_batteries" -> "batteries"
            "wheelchair_cushions" -> "cushions"
            "walker_accessories" -> "accessories"
        """
        # Common exclusion keywords to extract
        exclusion_keywords = [
            "batteries", "battery", "chargers", "charger",
            "repairs", "repair", "maintenance", "servicing",
            "accessories", "cushions", "parts", "components",
            "covers", "bags", "straps", "belts"
        ]
        
        device_lower = device_type.lower()
        
        # Check for exact keyword matches
        for keyword in exclusion_keywords:
            if keyword in device_lower:
                return keyword
        
        # Fallback: return the device type as-is
        return device_type
    
    def _build_context_content(
        self, 
        vector_results: List[Dict[str, Any]], 
        sql_result: Dict[str, Any]
    ) -> str:
        """
        Build context content from search results for transparency.
        Similar to ODB tool's context content.
        """
        context_parts = []
        
        # Add vector search context
        if vector_results:
            context_parts.append("**ADP Policy Context:**")
            for i, result in enumerate(vector_results[:3]):  # Top 3 most relevant
                text = result.get("text", "").strip()
                metadata = result.get("metadata", {})
                
                # Create meaningful reference
                policy_uid = metadata.get("policy_uid", "")
                section_id = metadata.get("section_id", "")
                title = metadata.get("title", "")
                
                if title:
                    ref = f"{policy_uid} - {title[:60]}..."
                elif section_id:
                    ref = f"Section {section_id}"
                else:
                    ref = f"ADP Policy {i+1}"
                
                # Add truncated text with reference
                text_snippet = text[:200] + "..." if len(text) > 200 else text
                context_parts.append(f"• {ref}: {text_snippet}")
        
        # Add SQL funding rules context
        funding_rules = sql_result.get("funding", [])
        if funding_rules:
            context_parts.append("\n**Funding Rules:**")
            for rule in funding_rules[:2]:  # Top 2 matching rules
                scenario = rule.get("scenario", "")
                client_share = rule.get("client_share_percent", "")
                adp_share = rule.get("adp_share_percent", "")
                
                if scenario and client_share and adp_share:
                    context_parts.append(f"• {scenario}: Client {client_share}%, ADP {adp_share}%")
        
        # Add exclusions context
        exclusions = sql_result.get("exclusions", [])
        if exclusions:
            context_parts.append("\n**Exclusions:**")
            for exclusion in exclusions[:2]:  # Top 2 relevant exclusions
                phrase = exclusion.get("phrase", "")
                applies_to = exclusion.get("applies_to", "")
                if phrase:
                    context_parts.append(f"• {phrase}: {applies_to}")
        
        return "\n".join(context_parts)
    
    async def _rerank_vector_results(
        self,
        query: str,
        vector_results: List[Dict[str, Any]],
        device_category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to rerank vector results for better relevance.
        Prioritizes exact device matches and relevant policy content.
        """
        if not self.openai_client or not vector_results:
            return vector_results
        
        try:
            # Build reranking prompt
            device_type = query
            category_context = f" in the {device_category} category" if device_category else ""
            
            # Prepare results for reranking
            results_text = []
            for i, result in enumerate(vector_results):
                text = result.get("text", "")[:300]  # Truncate for prompt
                metadata = result.get("metadata", {})
                title = metadata.get("title", "")
                policy_uid = metadata.get("policy_uid", "")
                
                result_summary = f"Result {i}: {title} ({policy_uid})\n{text}"
                results_text.append(result_summary)
            
            # LLM reranking call
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""Rank these ADP policy results by relevance to the query about {device_type}{category_context}.
                            
                            Prioritize:
                            1. Exact device name matches
                            2. Device category matches  
                            3. Funding and eligibility criteria
                            4. Specific policy requirements
                            
                            Return only the result numbers in order of relevance (most relevant first), separated by commas.
                            Example: 2,0,4,1,3"""
                        },
                        {
                            "role": "user",
                            "content": "\n\n".join(results_text[:8])  # Limit to top 8 for token efficiency
                        }
                    ],
                    temperature=0,
                    max_tokens=50
                )
            )
            
            # Parse reranking response
            ranking_text = response.choices[0].message.content.strip()
            try:
                ranking_indices = [int(x.strip()) for x in ranking_text.split(",") if x.strip().isdigit()]
                
                # Reorder results based on ranking
                reranked_results = []
                used_indices = set()
                
                for idx in ranking_indices:
                    if 0 <= idx < len(vector_results) and idx not in used_indices:
                        reranked_results.append(vector_results[idx])
                        used_indices.add(idx)
                
                # Add any remaining results
                for i, result in enumerate(vector_results):
                    if i not in used_indices:
                        reranked_results.append(result)
                
                logger.info(f"LLM reranked {len(vector_results)} results: {ranking_indices}")
                return reranked_results
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse ranking: {ranking_text}, error: {e}")
                return vector_results
                
        except Exception as e:
            logger.error(f"LLM reranking failed: {e}")
            return vector_results
    
    def _extract_citations(self, vector_results: List[Dict[str, Any]]) -> List[Citation]:
        """Extract enhanced citations from vector search results using rich metadata."""
        citations = []
        seen = set()
        
        for result in vector_results:
            metadata = result.get("metadata", {})
            
            # Use rich metadata for meaningful citations
            adp_doc = metadata.get("adp_doc", "")
            policy_uid = metadata.get("policy_uid", "")
            section_id = metadata.get("section_id", "")
            page_num = metadata.get("page_num")
            
            # Create meaningful source names
            if "mobility" in adp_doc.lower():
                source = "ADP Mobility Manual"
            elif "comm" in adp_doc.lower():
                source = "ADP Communication Aids Manual"
            elif "core" in adp_doc.lower():
                source = "ADP Core Manual"
            else:
                source = f"ADP {adp_doc.title()}" if adp_doc else "ADP Manual"
            
            # Create meaningful location reference
            if policy_uid:
                loc = policy_uid
            elif section_id:
                loc = f"Section {section_id}"
            else:
                loc = metadata.get("section_ref", metadata.get("section", ""))
            
            # Create unique key to avoid duplicates
            key = f"{source}:{loc}:{page_num}"
            if key not in seen:
                seen.add(key)
                citations.append(Citation(
                    source=source,
                    loc=loc,
                    page=page_num
                ))
        
        return citations

    async def _synthesize_answer(
        self,
        original_query: str,
        response: ADPGetResponse,
        sql_result: Dict[str, Any],
        vector_results: List[Dict[str, Any]],
        patient_income: Optional[float] = None
    ) -> tuple[str, float]:
        """
        Use LLM to synthesize a direct answer to the original clinical question.
        
        Args:
            original_query: The original natural language query
            response: The structured ADP response with all data
            sql_result: Raw SQL query results
            vector_results: Raw vector search results
            patient_income: Patient income if provided
            
        Returns:
            Tuple of (answer, confidence_score)
        """
        if not self.openai_client:
            logger.warning("LLM synthesis requested but no OpenAI API key available")
            return None, None
        
        try:
            # Build context for LLM from the structured response
            context_parts = []
            
            # Device information
            if hasattr(response, 'device_info'):
                context_parts.append(f"Device: {response.device_info}")
            
            # Funding information
            if response.funding:
                funding_text = f"ADP covers {response.funding.adp_contribution}%, patient pays {response.funding.client_share_percent}%"
                if response.cep and response.cep.eligible:
                    funding_text += f" (CEP eligible - patient cost eliminated due to income below ${response.cep.income_threshold:.0f})"
                elif response.cep and not response.cep.eligible:
                    funding_text += f" (income above CEP threshold of ${response.cep.income_threshold:.0f})"
                context_parts.append(f"Funding: {funding_text}")
            
            # Eligibility information
            if response.eligibility:
                elig_parts = []
                if response.eligibility.basic_mobility is True:
                    elig_parts.append("meets basic mobility need")
                elif response.eligibility.basic_mobility is False:
                    elig_parts.append("does not meet basic mobility need")
                
                if response.eligibility.ontario_resident is True:
                    elig_parts.append("Ontario resident")
                elif response.eligibility.ontario_resident is False:
                    elig_parts.append("not confirmed as Ontario resident")
                
                if response.eligibility.valid_prescription is True:
                    elig_parts.append("valid prescription required")
                elif response.eligibility.valid_prescription is False:
                    elig_parts.append("no valid prescription")
                
                if elig_parts:
                    context_parts.append(f"Eligibility: {', '.join(elig_parts)}")
            
            # Exclusions
            if response.exclusions:
                context_parts.append(f"Exclusions: {'; '.join(response.exclusions[:2])}")
            
            # Citations context
            if response.citations:
                citation_sources = [f"{c.source}" for c in response.citations[:3]]
                context_parts.append(f"Sources: {', '.join(citation_sources)}")
            
            # Income context
            if patient_income is not None:
                context_parts.append(f"Patient income: ${patient_income:.0f}")
            
            structured_context = "\n".join(context_parts)
            
            # Build LLM prompt for answer synthesis
            prompt = f"""You are a clinical expert analyzing ADP (Assistive Devices Program) funding eligibility in Ontario. 

Original question: "{original_query}"

Available information:
{structured_context}

Based on this information, provide a direct, clinical answer to the original question. Your answer should:
1. Directly answer the yes/no question if possible
2. Include specific funding percentages and costs
3. Mention CEP eligibility if relevant to low-income patients  
4. Note any important requirements or exclusions
5. Be concise but complete for a clinician

Also provide your confidence level (0.0-1.0) based on:
- Completeness of available data
- Clarity of eligibility criteria
- Presence of any exclusions or conflicts

Format your response as:
ANSWER: [Your direct answer]
CONFIDENCE: [0.0-1.0]

Example:
ANSWER: Yes, your patient qualifies for ADP funding for a power wheelchair. ADP covers 75% of the cost, and since the patient's income of $19,000 is below the CEP threshold of $28,000, they are eligible for the Chronic Equipment Pool which eliminates the patient's 25% share entirely. A valid prescription from an authorized prescriber is required.
CONFIDENCE: 0.9"""

            # Call LLM
            response_obj = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a clinical expert providing precise ADP funding guidance."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=300
                )
            )
            
            # Parse response
            llm_response = response_obj.choices[0].message.content.strip()
            
            # Extract answer and confidence
            answer = None
            confidence = None
            
            for line in llm_response.split('\n'):
                if line.startswith('ANSWER:'):
                    answer = line.replace('ANSWER:', '').strip()
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.replace('CONFIDENCE:', '').strip())
                    except ValueError:
                        confidence = None
            
            if answer is None:
                # Fallback: use entire response as answer
                answer = llm_response
                confidence = 0.7  # Lower confidence for unparsed response
            
            if confidence is None:
                confidence = 0.6  # Default moderate confidence
            
            logger.info(f"LLM synthesized answer (conf={confidence:.2f}): {answer[:100]}...")
            return answer, confidence
            
        except Exception as e:
            logger.error(f"LLM answer synthesis failed: {e}")
            return None, None


async def adp_get(
    request: Dict[str, Any],
    sql_client: Optional[SQLClient] = None,
    vector_client: Optional[VectorClient] = None
) -> Dict[str, Any]:
    """
    MCP tool entry point for adp.get.
    
    Args:
        request: Raw request dictionary - can be either:
            1. Natural language: {"query": "Can I get funding for a CPAP?", "patient_income": 35000}
            2. Structured: {"device": {"category": "respiratory", "type": "CPAP"}, ...}
        sql_client: Optional SQL client (for testing)
        vector_client: Optional vector client (for testing)
        
    Returns:
        Response dictionary with comprehensive context for LLM interpretation
    """
    # Preserve original query for LLM synthesis
    original_query_for_synthesis = None
    
    # Handle natural language query format
    if "query" in request and "device" not in request:
        # Natural language query - extract device and parameters
        extractor = get_device_extractor()
        query = request["query"]
        original_query_for_synthesis = query  # Preserve original query
        
        logger.info(f"Processing natural language query: {query}")
        extracted = extractor.extract_device_params(query)
        
        # Build structured request from extraction
        request = {
            "device": {
                "category": extracted.get("device_category", "mobility"),
                "type": extracted.get("device_type", "device")
            },
            "check": extracted.get("check_types", ["eligibility", "funding", "exclusions"]),
            "patient_income": request.get("patient_income", extracted.get("patient_income")),
            "use_case": extracted.get("use_case", {})
        }
        logger.info(f"Converted to structured request: {request}")
    
    # Category aliases for LLM flexibility  
    CATEGORY_ALIASES = {
        # Mobility variations
        "mobility": "mobility",
        "mobility_devices": "mobility",
        "wheelchairs": "mobility",
        
        # Communication variations
        "comm_aids": "comm_aids",
        "communication": "comm_aids",
        "communication_aids": "comm_aids",
        "aac": "comm_aids",
        "speech": "comm_aids",
        
        # Hearing variations
        "hearing": "hearing_devices",
        "hearing_devices": "hearing_devices",
        "hearing_aids": "hearing_devices",
        
        # Vision variations
        "vision": "visual_aids",
        "visual": "visual_aids",
        "visual_aids": "visual_aids",
        
        # Respiratory variations
        "respiratory": "respiratory",
        "oxygen": "respiratory",
        "ventilator": "respiratory",
        "cpap": "respiratory",
        
        # Insulin/glucose variations
        "insulin": "insulin_pump",
        "insulin_pump": "insulin_pump",
        "glucose": "glucose_monitoring",
        "glucose_monitoring": "glucose_monitoring",
        "blood_glucose": "glucose_monitoring",
        
        # Prosthetics variations
        "prosthesis": "prosthesis",
        "prosthetic": "prosthesis",
        "prosthetics": "prosthesis",
        "limb": "prosthesis",
        
        # Maxillofacial variations
        "maxillofacial": "maxillofacial",
        "facial": "maxillofacial",
        "facial_prosthetic": "maxillofacial",
        
        # Grants/core
        "grants": "grants",
        "special_funding": "grants",
        "core": "core_manual",
        "core_manual": "core_manual",
        "general": "core_manual"
    }
    
    # Normalize category using aliases
    if "device" in request and isinstance(request["device"], dict):
        device_info = request["device"]
        
        # Apply category aliasing for flexibility
        if "category" in device_info and device_info["category"]:
            original_cat = device_info["category"].lower().replace("-", "_")
            normalized_cat = CATEGORY_ALIASES.get(original_cat)
            if normalized_cat:
                device_info["category"] = normalized_cat
                logger.info(f"Normalized category '{original_cat}' to '{normalized_cat}'")
        
        device_type = device_info.get("type", "")
        
        # If device type looks like a natural language query, extract parameters
        extractor = get_device_extractor()
        if extractor._is_natural_language(device_type):
            logger.info(f"Detected natural language query: {device_type}")
            extracted_params = extractor.extract_device_params(device_type)
            
            # Update request with extracted parameters
            if extracted_params["device_type"]:
                request["device"]["type"] = extracted_params["device_type"]
            if extracted_params["device_category"] and not device_info.get("category"):
                request["device"]["category"] = extracted_params["device_category"]
            
            # Add extracted use case if not provided
            if extracted_params["use_case"] and not request.get("use_case"):
                request["use_case"] = extracted_params["use_case"]
            
            # Add extracted patient income if not provided  
            if extracted_params["patient_income"] is not None and not request.get("patient_income"):
                request["patient_income"] = extracted_params["patient_income"]
            
            # Add extracted check types if not provided
            if extracted_params["check_types"] and not request.get("check"):
                request["check"] = extracted_params["check_types"]
            
            logger.info(f"Enhanced request with extracted params: {request}")
    
    # Parse request
    parsed_request = ADPGetRequest(**request)
    
    # Create tool instance
    tool = ADPTool(sql_client=sql_client, vector_client=vector_client)
    
    # Execute query
    response = await tool.execute(parsed_request)
    
    # Add context content field like ODB tool
    response_dict = response.model_dump()
    
    # Build context content from the search results that were used
    # Re-run queries to get raw results for context building
    sql_result = await tool._sql_query(parsed_request)
    vector_result = await tool._vector_search(parsed_request)
    
    if not isinstance(sql_result, Exception) and not isinstance(vector_result, Exception):
        context_content = tool._build_context_content(vector_result, sql_result)
        response_dict["context"] = context_content
    
    # Add LLM synthesis for natural language queries
    original_query = original_query_for_synthesis  # Use preserved original query
    logger.info(f"Checking for synthesis: preserved query = {original_query}")
    
    # Fallback: check if device type was natural language
    if not original_query and "device" in request and isinstance(request["device"], dict):
        device_type = request["device"].get("type", "")
        extractor = get_device_extractor()
        if extractor._is_natural_language(device_type):
            original_query = device_type
            logger.info(f"Found natural language device type: {original_query}")
    
    logger.info(f"Final original_query: {original_query}")
    
    if original_query:
        logger.info(f"Attempting LLM synthesis for query: {original_query}")
        try:
            synthesized_answer, answer_confidence = await tool._synthesize_answer(
                original_query=original_query,
                response=response,
                sql_result=sql_result,
                vector_results=vector_result,
                patient_income=parsed_request.patient_income
            )
            
            logger.info(f"Synthesis returned: answer={synthesized_answer is not None}, confidence={answer_confidence}")
            
            if synthesized_answer:
                response_dict["answer"] = synthesized_answer
                response_dict["answer_confidence"] = answer_confidence
                logger.info(f"Added LLM synthesis to response: {answer_confidence:.2f} confidence")
            else:
                logger.warning("LLM synthesis returned null answer")
        except Exception as e:
            logger.error(f"LLM synthesis failed with exception: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    else:
        logger.info(f"No original query found for synthesis. Query in request: {'query' in request}")
    
    # Add LLM-friendly summary that directly answers common questions
    summary_parts = []
    
    # Build funding summary
    if response_dict.get("funding"):
        funding = response_dict["funding"]
        adp_pct = funding.get("adp_contribution", 0)
        client_pct = funding.get("client_share_percent", 0)
        
        # Check CEP eligibility
        if response_dict.get("cep") and response_dict["cep"].get("eligible"):
            summary_parts.append(f"✅ ELIGIBLE for funding: ADP covers {adp_pct}% with CEP eliminating patient cost (income below ${response_dict['cep']['income_threshold']:.0f})")
        elif response_dict.get("cep") and not response_dict["cep"].get("eligible"):
            summary_parts.append(f"✅ ELIGIBLE for funding: ADP covers {adp_pct}%, patient pays {client_pct}% (income above CEP threshold of ${response_dict['cep']['income_threshold']:.0f})")
        else:
            summary_parts.append(f"✅ ELIGIBLE for funding: ADP covers {adp_pct}%, patient pays {client_pct}%")
    else:
        summary_parts.append("❓ Funding information not available")
    
    # Add eligibility notes
    if response_dict.get("eligibility"):
        elig = response_dict["eligibility"]
        if elig.get("valid_prescription") == False:
            summary_parts.append("⚠️ Requires valid prescription from authorized prescriber")
        if elig.get("ontario_resident") == False:
            summary_parts.append("⚠️ Must be Ontario resident")
    
    # Add exclusions if any
    if response_dict.get("exclusions"):
        excl_list = response_dict["exclusions"]
        if excl_list:
            summary_parts.append(f"⚠️ Exclusions: {'; '.join(excl_list[:2])}")
    
    # Add device type for clarity
    if parsed_request.device:
        device_desc = f"{parsed_request.device.type}"
        if hasattr(parsed_request.device, 'category'):
            category_map = {
                "mobility": "Mobility Device",
                "comm_aids": "Communication Aid",
                "hearing_devices": "Hearing Device",
                "visual_aids": "Visual Aid",
                "respiratory": "Respiratory Equipment",
                "insulin_pump": "Insulin Pump",
                "glucose_monitoring": "Glucose Monitor",
                "prosthesis": "Prosthetic",
                "maxillofacial": "Maxillofacial Prosthetic"
            }
            cat_name = category_map.get(parsed_request.device.category, parsed_request.device.category)
            summary_parts.insert(0, f"📋 Device: {device_desc} ({cat_name})")
    
    response_dict["summary"] = " | ".join(summary_parts)
    
    # Add interpretation guidance for nulls
    response_dict["interpretation_notes"] = {
        "null_values": "null means 'not determined from query' - may require follow-up",
        "confidence": f"{response_dict['confidence']:.2f} - {'High' if response_dict['confidence'] > 0.9 else 'Moderate'} confidence",
        "cep": "Chronic Equipment Pool eliminates patient cost for low-income patients"
    }
    
    return response_dict