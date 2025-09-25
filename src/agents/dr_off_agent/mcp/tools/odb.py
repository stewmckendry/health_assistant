"""
ODB (Ontario Drug Benefit) dual-path retrieval tool.
Always runs SQL and vector search in parallel, merges results.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ..models.request import ODBGetRequest
from ..models.response import (
    ODBGetResponse,
    DrugCoverage,
    InterchangeableDrug,
    LowestCostDrug,
    Citation,
    Conflict
)
from ..retrieval import SQLClient, VectorClient
from ..utils import ConfidenceScorer, ConflictDetector
from .odb_drug_extractor import get_drug_extractor

logger = logging.getLogger(__name__)


class ODBTool:
    """
    ODB formulary retrieval tool with dual-path execution.
    Always runs SQL and vector queries in parallel for drug coverage.
    """
    
    def __init__(
        self,
        sql_client: Optional[SQLClient] = None,
        vector_client: Optional[VectorClient] = None
    ):
        """
        Initialize ODB tool with retrieval clients.
        
        Args:
            sql_client: SQL client instance (creates default if None)
            vector_client: Vector client instance (creates default if None)
        """
        # Use the correct database path with ODB tables
        self.sql_client = sql_client or SQLClient(
            db_path="data/ohip.db",  # Merged database location
            timeout_ms=500
        )
        self.vector_client = vector_client or VectorClient(
            persist_directory="data/dr_off_agent/processed/dr_off/chroma",
            timeout_ms=1000
        )
        self.confidence_scorer = ConfidenceScorer()
        self.conflict_detector = ConflictDetector()
        self.drug_extractor = get_drug_extractor()
        
        logger.info("ODB tool initialized with dual-path retrieval")
    
    async def execute(self, request: ODBGetRequest) -> ODBGetResponse:
        """
        Execute ODB query with dual-path retrieval.
        
        Args:
            request: ODBGetRequest with query parameters
            
        Returns:
            ODBGetResponse with merged SQL + vector results
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
            sql_result = []
            
        if not isinstance(vector_result, Exception):
            provenance.append("vector")
        else:
            logger.warning(f"Vector search failed: {vector_result}")
            # Log more details about the error
            import traceback
            if hasattr(vector_result, '__traceback__'):
                logger.error(f"Vector search traceback: {''.join(traceback.format_tb(vector_result.__traceback__))}")
            vector_result = []
        
        # Merge results
        coverage, interchangeable, lowest_cost, citations, conflicts, context = await self._merge_results(
            sql_result if not isinstance(sql_result, Exception) else [],
            vector_result if not isinstance(vector_result, Exception) else [],
            request
        )
        
        # Calculate confidence
        sql_hits = (1 if coverage else 0) + len(interchangeable) if "sql" in provenance else 0
        vector_hits = len(vector_result) if not isinstance(vector_result, Exception) and "vector" in provenance else 0
        
        confidence = self.confidence_scorer.calculate(
            sql_hits=sql_hits,
            vector_matches=vector_hits,
            has_conflict=len(conflicts) > 0
        )
        
        # Adjust response based on what was found
        if not coverage and not interchangeable and not provenance:
            # No data found
            confidence = 0.0
            
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"ODB query completed in {elapsed_ms:.1f}ms: "
            f"coverage={coverage is not None}, "
            f"alternatives={len(interchangeable)}, "
            f"confidence={confidence:.2f}"
        )
        
        return ODBGetResponse(
            provenance=provenance,
            confidence=confidence,
            coverage=coverage,
            interchangeable=interchangeable,
            lowest_cost=lowest_cost,
            citations=citations,
            conflicts=conflicts,
            context=context if context else None
        )
    
    async def _sql_query(self, request: ODBGetRequest) -> List[Dict[str, Any]]:
        """
        Execute SQL query for ODB drug data.
        
        Args:
            request: ODB request parameters
            
        Returns:
            List of SQL results
        """
        try:
            # Extract search parameters from the enhanced request
            din = getattr(request, 'din', None)
            raw_drug = getattr(request, 'drug', None)
            ingredient = getattr(request, 'ingredient', None)
            
            # If we have a drug query that looks like natural language, extract the drug name
            if raw_drug and not ingredient:
                extracted_drug, condition = self.drug_extractor.extract_drug_info(raw_drug)
                if extracted_drug:
                    ingredient = extracted_drug
                    logger.info(f"Extracted drug '{ingredient}' from query '{raw_drug}'")
                else:
                    # Fall back to using the raw query
                    ingredient = raw_drug
            
            # Handle drug class searches
            if hasattr(request, 'drug_class') and request.drug_class:
                # For drug classes, search by common ingredients
                ingredient = self._map_drug_class_to_ingredient(request.drug_class)
            
            # Check if we should exclude LU drugs
            exclude_lu = getattr(request, 'exclude_lu', False)
            
            # Use specialized ODB query method
            results = await self.sql_client.query_odb_drugs(
                din=din,
                ingredient=ingredient,
                lowest_cost_only=False,  # Get all, we'll filter later
                limit=request.top_k * 3  # Get extra for filtering
            )
            
            # Filter out LU drugs if requested
            if exclude_lu and results:
                # This would need LU data in the database
                # For now, we'll pass through all results
                pass
            
            logger.debug(f"SQL query returned {len(results)} drug records")
            return results
            
        except asyncio.TimeoutError:
            logger.warning("SQL query timed out")
            raise
        except Exception as e:
            logger.error(f"SQL query error: {e}")
            raise
    
    async def _vector_search(self, request: ODBGetRequest) -> List[Dict[str, Any]]:
        """
        Execute vector search for ODB policy context.
        
        Args:
            request: ODB request parameters
            
        Returns:
            List of vector search results
        """
        try:
            # Build comprehensive search query
            query_parts = []
            
            # Add the main query text
            if hasattr(request, 'q'):
                query_parts.append(request.q)
            
            # Add drug name if provided
            if hasattr(request, 'drug') and request.drug:
                query_parts.append(request.drug)
            elif hasattr(request, 'ingredient') and request.ingredient:
                query_parts.append(request.ingredient)
                
            # Add condition context for LU evaluation
            if hasattr(request, 'condition') and request.condition:
                query_parts.append(request.condition)
            
            # Add specific checks requested
            if hasattr(request, 'check') and request.check:
                for check in request.check:
                    if check == "lu_criteria":
                        query_parts.append("limited use criteria requirements")
                    elif check == "documentation":
                        query_parts.append("documentation requirements")
                    elif check == "alternatives":
                        query_parts.append("alternative medications covered")
            
            search_query = " ".join(query_parts)
            
            # Search ODB policy documents
            results = await self.vector_client.search_odb(
                query=search_query,
                drug_class=getattr(request, 'drug_class', None),
                n_results=request.top_k
            )
            
            logger.debug(f"Vector search returned {len(results)} chunks")
            return results
            
        except asyncio.TimeoutError:
            logger.warning("Vector search timed out")
            raise
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            raise
    
    async def _merge_results(
        self,
        sql_results: List[Dict[str, Any]],
        vector_results: List[Dict[str, Any]],
        request: ODBGetRequest
    ) -> Tuple[Optional[DrugCoverage], List[InterchangeableDrug], 
               Optional[LowestCostDrug], List[Citation], List[Conflict], List[str]]:
        """
        Merge SQL and vector results for comprehensive drug information.
        
        Args:
            sql_results: Results from SQL query
            vector_results: Results from vector search
            request: Original request for context
            
        Returns:
            Tuple of (coverage, interchangeable, lowest_cost, citations, conflicts, context)
        """
        coverage = None
        interchangeable = []
        lowest_cost = None
        citations = []
        conflicts = []
        
        # Process SQL results for structured drug data
        if sql_results:
            # Find the primary drug requested
            primary_drug = self._find_primary_drug(sql_results, request)
            
            if primary_drug:
                # Extract LU requirements from vector if available
                lu_info = self._extract_lu_criteria(vector_results, primary_drug)
                
                coverage = DrugCoverage(
                    covered=True,  # If in database, it's covered
                    din=primary_drug.get('din', ''),
                    brand_name=primary_drug.get('name', ''),  # SQL returns 'name' not 'brand'
                    generic_name=primary_drug.get('generic_name', ''),  # SQL returns 'generic_name' not 'ingredient'
                    strength=primary_drug.get('strength', ''),
                    lu_required=lu_info.get('required', False),
                    lu_criteria=lu_info.get('criteria')
                )
            
            # Find interchangeable drugs
            group_id = primary_drug.get('interchangeable_group_id') if primary_drug else None  # Fixed field name
            if group_id:
                for drug in sql_results:
                    if drug.get('interchangeable_group_id') == group_id:  # Fixed field name
                        interchangeable.append(InterchangeableDrug(
                            din=drug.get('din', ''),
                            brand=drug.get('name', ''),  # SQL returns 'name' not 'brand'
                            price=drug.get('individual_price', 0.0),  # SQL returns 'individual_price' not 'price'
                            lowest_cost=drug.get('is_lowest_cost', False)  # SQL returns 'is_lowest_cost' not 'lowest_cost'
                        ))
            
            # Find lowest cost option
            if interchangeable:
                lowest = min(interchangeable, key=lambda x: x.price)
                savings = 0.0
                if primary_drug:
                    primary_price = primary_drug.get('individual_price', 0.0)  # Fixed field name
                    savings = primary_price - lowest.price
                
                lowest_cost = LowestCostDrug(
                    din=lowest.din,
                    brand=lowest.brand,
                    price=lowest.price,
                    savings=max(0.0, savings)
                )
        
        # Process vector results for policy context and citations
        context_snippets = []
        is_vector_only = len(sql_results) == 0  # Detect vector-only search
        
        for vector_item in vector_results:
            metadata = vector_item.get('metadata', {})
            text = vector_item.get('text', '')
            
            # Collect context snippets - provide more context for vector-only searches
            if text:
                # For drug embeddings, provide full text (they're structured and concise)
                # For policy documents, provide more context if it's a vector-only search
                if metadata.get('din'):  # Drug embedding
                    context_snippets.append(text)  # Full drug info
                elif len(context_snippets) < (5 if is_vector_only else 3):  # More context for vector-only
                    # For policy docs, provide more context for clinical questions
                    # Vector-only searches get longer snippets since they're the primary info source
                    max_chars = 800 if is_vector_only else 500
                    snippet = text[:max_chars] + "..." if len(text) > max_chars else text
                    context_snippets.append(snippet)
            
            # Create citation with better metadata handling
            # For drug embeddings, create a meaningful location string
            if metadata.get('din'):
                loc = f"DIN: {metadata.get('din')} - {metadata.get('brand_name', '')} ({metadata.get('generic_name', '')})"
            else:
                loc = metadata.get('section', '')
            
            citation = Citation(
                source=metadata.get('source_document', metadata.get('source', 'odb_formulary')),
                loc=loc,
                page=metadata.get('page')
            )
            
            # Avoid duplicate citations
            if not any(c.source == citation.source and c.loc == citation.loc 
                      for c in citations):
                citations.append(citation)
            
            # Check for conflicts between SQL and vector
            if coverage and self._detect_coverage_conflict(coverage, text):
                conflict = Conflict(
                    field="coverage",
                    sql_value="covered",
                    vector_value=self._extract_coverage_statement(text),
                    resolution="SQL data is authoritative for formulary listing"
                )
                conflicts.append(conflict)
        
        # Handle case where drug is not in SQL but mentioned in vector
        if not coverage and vector_results:
            coverage_info = self._extract_coverage_from_vector(vector_results, request)
            if coverage_info:
                coverage = coverage_info
        
        # Handle alternatives if primary drug not covered
        if coverage and not coverage.covered:
            alternatives = self._find_alternatives_from_vector(vector_results, request)
            for alt in alternatives:
                # Create pseudo-interchangeable entries for alternatives
                interchangeable.append(InterchangeableDrug(
                    din="",  # Will be filled if found in SQL
                    brand=alt.get('name', ''),
                    price=0.0,  # Unknown from vector
                    lowest_cost=False
                ))
        
        return coverage, interchangeable, lowest_cost, citations, conflicts, context_snippets
    
    def _find_primary_drug(
        self,
        sql_results: List[Dict[str, Any]],
        request: ODBGetRequest
    ) -> Optional[Dict[str, Any]]:
        """Find the primary drug being queried."""
        # If DIN specified, find exact match
        if hasattr(request, 'din') and request.din:
            for drug in sql_results:
                if drug.get('din') == request.din:
                    return drug
        
        # Otherwise find by generic_name/name (actual SQL field names)
        search_term = (getattr(request, 'drug', None) or 
                      getattr(request, 'ingredient', None))
        
        if search_term:
            search_lower = search_term.lower()
            for drug in sql_results:
                if (search_lower in drug.get('generic_name', '').lower() or
                    search_lower in drug.get('name', '').lower()):
                    return drug
        
        # Return first result as fallback
        return sql_results[0] if sql_results else None
    
    def _extract_lu_criteria(
        self,
        vector_results: List[Dict[str, Any]],
        drug_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract Limited Use criteria from vector results."""
        lu_info = {'required': False, 'criteria': None}
        
        drug_name = drug_info.get('ingredient', '').lower()
        
        for result in vector_results:
            text = result.get('text', '').lower()
            
            # Check if LU is mentioned for this drug
            if drug_name in text and ('limited use' in text or ' lu ' in text):
                lu_info['required'] = True
                
                # Extract criteria
                if 'must' in text or 'require' in text:
                    # Find the sentence containing requirements
                    sentences = result.get('text', '').split('.')
                    for sentence in sentences:
                        if drug_name in sentence.lower() and 'require' in sentence.lower():
                            lu_info['criteria'] = sentence.strip()
                            break
                
                # Common LU requirements
                if 'metformin' in text and 'fail' in text:
                    if not lu_info['criteria']:
                        lu_info['criteria'] = "Must have failed or have contraindication to metformin"
        
        return lu_info
    
    def _detect_coverage_conflict(
        self,
        coverage: DrugCoverage,
        vector_text: str
    ) -> bool:
        """Detect if vector evidence conflicts with SQL coverage."""
        text_lower = vector_text.lower()
        drug_lower = coverage.generic_name.lower()
        
        # Check for conflicting coverage statements
        if drug_lower in text_lower:
            if 'not covered' in text_lower or 'not listed' in text_lower:
                return True
            if 'special authorization' in text_lower and not coverage.lu_required:
                return True
        
        return False
    
    def _extract_coverage_statement(self, text: str) -> str:
        """Extract coverage statement from vector text."""
        sentences = text.split('.')
        for sentence in sentences:
            if 'cover' in sentence.lower() or 'authoriz' in sentence.lower():
                return sentence.strip()[:200]
        return "Restrictions may apply"
    
    def _extract_coverage_from_vector(
        self,
        vector_results: List[Dict[str, Any]],
        request: ODBGetRequest
    ) -> Optional[DrugCoverage]:
        """Extract coverage info when drug not in SQL database."""
        drug_name = getattr(request, 'drug', '') or getattr(request, 'ingredient', '')
        if not drug_name:
            return None
        
        drug_lower = drug_name.lower()
        
        for result in vector_results:
            text = result.get('text', '')
            text_lower = text.lower()
            
            if drug_lower in text_lower:
                # Check coverage status
                covered = 'covered' in text_lower and 'not covered' not in text_lower
                
                return DrugCoverage(
                    covered=covered,
                    din=getattr(request, 'din', '') or '',
                    brand_name=drug_name,
                    generic_name=drug_name,
                    strength='',
                    lu_required='limited use' in text_lower or ' lu ' in text_lower,
                    lu_criteria=self._extract_lu_criteria(vector_results, 
                                                         {'ingredient': drug_name}).get('criteria')
                )
        
        # Not found in vector either
        return DrugCoverage(
            covered=False,
            din=getattr(request, 'din', '') or '',
            brand_name=drug_name,
            generic_name=drug_name,
            strength='',
            lu_required=False,
            lu_criteria=None
        )
    
    def _find_alternatives_from_vector(
        self,
        vector_results: List[Dict[str, Any]],
        request: ODBGetRequest
    ) -> List[Dict[str, Any]]:
        """Find alternative drugs mentioned in vector results."""
        alternatives = []
        drug_class = getattr(request, 'drug_class', None)
        
        if drug_class:
            class_lower = drug_class.lower()
            
            for result in vector_results:
                text = result.get('text', '')
                
                # Look for drug names in the same class
                if class_lower in text.lower():
                    # Extract drug names (simplified - would need NER in production)
                    if 'statin' in class_lower:
                        for statin in ['atorvastatin', 'simvastatin', 'rosuvastatin', 
                                      'pravastatin', 'lovastatin']:
                            if statin in text.lower():
                                alternatives.append({'name': statin})
                    elif 'glp' in class_lower or 'glp-1' in class_lower:
                        for glp1 in ['semaglutide', 'ozempic', 'liraglutide', 'victoza']:
                            if glp1 in text.lower():
                                alternatives.append({'name': glp1})
        
        return alternatives
    
    def _map_drug_class_to_ingredient(self, drug_class: str) -> str:
        """Map drug class to common ingredients for SQL search."""
        class_lower = drug_class.lower()
        
        # Common mappings
        if 'statin' in class_lower:
            return 'statin'  # Will match atorvastatin, simvastatin, etc.
        elif 'glp' in class_lower or 'glp-1' in class_lower:
            return 'glutide'  # Will match semaglutide, liraglutide, etc.
        elif 'ace' in class_lower:
            return 'pril'  # Will match enalapril, lisinopril, etc.
        elif 'arb' in class_lower:
            return 'sartan'  # Will match losartan, valsartan, etc.
        
        return drug_class


async def odb_get(
    request: Dict[str, Any],
    sql_client: Optional[SQLClient] = None,
    vector_client: Optional[VectorClient] = None
) -> Dict[str, Any]:
    """
    MCP tool entry point for odb.get.
    
    Args:
        request: Raw request dictionary
        sql_client: Optional SQL client (for testing)
        vector_client: Optional vector client (for testing)
        
    Returns:
        Response dictionary
    """
    # Parse request - handle both simple and complex request formats
    if 'q' in request:
        # Enhanced request format from tests
        parsed_request = type('ODBGetRequest', (), {
            'q': request.get('q', ''),
            'drug': request.get('drug'),
            'din': request.get('din'),
            'ingredient': request.get('ingredient'),
            'strength': request.get('strength'),
            'drug_class': request.get('drug_class'),
            'check': request.get('check', ['coverage', 'interchangeable', 'lowest_cost']),
            'condition': request.get('condition'),
            'include_brand': request.get('include_brand', True),
            'exclude_lu': request.get('exclude_lu', False),
            'top_k': request.get('top_k', 5)
        })()
    else:
        # Simple format from existing model
        parsed_request = ODBGetRequest(**request)
    
    # Create tool instance
    tool = ODBTool(sql_client=sql_client, vector_client=vector_client)
    
    # Execute query
    response = await tool.execute(parsed_request)
    
    # Return as dictionary
    return response.model_dump()