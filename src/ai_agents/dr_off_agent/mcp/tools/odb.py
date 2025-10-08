"""
ODB (Ontario Drug Benefit) dual-path retrieval tool.
Always runs SQL and vector search in parallel, merges results.

Now includes ODBQueryProcessor for flexible natural language understanding.
"""
import asyncio
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from ..models.response import (
    ODBGetResponse,
    DrugCoverage,
    InterchangeableDrug,
    LowestCostDrug,
    Citation,
    Conflict,
    RetrievedItem
)
from ..retrieval import SQLClient, VectorClient
from ..utils import ConfidenceScorer, ConflictDetector
from .odb_drug_extractor import get_drug_extractor
from .odb_query_processor import ODBQueryProcessor

logger = logging.getLogger(__name__)

# Feature flag for new query processor - unified toggle
def _should_use_query_processor():
    """Check if query processor should be enabled (global or tool-specific override)."""
    # Check tool-specific override first
    tool_specific = os.getenv("ODB_QUERY_PROCESSOR")
    if tool_specific is not None:
        return tool_specific.lower() in ["true", "1", "yes"]

    # Fall back to global setting
    global_setting = os.getenv("ENABLE_QUERY_PROCESSOR", "false")
    return global_setting.lower() in ["true", "1", "yes"]

USE_QUERY_PROCESSOR = _should_use_query_processor()


class ODBTool:
    """
    ODB formulary retrieval tool with dual-path execution.
    Always runs SQL and vector queries in parallel for drug coverage.
    """
    
    def __init__(
        self,
        sql_client: Optional[SQLClient] = None,
        vector_client: Optional[VectorClient] = None,
        use_query_processor: Optional[bool] = None
    ):
        """
        Initialize ODB tool with retrieval clients.

        Args:
            sql_client: SQL client instance (creates default if None)
            vector_client: Vector client instance (creates default if None)
            use_query_processor: Whether to use new LLM-powered query processor (default: from env)
        """
        # Use the correct database path with ODB tables
        self.sql_client = sql_client or SQLClient(
            db_path="data/ohip.db",  # Merged database location
            timeout_ms=500
        )
        self.vector_client = vector_client or VectorClient(
            persist_directory=None,  # Will use environment-appropriate default
            timeout_ms=5000
        )
        self.confidence_scorer = ConfidenceScorer()
        self.conflict_detector = ConflictDetector()
        self.drug_extractor = get_drug_extractor()

        # Initialize query processor if enabled
        self.use_query_processor = use_query_processor if use_query_processor is not None else USE_QUERY_PROCESSOR
        if self.use_query_processor:
            try:
                self.query_processor = ODBQueryProcessor(
                    sql_client=self.sql_client,
                    vector_client=self.vector_client
                )
                logger.info("ODB tool initialized with LLM-powered query processor")
            except Exception as e:
                logger.warning(f"Failed to initialize query processor: {e}. Falling back to legacy mode.")
                self.use_query_processor = False
                self.query_processor = None
        else:
            self.query_processor = None
            logger.info("ODB tool initialized with dual-path retrieval (legacy mode)")
    
    async def execute(self, request: Dict[str, Any]) -> ODBGetResponse:
        """
        Execute ODB query with dual-path retrieval.

        Routes to enhanced query processor if enabled, otherwise uses legacy path.

        Args:
            request: Request dictionary with query parameters

        Returns:
            ODBGetResponse with merged SQL + vector results
        """
        start_time = datetime.now()

        # Route to query processor if enabled and this is a natural language query
        if self.use_query_processor and 'q' in request:
            logger.info("Using enhanced query processor for natural language understanding")
            try:
                return await self._execute_with_query_processor(request)
            except Exception as e:
                logger.error(f"Query processor failed: {e}. Falling back to legacy path.")
                # Fall through to legacy execution
        
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
            if sql_result:  # Only add if we got results
                provenance.append("sql")
        else:
            logger.warning(f"SQL query failed: {sql_result}")
            sql_result = []

        if not isinstance(vector_result, Exception):
            if vector_result:  # Only add if we got results
                provenance.append("vector")
        else:
            logger.warning(f"Vector search failed: {vector_result}")
            # Log more details about the error
            import traceback
            if hasattr(vector_result, '__traceback__'):
                logger.error(f"Vector search traceback: {''.join(traceback.format_tb(vector_result.__traceback__))}")
            vector_result = []
        
        # Merge results
        coverage, interchangeable, lowest_cost, citations, conflicts = await self._merge_results(
            sql_result if not isinstance(sql_result, Exception) else [],
            vector_result if not isinstance(vector_result, Exception) else [],
            request
        )

        # Build items from vector results
        items = self._build_items(
            vector_result if not isinstance(vector_result, Exception) else []
        )
        
        # Calculate confidence
        sql_hits = (1 if coverage else 0) + len(interchangeable) if "sql" in provenance else 0
        vector_hits = len(vector_result) if not isinstance(vector_result, Exception) and "vector" in provenance else 0
        
        confidence = self.confidence_scorer.calculate(
            sql_hits=sql_hits,
            vector_matches=vector_hits,
            has_conflict=len(conflicts) > 0
        )
        
        # Ensure we always have at least one citation, even when no data is found
        if not citations:
            citations.append(Citation(
                source="Ontario Drug Benefit Formulary (Edition 43)",
                loc="General Reference",
                section_path=None,
                page=None,
                url="https://www.ontario.ca/files/2025-09/moh-formulary-edition-43-en-2025-09-17.pdf"
            ))
        
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
            items=items,
            coverage=coverage,
            interchangeable=interchangeable,
            lowest_cost=lowest_cost,
            citations=citations,
            conflicts=conflicts
        )

    async def _execute_with_query_processor(self, request: Dict[str, Any]) -> ODBGetResponse:
        """
        Execute query using enhanced LLM-powered query processor.

        This provides flexible natural language understanding and structured extraction.

        Args:
            request: Request dictionary with 'q' field containing natural language query

        Returns:
            ODBGetResponse with enhanced understanding and extraction
        """
        start_time = datetime.now()
        raw_query = request.get('q', '')

        # Step 1: Understand the query
        intent = await self.query_processor.understand_query(raw_query)
        logger.info(f"Query intent: {intent.query_type}, drugs: {intent.drug_names}")

        # Step 2: Retrieve data
        retrieval = await self.query_processor.retrieve(intent)

        # Step 3: Enrich with LLM extraction
        enriched = await self.query_processor.enrich_with_llm(intent, retrieval)

        # Step 4: Convert to ODBGetResponse format
        response = await self._format_enhanced_response(enriched, start_time)

        return response

    async def _format_enhanced_response(
        self,
        enriched,  # EnrichedResult
        start_time: datetime
    ) -> ODBGetResponse:
        """
        Format EnrichedResult into standard ODBGetResponse.

        This bridges the new query processor with the existing response format.
        """
        provenance = []
        if enriched.retrieval.sql_results:
            provenance.append("sql")
        if enriched.retrieval.vector_results:
            provenance.append("vector")

        # Build coverage from SQL if available
        coverage = None
        interchangeable = []
        lowest_cost = None

        if enriched.retrieval.sql_results:
            # Use existing merge logic
            coverage, interchangeable, lowest_cost, citations, conflicts = await self._merge_results(
                enriched.retrieval.sql_results,
                enriched.retrieval.vector_results,
                {'q': enriched.intent.original_query}
            )
        else:
            # Vector-only results - use drug class handling
            citations = []
            conflicts = []
            if enriched.retrieval.vector_results:
                coverage, interchangeable, lowest_cost, citations, conflicts = await self._merge_results(
                    [],
                    enriched.retrieval.vector_results,
                    {'q': enriched.intent.original_query}
                )

        # Enrich coverage with LU criteria if extracted
        if enriched.lu_criteria and coverage:
            coverage.lu_required = enriched.lu_criteria.lu_required
            coverage.lu_criteria = enriched.lu_criteria.criteria

        # Add therapeutic alternatives to interchangeable list
        for alt in enriched.therapeutic_alternatives:
            # Check if already in list
            if not any(d.brand == alt.drug_name for d in interchangeable):
                interchangeable.append(InterchangeableDrug(
                    din=alt.din or '',
                    brand=f"{alt.drug_name} ({', '.join(alt.brand_names)})" if alt.brand_names else alt.drug_name,
                    price=alt.price or 0.0,
                    lowest_cost=False
                ))

        # Build items from vector results
        items = self._build_items(enriched.retrieval.vector_results)

        # Calculate confidence
        sql_hits = (1 if coverage else 0) + len(interchangeable) if enriched.retrieval.sql_success else 0
        vector_hits = len(enriched.retrieval.vector_results) if enriched.retrieval.vector_success else 0

        confidence = self.confidence_scorer.calculate(
            sql_hits=sql_hits,
            vector_matches=vector_hits,
            has_conflict=len(conflicts) > 0 if 'conflicts' in locals() else False
        )

        # Boost confidence for successful LLM extraction
        if enriched.enrichment_method == "llm_extraction":
            confidence = min(1.0, confidence + 0.1)

        # Ensure we always have citations
        if not citations:
            citations = [Citation(
                source="Ontario Drug Benefit Formulary (Edition 43)",
                loc="General Reference",
                section_path=None,
                page=None,
                url="https://www.ontario.ca/files/2025-09/moh-formulary-edition-43-en-2025-09-17.pdf"
            )]

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(
            f"Enhanced ODB query completed in {elapsed_ms:.1f}ms: "
            f"query_type={enriched.intent.query_type}, "
            f"confidence={confidence:.2f}"
        )

        return ODBGetResponse(
            provenance=provenance,
            confidence=confidence,
            items=items,
            coverage=coverage,
            interchangeable=interchangeable,
            lowest_cost=lowest_cost,
            citations=citations,
            conflicts=conflicts if 'conflicts' in locals() else []
        )

    async def _sql_query(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute SQL query for ODB drug data.

        Args:
            request: ODB request parameters

        Returns:
            List of SQL results
        """
        try:
            # Extract search parameters from the request dict
            din = request.get('din')
            raw_drug = request.get('drug')
            ingredient = request.get('ingredient')

            # Detect drug class queries - skip SQL for these as they work better with vector search
            if raw_drug and not din and not ingredient:
                drug_class_keywords = ['medications', 'drugs', 'medicines', 'class', 'agents', 'therapies']
                query_lower = raw_drug.lower()
                if any(keyword in query_lower for keyword in drug_class_keywords):
                    logger.info(f"Detected drug class query: '{raw_drug}' - skipping SQL, using vector-only")
                    return []

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
            drug_class = request.get('drug_class')
            if drug_class:
                # For drug classes, search by common ingredients
                ingredient = self._map_drug_class_to_ingredient(drug_class)

            # Check if we should exclude LU drugs
            exclude_lu = request.get('exclude_lu', False)

            # Use specialized ODB query method
            top_k = request.get('top_k', 5)
            results = await self.sql_client.query_odb_drugs(
                din=din,
                ingredient=ingredient,
                lowest_cost_only=False,  # Get all, we'll filter later
                limit=top_k * 3  # Get extra for filtering
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
    
    async def _vector_search(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
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
            q = request.get('q')
            if q:
                query_parts.append(q)

            # Add drug name if provided
            drug = request.get('drug')
            ingredient = request.get('ingredient')
            if drug:
                query_parts.append(drug)
            elif ingredient:
                query_parts.append(ingredient)

            # Add condition context for LU evaluation
            condition = request.get('condition')
            if condition:
                query_parts.append(condition)

            # Add specific checks requested
            check = request.get('check')
            if check:
                for check_item in check:
                    if check_item == "lu_criteria":
                        query_parts.append("limited use criteria requirements")
                    elif check_item == "documentation":
                        query_parts.append("documentation requirements")
                    elif check_item == "alternatives":
                        query_parts.append("alternative medications covered")

            search_query = " ".join(query_parts)

            # Search ODB policy documents
            top_k = request.get('top_k', 5)
            drug_class = request.get('drug_class')
            results = await self.vector_client.search_odb(
                query=search_query,
                drug_class=drug_class,
                n_results=top_k
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
        request: Dict[str, Any]
    ) -> Tuple[Optional[DrugCoverage], List[InterchangeableDrug],
               Optional[LowestCostDrug], List[Citation], List[Conflict]]:
        """
        Merge SQL and vector results for comprehensive drug information.

        Args:
            sql_results: Results from SQL query
            vector_results: Results from vector search
            request: Original request for context

        Returns:
            Tuple of (coverage, interchangeable, lowest_cost, citations, conflicts)
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
                    din=primary_drug.get('din') or '',
                    brand_name=primary_drug.get('name') or '',  # SQL returns 'name' not 'brand'
                    generic_name=primary_drug.get('generic_name') or '',  # SQL returns 'generic_name' not 'ingredient'
                    strength=primary_drug.get('strength') or '',  # Ensure string, not None
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
                            price=drug.get('individual_price') or 0.0,  # Handle None values explicitly
                            lowest_cost=drug.get('is_lowest_cost', False)  # SQL returns 'is_lowest_cost' not 'lowest_cost'
                        ))
            
            # Find lowest cost option
            if interchangeable:
                lowest = min(interchangeable, key=lambda x: x.price)
                savings = 0.0
                if primary_drug:
                    primary_price = primary_drug.get('individual_price') or 0.0  # Handle None values explicitly
                    # Ensure both values are floats
                    try:
                        primary_price = float(primary_price) if primary_price else 0.0
                        lowest_price = float(lowest.price) if lowest.price else 0.0
                        savings = primary_price - lowest_price
                    except (TypeError, ValueError):
                        savings = 0.0
                
                lowest_cost = LowestCostDrug(
                    din=lowest.din,
                    brand=lowest.brand,
                    price=lowest.price,
                    savings=max(0.0, savings)
                )
        
        # Process vector results for citations
        for vector_item in vector_results:
            metadata = vector_item.get('metadata', {})
            text = vector_item.get('text', '')
            
            # Create citation with better metadata handling
            # For drug embeddings, create a meaningful location string
            if metadata.get('din'):
                loc = f"DIN: {metadata.get('din')} - {metadata.get('brand_name', '')} ({metadata.get('generic_name', '')})"
                # Use ODB formulary search URL with DIN
                din = metadata.get('din', '')
                url = f"https://www.formulary.health.gov.on.ca/formulary/results.xhtml?q={din}" if din else "https://www.formulary.health.gov.on.ca/formulary/"
                source = "Ontario Drug Benefit Formulary (Edition 43)"
            else:
                loc = metadata.get('section', '')
                # Use the actual ODB PDF URL
                url = "https://www.ontario.ca/files/2025-09/moh-formulary-edition-43-en-2025-09-17.pdf"
                source = "ODB Coverage Guidelines"
            
            citation = Citation(
                source=source,
                loc=loc,
                section_path=metadata.get('section_path'),
                page=metadata.get('page'),
                url=url
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
        # Only try this if we have sql_results (meaning we tried to query a specific drug)
        if not coverage and vector_results and sql_results:
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

        # Handle drug class queries - when SQL returns empty but vector has results
        # This happens for queries like "glycemic control medications" that are drug classes
        if not coverage and not sql_results and vector_results:
            logger.info(f"No SQL results but {len(vector_results)} vector results - treating as drug class query")
            for result in vector_results[:10]:  # Top 10 drugs from vector search
                metadata = result.get('metadata', {})
                text = result.get('text', '')

                if metadata.get('din'):
                    # Extract price from text (format: "Price: $X.XX per unit" or "Price: $X")
                    price = 0.0
                    if 'Price:' in text:
                        try:
                            # Find price line
                            import re
                            price_match = re.search(r'Price:\s*\$?([\d.]+)', text)
                            if price_match:
                                price = float(price_match.group(1))
                        except (ValueError, AttributeError):
                            price = 0.0

                    brand = metadata.get('brand_name', '')
                    generic = metadata.get('generic_name', '')

                    interchangeable.append(InterchangeableDrug(
                        din=metadata.get('din', ''),
                        brand=f"{brand} ({generic})" if brand and generic else (brand or generic),
                        price=price,
                        lowest_cost=False
                    ))

            # Find lowest cost option if we have prices
            if interchangeable:
                priced_drugs = [d for d in interchangeable if d.price > 0]
                if priced_drugs:
                    lowest = min(priced_drugs, key=lambda x: x.price)
                    lowest_cost = LowestCostDrug(
                        din=lowest.din,
                        brand=lowest.brand,
                        price=lowest.price,
                        savings=0.0
                    )
        
        # Always include at least one citation to the ODB Formulary
        # This ensures users know the source of the information, even for negative results
        if not citations:
            citations.append(Citation(
                source="Ontario Drug Benefit Formulary (Edition 43)",
                loc="General Reference",
                section_path=None,
                page=None,
                url="https://www.ontario.ca/files/2025-09/moh-formulary-edition-43-en-2025-09-17.pdf"
            ))
        
        return coverage, interchangeable, lowest_cost, citations, conflicts
    
    def _find_primary_drug(
        self,
        sql_results: List[Dict[str, Any]],
        request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find the primary drug being queried."""
        # If DIN specified, find exact match
        din = request.get('din')
        if din:
            for drug in sql_results:
                if drug.get('din') == din:
                    return drug

        # Otherwise find by generic_name/name (actual SQL field names)
        search_term = request.get('drug') or request.get('ingredient')
        
        if search_term:
            search_lower = search_term.lower()
            for drug in sql_results:
                if (search_lower in drug.get('generic_name', '').lower() or
                    search_lower in drug.get('name', '').lower()):
                    return drug
        
        # Return first result as fallback
        return sql_results[0] if sql_results else None

    def _build_items(
        self,
        vector_results: List[Dict[str, Any]]
    ) -> List[RetrievedItem]:
        """
        Build standardized retrieved items from vector search results.

        Args:
            vector_results: List of vector search results

        Returns:
            List of RetrievedItem objects for evaluation and observability
        """
        items = []
        for result in vector_results:
            metadata = result.get("metadata", {})
            distance = result.get("distance", 0.0)

            # Convert distance to relevance score (distance is cosine, 0=perfect match, 2=opposite)
            # Normalize to 0-1 range where 1 is most relevant
            relevance_score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))

            # Extract identifier (din, chunk_id, or use generic identifier)
            item_id = metadata.get("din") or metadata.get("chunk_id") or metadata.get("uid", "unknown")

            # Build source identifier from metadata
            source = "odb_formulary"

            # Create RetrievedItem
            items.append(RetrievedItem(
                id=str(item_id),
                text=result.get("text", ""),
                relevance_score=relevance_score,
                source=source,
                metadata={
                    "din": metadata.get("din"),
                    "drug_name": metadata.get("drug_name"),
                    "generic_name": metadata.get("generic_name"),
                    "page_num": metadata.get("page_num"),
                    "section": metadata.get("section"),
                    "distance": distance
                }
            ))

        return items

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
        request: Dict[str, Any]
    ) -> Optional[DrugCoverage]:
        """Extract coverage info when drug not in SQL database."""
        drug_name = request.get('drug', '') or request.get('ingredient', '')
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
                    din=request.get('din', ''),
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
            din=request.get('din', ''),
            brand_name=drug_name,
            generic_name=drug_name,
            strength='',
            lu_required=False,
            lu_criteria=None
        )
    
    def _find_alternatives_from_vector(
        self,
        vector_results: List[Dict[str, Any]],
        request: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find alternative drugs mentioned in vector results."""
        alternatives = []
        drug_class = request.get('drug_class')
        
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
        request: Standardized request dict with query, k, filters
        sql_client: Optional SQL client (for testing)
        vector_client: Optional vector client (for testing)

    Returns:
        Response dictionary
    """
    # Extract from standardized format
    query = request.get("query", "")
    k = request.get("k", 5)
    filters = request.get("filters", {})

    # Build internal request format
    parsed_request = {
        'q': query,
        'drug': query,  # Use query as drug name
        'din': filters.get('din'),
        'ingredient': filters.get('ingredient'),
        'strength': filters.get('strength'),
        'drug_class': filters.get('drug_class'),
        'check': filters.get('check', ['coverage', 'interchangeable', 'lowest_cost']),
        'condition': filters.get('condition'),
        'include_brand': filters.get('include_brand', True),
        'exclude_lu': filters.get('exclude_lu', False),
        'top_k': k
    }

    # Create tool instance
    tool = ODBTool(sql_client=sql_client, vector_client=vector_client)

    # Execute query
    response = await tool.execute(parsed_request)

    # Return as dictionary
    return response.model_dump()